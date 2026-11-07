"""Owned, isolated oMLX server for the Qwen4 PLE/vision runtime.

Never connects to or changes the user's separately running oMLX instance.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import subprocess

from .backend import MlxLmBackend

OMLX_REVISION = "2165e75726ba83d9651dbaced61c97728da77bba"
MODEL_KEY = "qwen38-flash-next"
MODEL_ALIAS = "lmdesk-qwen38-flash-next"
CONTEXT = 262144
# Model-card estimate ~84 GiB resident + KV/prefill/vision/MTP headroom.
# This is a reservation, never a claim of local measurement.
RESERVATION_GIB = 100


def runtime_python(roots):
    from ..foundation.config import read_config
    configured = read_config(roots).extra.get("omlx_python", "")
    if not isinstance(configured, str) or (configured and not Path(configured).is_absolute()):
        raise OSError("omlx_python 必须为 Python 可执行文件的绝对路径")
    return Path(configured) if configured else roots.data_root / "runtimes" / "omlx" / "bin" / "python"


class LocalBackend(MlxLmBackend):
    def __init__(self, resolve_paths, **kwargs):
        super().__init__(**kwargs)
        self._roots = resolve_paths
        self._omlx = False
        self.startup_error = None

    @property
    def request_timeout(self):
        return 900.0 if self._omlx else 300.0

    def validate_entry(self, entry, model_path):
        if getattr(entry, "backend", "mlx-lm") != "omlx":
            return
        python = runtime_python(self._roots())
        if not python.is_file() or not os.access(python, os.X_OK):
            raise OSError("缺少独立 oMLX Python；请按 docs/qwen38-flash-next.md 安装并在设置中指定")
        config = json.loads((model_path / "config.json").read_text())
        if config.get("model_type") != "qwen4_exp" or not config.get("vision_config"):
            raise OSError("需要 qwen4_exp 完整视觉模型，不能使用仅文本或 stock MLX 替代")
        index = json.loads((model_path / "model.safetensors.index.json").read_text())
        shards = set(index.get("weight_map", {}).values())
        if not shards or any(not (model_path / shard).is_file() for shard in shards):
            raise OSError("模型权重分片不完整；请显式下载并校验后再加载")
        # Fail before evicting an existing model. Verify the exact audited source,
        # schema and Qwen4 patch; a matching version number alone is insufficient.
        probe = """import json, importlib.metadata as m
from omlx.model_settings import ModelSettings
from omlx.patches import mlx_vlm_qwen4_exp_compat
assert mlx_vlm_qwen4_exp_compat._APPLIED or mlx_vlm_qwen4_exp_compat.apply_mlx_vlm_qwen4_exp_compat_patch(), "Qwen4 registration failed"
from mlx_vlm.models.qwen4_exp import Model
s=ModelSettings(qwen4_ple_ssd_offload=True, mtp_enabled=True, mtp_fixed_depth=3, turboquant_kv_enabled=True, turboquant_kv_bits=4)
d=json.loads(m.distribution('omlx').read_text('direct_url.json') or '{}')
assert d.get('vcs_info',{}).get('commit_id') == %r, 'oMLX source revision mismatch'
""" % OMLX_REVISION
        try:
            result = subprocess.run([str(python), "-I", "-c", probe], capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired as exc:
            raise OSError("oMLX 兼容性检查超时") from exc
        if result.returncode:
            raise OSError("oMLX 兼容性检查失败: " + result.stderr[-2000:])

    def spawn(self, python, model_path, port, log_path, extra_args=None):
        self.startup_error = None
        config = json.loads((model_path / "config.json").read_text())
        self._omlx = config.get("model_type") == "qwen4_exp"
        if not self._omlx:
            return super().spawn(python, model_path, port, log_path, extra_args)
        roots = self._roots()
        base = roots.data_root / "omlx-qwen38"
        models = base / "models"
        models.mkdir(parents=True, exist_ok=True)
        link = models / MODEL_ALIAS
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise OSError(f"专用模型链接被其他文件占用: {link}")
        link.symlink_to(model_path.resolve(), target_is_directory=True)
        settings = {"version": 2, "models": {MODEL_ALIAS: {
            "is_pinned": True, "is_default": True,
            "qwen4_ple_ssd_offload": True,
            "mtp_enabled": True, "mtp_fixed_depth": 3,
            "turboquant_kv_enabled": True, "turboquant_kv_bits": 4,
            "turboquant_skip_last": True, "max_context_window": CONTEXT,
            "temperature": 1.0, "top_p": .95, "top_k": 20,
        }}}
        (base / "model_settings.json").write_text(json.dumps(settings, indent=2))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        argv = [str(runtime_python(roots)), "-I", "-c", "from omlx.cli import main; main()",
                "serve", "--base-path", str(base), "--model-dir", str(models),
                "--host", "127.0.0.1", "--port", str(port), "--headless",
                "--no-hf-cache", "--max-concurrent-requests", "1",
                "--memory-guard", "aggressive", "--hot-cache-max-size", "0",
                "--paged-ssd-cache-max-size", "8GB"]
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("OMLX_") or key in ("PYTHONPATH", "PYTHONHOME"):
                env.pop(key)
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        with log_path.open("ab") as log:
            return subprocess.Popen(argv, stdout=log, stderr=log, env=env)

    def health(self, port):
        if not self._omlx:
            return super().health(port)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            conn.request("GET", "/health")
            response = conn.getresponse()
            body = json.loads(response.read())
            ready = response.status == 200 and body.get("status") == "healthy"
            count = body.get("engine_pool", {}).get("loaded_count")
            if ready and count == 0:
                self.startup_error = "oMLX 模型预加载失败；请查看日志中的动态内存额度或加载错误"
            return ready and count == 1
        except (OSError, ValueError, AttributeError):
            return False
        finally:
            conn.close()
