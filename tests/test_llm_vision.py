"""Multimodal validation and transport contracts, without loading weights."""
import base64
import json
from pathlib import Path

import pytest
from desk.llm.content import normalize_content
from desk.llm.backend import MlxLmBackend
from desk.gateway.openai_dialect import parse_request
from desk.gateway.anthropic_dialect import parse_request as anthropic
from desk.gateway.errors import GatewayReject
from tests.llm.llm_fakes import make_loaded

IMAGE = 'data:image/png;base64,' + base64.b64encode(b'fixture image bytes').decode()
BLOCK = {'type': 'image_url', 'image_url': {'url': IMAGE}}


def test_openai_and_anthropic_preserve_images_and_text():
    content = [{'type': 'text', 'text': 'Describe'}, BLOCK]
    req = parse_request({'messages': [{'role': 'user', 'content': content}], 'enable_thinking': False})
    assert req['chat_request']['messages'][0]['content'] == content
    assert req['chat_request']['enable_thinking'] is False
    req = anthropic({'max_tokens': 20, 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'Describe'}, {'type': 'image', 'source': {
            'type': 'base64', 'media_type': 'image/png', 'data': IMAGE.split(',')[1]}}]}]})
    assert req['chat_request']['messages'][0]['content'] == content


@pytest.mark.parametrize('url', ['https://example.com/a.png', 'file:///tmp/a.png', 'data:image/png;base64,%%%'])
def test_never_fetch_remote_urls_or_read_local_image_paths(url):
    with pytest.raises(ValueError):
        normalize_content([{'type': 'image_url', 'image_url': {'url': url}}])


def test_text_model_rejects_images_instead_of_dropping_them(tmp_path):
    from desk.llm.state import LlmRejected
    h = make_loaded(tmp_path)
    with pytest.raises(LlmRejected, match='视觉权重'):
        h.service.chat_completion({'messages': [{'role': 'user', 'content': [BLOCK]}]})


def test_vision_payload_uses_exact_local_path_and_thinking_setting(tmp_path):
    h = make_loaded(tmp_path)
    entry = h.entries[0]
    model = h.paths.models_root / entry.relpath
    (model / 'config.json').write_text(json.dumps({'vision_config': {'model_type': 'qwen3_5'}}))
    req = h.service._upstream_payload({'messages': [{'role': 'user', 'content': [BLOCK]}], 'enable_thinking': True}, entry)
    assert req['model'] == str(model)
    assert req['messages'][0]['content'] == [BLOCK]
    assert req['enable_thinking'] is True


def test_vision_spawn_isolates_dependencies_and_does_not_pass_text_cache_flags(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr('desk.llm.backend.subprocess.Popen', lambda argv, **kw: calls.append((argv, kw)))
    (tmp_path / 'config.json').write_text('{"vision_config":{"model_type":"qwen3_5"}}')
    MlxLmBackend(vision_python=Path('/vision/python'), vision_env={'PYTHONPATH': '/vision/libs'}).spawn(
        Path('/text/python'), tmp_path, 1234, tmp_path / 'server.log', ['--prompt-cache-size', '1'])
    argv, kw = calls[0]
    assert argv[:4] == ['/vision/python', '-s', '-m', 'mlx_vlm.server']
    assert '--prompt-cache-size' not in argv
    assert kw['env']['PYTHONPATH'] == '/vision/libs'


def test_invalid_thinking_setting_rejected():
    with pytest.raises(GatewayReject):
        parse_request({'messages': [{'role': 'user', 'content': 'x'}], 'enable_thinking': 'yes'})


def test_vision_stream_does_not_calibrate_from_stale_text_server_cache_logs(tmp_path):
    from types import SimpleNamespace
    calls = []
    chunks = [{'choices': [{'delta': {'content': 'red'}, 'finish_reason': 'stop'}],
               'usage': {'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11}}]
    h = make_loaded(tmp_path, backend_kw={'chunks': chunks, 'tail_text': 'Prompt Cache: 1 sequences, 12.40 GB'})
    h.service._budget = SimpleNamespace(record_turn=lambda *args: calls.append(args))
    model = h.paths.models_root / h.entries[0].relpath
    (model / 'config.json').write_text('{"vision_config":{"model_type":"qwen3_5"}}')
    assert list(h.service.chat_stream({'messages': [{'role': 'user', 'content': [BLOCK]}]}))[-1]['type'] == 'done'
    assert calls == []
