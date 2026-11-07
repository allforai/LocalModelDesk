"""Pi provider lifecycle behind status/apply/check; never edits Pi's settings.

Only bundled code is installed. A receipt records the installed digest and local
endpoints. Modified files, foreign receipts and symlinks are never overwritten or
removed. Exact copies of known manual releases can be adopted by explicit install.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
from urllib.request import urlopen

from .brew import BrewInstall

OWNER = "LocalModelDesk"
FORMAT = 1
EXTENSION = Path(".pi/agent/extensions/lmdesk.ts")
RECEIPT = Path(".pi/agent/localmodeldesk.json")
# Exact manual copies shipped before the settings installer existed, not a marker
# that could also appear in a user's modified file.
LEGACY_HASHES = frozenset({
    "6423b49d663a5f6613748fc723191aec812dac81446360978783baf6a720a85c",
    "2968070130c41e57470037469de15122043ee4e28c9e0842518b41d41dbd8757",
})


class IntegrationError(Exception):
    def __init__(self, message: str, code: str = "pi_integration_conflict", http: int = 409):
        super().__init__(message)
        self.code, self.http = code, http


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _probe(url: str) -> dict:
    with urlopen(url, timeout=3) as response:
        return json.load(response)


def _which_pi(_name):
    found = shutil.which("pi")
    if found:
        return found
    # Finder-launched apps need not inherit Homebrew's PATH.
    return next((str(p) for p in (Path("/opt") / "homebrew/bin/pi", Path("/usr/local/bin/pi"))
                 if p.is_file() and os.access(p, os.X_OK)), None)


def _gateway_url(status: dict) -> str:
    host = status.get("host") or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    if host == "::":
        host = "::1"
    if not re.fullmatch(r"[a-zA-Z0-9.:-]+", host):
        raise IntegrationError("网关主机地址无效，请先在设置中修正", "invalid_gateway")
    port = status.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        raise IntegrationError("网关端口无效，请先在设置中修正", "invalid_gateway")
    authority = f"[{host}]" if ":" in host else host
    return f"http://{authority}:{port}/v1"


def _atomic_write(path: Path, data: bytes, *, absent: bool = False, mode: int = 0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".lmdesk-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        if absent:
            # Unlike replace, link refuses a file that appeared after inspection.
            os.link(name, path)
        else:
            os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class PiIntegrationService:
    def __init__(self, resources_root: Path, mode: str, home: Path, *,
                 gateway_status, control_url, which=_which_pi, probe=_probe, brew_installer=None):
        root = Path(resources_root)
        self.provider = (root / "desk/pi_integration/bundled/lmdesk.ts" if mode == "bundle"
                         else root / "integrations/pi/lmdesk.ts")
        self.home = Path(home)
        self.extension, self.receipt = self.home / EXTENSION, self.home / RECEIPT
        self._gateway_status, self._control_url = gateway_status, control_url
        self._which, self._probe = which, probe
        self._lock = threading.RLock()
        self._brew = brew_installer if brew_installer is not None else BrewInstall()
        self._closed = False

    def _inspect(self):
        gateway = self._gateway_status()
        result = {"state": "absent", "message": "尚未安装 pi 本地编程接入", "path": str(self.extension),
                  "config_path": str(self.receipt), "pi_detected": bool(self._which("pi")),
                  "gateway_enabled": bool(gateway.get("enabled")),
                  "gateway_listening": bool(gateway.get("listening")),
                  "can_install": False, "can_remove": False,
                  "gateway_url": None, "desk_url": self._control_url(),
                  "models": json.loads(Path(__file__).with_name("models.json").read_text(encoding="utf-8"))}
        data = None
        receipt = None
        try:
            defaults = {"gateway_url": _gateway_url(gateway), "desk_url": self._control_url()}
            result.update(defaults)
            # Do not follow a user's directory symlink to write somewhere else.
            parents = [self.home / ".pi", self.home / ".pi/agent", self.extension.parent]
            if any(p.is_symlink() or (p.exists() and not p.is_dir()) for p in parents):
                raise IntegrationError("pi 配置目录是链接或被文件占用，台面不会改动；请手动安装")
            if self.extension.is_symlink() or self.receipt.is_symlink():
                raise IntegrationError("已有同名链接，台面不会覆盖或移除")
            if self.receipt.exists():
                try:
                    receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
                except (ValueError, UnicodeError):
                    raise IntegrationError("连接配置已有内容但不是有效的台面管理记录，不会覆盖") from None
                if (not isinstance(receipt, dict) or receipt.get("owner") != OWNER
                        or type(receipt.get("format")) is not int or receipt.get("format") != FORMAT
                        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("installed_sha256", "")))):
                    raise IntegrationError("连接配置不属于台面，不会覆盖")
            try:
                data = self.provider.read_bytes() or None
            except OSError:
                pass
            source_hash = _digest(data) if data is not None else None
            actual = self.extension.read_bytes() if self.extension.exists() else None
            actual_hash = _digest(actual) if actual is not None else None
            if actual is not None:
                if receipt and actual_hash in {receipt["installed_sha256"], source_hash}:
                    current = (actual_hash == source_hash and all(receipt.get(k) == v for k, v in defaults.items()))
                    result.update(state="installed" if current else "stale",
                                  message="原生工具调用接入已安装" if current else "扩展或连接配置需更新",
                                  can_remove=True)
                elif receipt is None and actual_hash in LEGACY_HASHES | ({source_hash} if source_hash else set()):
                    result.update(state="manual", message="检测到手动安装的台面扩展，可接管并更新")
                else:
                    raise IntegrationError("已有同名文件或扩展已被修改，台面不会覆盖或移除")
            elif receipt:
                result["can_remove"] = True  # clean up our own orphaned receipt
            result["can_install"] = data is not None and (result["state"] != "installed" or not result["pi_detected"])
            if data is None:
                result.update(state="error", message="安装包缺少 pi 扩展，请重新安装新版台面", can_install=False)
        except IntegrationError as error:
            result.update(state="error" if error.code == "invalid_gateway" else "conflict",
                          message=str(error), can_install=False, can_remove=False)
        except OSError as error:
            result.update(state="error", message=f"无法读取 pi 接入文件：{error.strerror or error}",
                          can_install=False, can_remove=False)
        return result, data, receipt

    def status(self) -> dict:
        with self._lock:
            state = self._inspect()[0]
            state["pi_install"] = self._brew.status()
            if state["pi_install"]["state"] == "running":
                state.update(state="installing", message=state["pi_install"]["message"], can_install=False, can_remove=False)
            return state

    def _finish_install(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("台面已退出；请重新打开后安装接入扩展")
            if not self._which("pi"):
                raise RuntimeError("brew 已结束但未找到 pi 命令，请查看 Homebrew 输出并检查安装位置")
            self._apply_extension("install")

    def apply(self, action: str) -> dict:
        if not isinstance(action, str) or action not in {"install", "remove"}:
            raise ValueError("action 须为 install 或 remove")
        with self._lock:
            if self._closed:
                raise IntegrationError("台面正在退出")
            if self._brew.status()["state"] == "running":
                raise IntegrationError("正在安装 pi，请等待安装结束")
            if action == "install" and not self._which("pi"):
                state = self._inspect()[0]
                if not state["can_install"] and state["state"] != "installed":
                    raise IntegrationError(state["message"])
                try:
                    self._brew.start(self._finish_install)
                except RuntimeError as error:
                    raise IntegrationError(str(error), "pi_install_failed") from error
                return self.status()
            self._apply_extension(action)
            self._brew.reset()
            return self.status()

    def close(self):
        with self._lock:
            self._closed = True
        self._brew.close()

    def _apply_extension(self, action: str) -> dict:
        if not isinstance(action, str) or action not in {"install", "remove"}:
            raise ValueError("action 须为 install 或 remove")
        with self._lock:
            state, data, receipt = self._inspect()
            try:
                if action == "remove":
                    if not state["can_remove"]:
                        if state["state"] == "absent":
                            return state
                        raise IntegrationError(state["message"])
                    self.extension.unlink(missing_ok=True)
                    self.receipt.unlink(missing_ok=True)
                else:
                    if state["state"] == "installed":
                        return state
                    if not state["can_install"]:
                        raise IntegrationError(state["message"])
                    desired = {"owner": OWNER, "format": FORMAT, "installed_sha256": _digest(data),
                               "gateway_url": state["gateway_url"], "desk_url": state["desk_url"]}
                    # An exact manual current copy is adopted without touching its bytes.
                    if not self.extension.exists() or self.extension.read_bytes() != data:
                        _atomic_write(self.extension, data, absent=not self.extension.exists(), mode=0o644)
                    _atomic_write(self.receipt, (json.dumps(desired, ensure_ascii=False, indent=2) + "\n").encode(),
                                  absent=receipt is None)
            except OSError as error:
                raise IntegrationError(f"写入 pi 接入失败：{error.strerror or error}", "pi_integration_write_failed") from error
            return self._inspect()[0]

    def check(self) -> dict:
        state = self.status()
        if state["state"] != "installed":
            return {"ok": False, "message": "请先安装或更新 pi 接入；" + state["message"]}
        if not state["pi_detected"]:
            return {"ok": False, "message": "未检测到 pi 命令；请先安装 pi，再执行 /reload"}
        if not state["gateway_enabled"] or not state["gateway_listening"]:
            return {"ok": False, "message": "对外接口未监听；请在设置中开启并保存应用"}
        try:
            control = self._probe(state["desk_url"] + "/api/llm/status")
            if not isinstance(control, dict) or not isinstance(control.get("state"), dict) or not isinstance(control["state"].get("status"), str):
                raise ValueError("控制面返回了无效的模型状态")
            listing = self._probe(state["gateway_url"] + "/models")
            if not isinstance(listing, dict) or listing.get("object") != "list" or not isinstance(listing.get("data"), list):
                raise ValueError("返回的不是 OpenAI 模型列表")
        except (OSError, ValueError) as error:
            return {"ok": False, "message": f"连接检查失败：{error}"}
        message = "扩展已安装，控制面与网关可达；在 pi 执行 /reload，再用 /model 选择 lmdesk"
        if not listing["data"]:
            message += "。尚未加载模型，pi 的第一条请求会按需加载"
        return {"ok": True, "message": message}
