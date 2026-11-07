"""No weights/MLX required: exercise owned runtime and public wire contracts."""
import base64
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from desk.budget.budget import Budget, Workload, fits
from desk.budget.store import Measurements
from desk.foundation.config import update_config
from desk.gateway.openai_dialect import parse_request, completion_response, stream_chunks
from desk.llm.omlx import LocalBackend, MODEL_ALIAS, MODEL_KEY, OMLX_REVISION
from desk.llm.state import LlmRejected
from desk.resources.catalog import entry
from desk.testing.seed import TINY_PNG
from desk.resources.fit import model_fit
from desk.resources.manifest import ManifestStore
from tests.llm.llm_fakes import make_entry, make_service

# Valid tiny PNG; transport tests do not claim image understanding.
IMAGE = 'data:image/png;base64,' + base64.b64encode(TINY_PNG).decode()


def roots_at(tmp_path):
    return SimpleNamespace(data_root=tmp_path, config_path=tmp_path / 'config.json')


def model_at(tmp_path):
    model = tmp_path / 'weights'
    model.mkdir()
    (model / 'config.json').write_text(json.dumps({'model_type': 'qwen4_exp', 'vision_config': {'depth': 1}}))
    (model / 'model.safetensors.index.json').write_text(json.dumps({'weight_map': {'a': 'model.safetensors'}}))
    (model / 'model.safetensors').write_bytes(b'mock')
    return model


def test_spawn_isolated_pinned_runtime_and_no_mlx_lm_flags(tmp_path, monkeypatch):
    roots = roots_at(tmp_path)
    model = model_at(tmp_path)
    backend = LocalBackend(lambda: roots)
    spawn = Mock()
    monkeypatch.setattr('desk.llm.omlx.subprocess.Popen', spawn)
    monkeypatch.setenv('OMLX_HOST', '0.0.0.0')
    backend.spawn(Path('/desk/python'), model, 8767, tmp_path / 'logs/server.log', ['--prompt-cache-size', '1'])
    args = spawn.call_args.args[0]
    assert '--prompt-cache-size' not in args
    assert args[0] == str(tmp_path / 'runtimes/omlx/bin/python')
    assert args[args.index('--host') + 1] == '127.0.0.1'
    assert '--no-hf-cache' in args
    assert args[args.index('--memory-guard') + 1] == 'aggressive'
    assert args[args.index('--max-concurrent-requests') + 1] == '1'
    assert spawn.call_args.kwargs['env']['HF_HUB_OFFLINE'] == '1'
    assert 'OMLX_HOST' not in spawn.call_args.kwargs['env']
    base = tmp_path / 'omlx-qwen38'
    assert (base / 'models' / MODEL_ALIAS).resolve() == model
    settings = json.loads((base / 'model_settings.json').read_text())['models'][MODEL_ALIAS]
    assert settings['qwen4_ple_ssd_offload'] and settings['is_pinned']
    assert settings['mtp_enabled'] and settings['mtp_fixed_depth'] == 3
    assert settings['turboquant_kv_bits'] == 4 and settings['turboquant_skip_last']
    assert settings['max_context_window'] == 262144


@pytest.mark.parametrize('status,count,expected', [(503, 0, False), (200, 0, False), (200, 1, True)])
def test_health_waits_for_real_preload(tmp_path, monkeypatch, status, count, expected):
    backend = LocalBackend(lambda: roots_at(tmp_path))
    backend._omlx = True
    conn = Mock()
    response = conn.getresponse.return_value
    response.status = status
    response.read.return_value = json.dumps({'status': 'healthy', 'engine_pool': {'loaded_count': count}}).encode()
    monkeypatch.setattr('desk.llm.omlx.http.client.HTTPConnection', Mock(return_value=conn))
    assert backend.health(8767) is expected
    conn.request.assert_called_with('GET', '/health')
    conn.close.assert_called_once()


def test_missing_runtime_and_bad_revision_fail_before_spawn(tmp_path, monkeypatch):
    roots = roots_at(tmp_path)
    backend = LocalBackend(lambda: roots)
    model = model_at(tmp_path)
    with pytest.raises(OSError, match='独立 oMLX'):
        backend.validate_entry(entry(MODEL_KEY), model)
    update_config(roots, omlx_python='/bin/sh')
    run = Mock(return_value=SimpleNamespace(returncode=1, stderr='revision mismatch'))
    monkeypatch.setattr('desk.llm.omlx.subprocess.run', run)
    with pytest.raises(OSError, match='revision mismatch'):
        backend.validate_entry(entry(MODEL_KEY), model)
    assert OMLX_REVISION in run.call_args.args[0][-1]
    (model / 'model.safetensors').unlink()
    with pytest.raises(OSError, match='分片不完整'):
        backend.validate_entry(entry(MODEL_KEY), model)


def test_missing_runtime_does_not_evict_current_model(tmp_path):
    bed = make_service(tmp_path, entries=[make_entry(), entry(MODEL_KEY)])
    bed.service.load('glm')
    assert bed.service.wait_settled()['status'] == 'loaded'
    bed.calls.clear()
    bed.backend.validate_entry = Mock(side_effect=OSError('runtime missing'))
    with pytest.raises(LlmRejected, match='runtime missing'):
        bed.service.load(MODEL_KEY)
    assert not any(call[0] in ('acquire', 'spawn', 'terminate') for call in bed.calls)
    assert bed.service.status()['loaded_model']['key'] == 'glm'
    bed.service.close()


def test_spawn_failure_releases_reservation(tmp_path):
    bed = make_service(tmp_path)
    bed.backend.spawn = Mock(side_effect=OSError('exec failed'))
    bed.service.load('glm')
    assert bed.service.wait_settled()['status'] == 'error'
    assert any(call[0] == 'release' for call in bed.calls)
    bed.service.close()


def test_images_and_native_tool_roundtrip_and_sse(tmp_path):
    model = entry(MODEL_KEY)
    call = {'id': 'call_a', 'type': 'function', 'function': {'name': 'read_file', 'arguments': '{"path":"a.py"}'}}
    raw = {'choices': [{'message': {'content': None, 'tool_calls': [call]}, 'finish_reason': 'tool_calls'}],
           'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5}}
    bed = make_service(tmp_path, entries=[model], backend_kw={'chat_result': raw})
    bed.service.load(MODEL_KEY)
    assert bed.service.wait_settled()['status'] == 'loaded'
    bed.arbiter.set_desk_state({'holders': [{'kind': 'llm', 'label': MODEL_KEY, 'phase': 'held'}]})
    messages = [{'role': 'user', 'content': [{'type': 'text', 'text': '修复截图中的代码'},
                 {'type': 'image_url', 'image_url': {'url': IMAGE}}]}]
    request = parse_request({'model': model.hf_repo, 'messages': messages,
                             'tools': [{'type': 'function', 'function': {'name': 'read_file', 'parameters': {'type': 'object'}}}],
                             'enable_thinking': False})['chat_request']
    result = bed.service.chat_completion(request)
    upstream = next(c[2] for c in bed.calls if c[0] == 'chat')
    assert upstream['model'] == MODEL_ALIAS
    assert upstream['messages'] == messages
    assert upstream['tools'][0]['function']['name'] == 'read_file'
    assert upstream['chat_template_kwargs'] == {'enable_thinking': False}
    assert (upstream['temperature'], upstream['top_p'], upstream['presence_penalty']) == (.7, .8, 1.5)
    assert completion_response(result, model.hf_repo, 'c', 0)['choices'][0]['message']['tool_calls'] == [call]
    history = messages + [{'role': 'assistant', 'content': None, 'tool_calls': [call]},
                          {'role': 'tool', 'tool_call_id': 'call_a', 'content': 'print(1)'}]
    followup = parse_request({'messages': history})['chat_request']
    bed.service.chat_completion(followup)
    assert [c for c in bed.calls if c[0] == 'chat'][-1][2]['messages'][-1]['tool_call_id'] == 'call_a'
    chunks = [{'choices': [{'delta': {'tool_calls': [{'index': 0, **call}]}, 'finish_reason': None}]},
              {'choices': [{'delta': {}, 'finish_reason': 'tool_calls'}], 'usage': raw['usage']}]
    bed.backend.chat_stream = Mock(return_value=iter(chunks))
    events = list(bed.service.chat_stream(request))
    wire = b''.join(stream_chunks([('tool_calls', events[0]['tool_calls']), ('finish', events[1])], 'c', 0, model.hf_repo))
    assert b'"index": 0' in wire and b'"finish_reason": "tool_calls"' in wire
    assert wire.endswith(b'data: [DONE]\n\n')
    bed.service.close()


def test_disk_manifest_and_exclusive_reservation(tmp_path):
    model = entry(MODEL_KEY)
    manifest = ManifestStore(lambda: tmp_path, fetcher=Mock(side_effect=AssertionError('network'))).get(model)
    assert manifest.source == 'pinned'
    assert len([f for f in manifest.files if f.path.endswith('.safetensors')]) == 25
    assert 128.54e9 < manifest.total_bytes < 128.6e9
    assert all(f.revision == model.sources[0]['revision'] for f in manifest.files)
    budget = Budget(Measurements(), None, None, lambda: 0)
    cost = budget.cost('llm', key=MODEL_KEY, weights_gb=model.gb)
    assert cost.bytes_needed == 100 * 1024**3
    assert cost.source == 'unavailable'
    assert not fits([cost], 96 * 1024**3).ok
    assert fits([cost], int(107.5 * 1024**3)).ok
    assert not fits([cost, Workload('image', 'x', 1, 'predicted')], 128 * 1024**3).ok
    budget.capacity_bytes = lambda: int(107.5 * 1024**3)
    assert model_fit(model, budget, tmp_path)['needed_bytes'] == cost.bytes_needed
    assert budget.launch_args(MODEL_KEY, {}, model.gb) == []


@pytest.mark.parametrize('url', ['https://example.org/a.png', 'file:///tmp/a.png', '/tmp/a.png'])
def test_remote_and_local_image_paths_rejected(url):
    with pytest.raises(Exception, match='base64'):
        parse_request({'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': url}}]}]})


def test_runtime_configuration_validation_and_persistence(tmp_path):
    from desk.foundation.config import read_config
    from desk.foundation.errors import ConfigInvalidError
    from desk.llm.omlx import runtime_python
    roots = roots_at(tmp_path)
    with pytest.raises(ConfigInvalidError):
        update_config(roots, omlx_python='relative/bin/python')
    update_config(roots, omlx_python='/absolute/review-only/bin/python')
    assert runtime_python(roots) == Path('/absolute/review-only/bin/python')
    update_config(roots, gateway={'enabled': False})
    assert read_config(roots).extra['omlx_python'] == '/absolute/review-only/bin/python'
    update_config(roots, omlx_python='')
    assert runtime_python(roots) == tmp_path / 'runtimes/omlx/bin/python'


def test_failed_pinned_preload_fails_fast_and_releases_budget(tmp_path):
    bed = make_service(tmp_path, backend_kw={"health_script": [False]})
    bed.backend.startup_error = "oMLX preload failed: memory ceiling"
    bed.service.load('glm')
    final = bed.service.wait_settled()
    assert final['status'] == 'error'
    assert final['error']['code'] == 'backend_exited'
    assert 'memory ceiling' in final['error']['message']
    assert bed.proc.terminated
    assert any(c[0] == 'release' for c in bed.calls)
    bed.service.close()
