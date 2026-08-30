#!/usr/bin/env python3
"""Local model desk: mlx-lm chat + MiniMax H3 + Music 3."""
from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
GUI = Path(__file__).resolve().parent
ROOT = GUI.parent
H3_ROOT = ROOT / "minimax-h3"
MUSIC_PY = ROOT / ".venv-music3" / "bin" / "python3"
OUT_DIR = ROOT / "outputs"
HISTORY_FILE = OUT_DIR / "history.jsonl"
CHAT_FILE = GUI / "chat-history.json"
MLX_H3 = HOME / ".local" / "bin" / "mlx-h3"
DESK_PY = ROOT / ".venv-desk" / "bin" / "python"
LM_PORT = 8767
LM_API = f"http://127.0.0.1:{LM_PORT}/v1"
LM_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer local",
}
HOST, PORT = "127.0.0.1", 8766
HEAVY_LLM_GB = 50
MODELS_ROOT = ROOT / "llms"
MODEL_CATALOG = [
    {
        "key": "huihui-glm-4.7-flash-abliterated-mlx",
        "name": "GLM 4.7 Flash 越狱 4bit",
        "path": MODELS_ROOT / "huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit",
        "gb": 16.9,
        "vision": False,
        "quant": "4bit",
        "params": "30B-A3B",
    },
    {
        "key": "superqwen3.8-27b-abliterated-mlx",
        "name": "SuperQwen3.8 27B 越狱 4bit",
        "path": MODELS_ROOT / "Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
        "gb": 16.1,
        "vision": True,
        "quant": "4bit",
        "params": "27B",
    },
    {
        "key": "huihui-qwen3.8-27b-abliterated-mlx",
        "name": "Qwen3.8 27B 越狱 8bit",
        "path": MODELS_ROOT / "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
        "gb": 29.5,
        "vision": True,
        "quant": "8bit",
        "params": "27B",
    },
    {
        "key": "huihui-gemma-4-31b-it-v2-mlx",
        "name": "Gemma 4 31B 越狱 8bit 视觉",
        "path": MODELS_ROOT / "thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
        "gb": 33.8,
        "vision": True,
        "quant": "8bit",
        "params": "31B",
    },
    {
        "key": "huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated-mlx",
        "name": "Qwen3.6 35B-A3B 越狱 8bit",
        "path": MODELS_ROOT / "mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
        "gb": 36.8,
        "vision": False,
        "quant": "8bit",
        "params": "35B-A3B",
    },
    {
        "key": "llama-3.3-70b-instruct-abliterated-mlx",
        "name": "Llama 3.3 70B 越狱 8bit",
        "path": MODELS_ROOT / "divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
        "gb": 75.0,
        "vision": False,
        "quant": "8bit",
        "params": "70B",
    },
]

_lock = threading.Lock()
_job: dict = {
    "status": "idle",
    "kind": None,
    "log": "",
    "output": None,
    "error": None,
    "started": None,
}
_proc: subprocess.Popen | None = None
_llm_load: dict = {"status": "idle", "model": None, "error": None}
_job_params: dict = {}
_llm_server: subprocess.Popen | None = None


def _append(msg: str) -> None:
    with _lock:
        _job["log"] += msg


def _append_history(entry: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_history(limit: int = 80) -> list[dict]:
    items: list[dict] = []
    if HISTORY_FILE.exists():
        for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    known = {i.get("output") for i in items if i.get("output")}
    if OUT_DIR.exists():
        for p in OUT_DIR.iterdir():
            if p.suffix.lower() in {".mp4", ".wav", ".m4a", ".webm"} and p.name not in known:
                kind = "h3" if p.name.startswith("h3-") else "music" if p.name.startswith("music3-") else "file"
                items.append(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(p.stat().st_mtime)),
                        "kind": kind,
                        "output": p.name,
                        "status": "done",
                        "prompt": None,
                        "orphan": True,
                    }
                )
    items.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return items[:limit]


def _catalog_by_key(key: str) -> dict | None:
    for m in MODEL_CATALOG:
        if m["key"] == key:
            return m
    return None


def _llm_alive() -> bool:
    global _llm_server
    if _llm_server is None:
        return False
    if _llm_server.poll() is not None:
        _llm_server = None
        return False
    return True


def _unload_llms() -> None:
    global _llm_server
    if _llm_server is not None and _llm_server.poll() is None:
        _llm_server.terminate()
        try:
            _llm_server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _llm_server.kill()
    _llm_server = None
    with _lock:
        _llm_load.update(status="idle", model=None, error=None)
    _append("Unloaded MLX LLM.\n")


def _loaded_llms() -> list[dict]:
    if not _llm_alive():
        return []
    with _lock:
        key = _llm_load.get("model")
    meta = _catalog_by_key(key or "") or {}
    return [
        {
            "identifier": str(meta.get("path") or key),
            "modelKey": key,
            "displayName": meta.get("name") or key,
            "sizeBytes": int((meta.get("gb") or 0) * 1e9),
            "path": str(meta.get("path") or ""),
        }
    ]


def _disk_llms() -> list[dict]:
    out = []
    for m in MODEL_CATALOG:
        path = Path(m["path"])
        if not path.exists():
            continue
        gb = float(m["gb"])
        out.append(
            {
                "key": m["key"],
                "name": m["name"],
                "path": str(path),
                "gb": gb,
                "vision": bool(m.get("vision")),
                "quant": m.get("quant"),
                "params": m.get("params"),
                "heavy": gb >= HEAVY_LLM_GB,
            }
        )
    out.sort(key=lambda x: (x["heavy"], x["gb"], x["name"] or ""))
    return out


def _planner() -> dict:
    loaded = []
    for m in _loaded_llms():
        ident = m.get("identifier") or m.get("modelKey") or m.get("path")
        size = m.get("sizeBytes") or 0
        loaded.append(
            {
                "id": ident,
                "key": m.get("modelKey") or ident,
                "name": m.get("displayName") or ident,
                "gb": round(size / 1e9, 1) if size else None,
            }
        )
    with _lock:
        media = {k: _job[k] for k in ("status", "kind", "error", "output", "started")}
        llm_load = dict(_llm_load)
    heavy = any((x.get("gb") or 0) >= HEAVY_LLM_GB for x in loaded)
    media_busy = media["status"] == "running"
    if media_busy and loaded:
        advice = "媒体生成中仍挂着 LLM，内存可能打架。生成前会尝试卸模型。"
    elif media_busy:
        advice = "正在出片/出歌，先别加载 70B。"
    elif heavy:
        advice = "70B 已加载。要跑 H3/Music 会先自动卸掉它。"
    elif loaded:
        advice = "可以聊天。点视频/音乐会先卸掉当前 LLM。"
    else:
        advice = "空闲。聊天请先加载一个模型；70B 和 H3 不要同时驻留。"
    return {
        "ram_gb": 128,
        "loaded": loaded,
        "llm_load": llm_load,
        "media": media,
        "advice": advice,
        "conflict": media_busy and bool(loaded),
    }


def _run_cmd(cmd: list[str], output: Path) -> None:
    global _proc
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with _lock:
            _proc = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            _append(line)
        code = proc.wait()
        with _lock:
            _proc = None
            started = _job.get("started")
            elapsed = (time.time() - started) if started else None
            params = dict(_job_params)
            if code == 0 and output.exists():
                _job["status"] = "done"
                _job["output"] = output.name
                _job["error"] = None
                status = "done"
            else:
                _job["status"] = "error"
                _job["error"] = f"exit {code}"
                if output.exists():
                    _job["output"] = output.name
                status = "error"
        _append_history(
            {
                "kind": params.get("kind") or _job.get("kind"),
                "status": status,
                "output": output.name if output.exists() else None,
                "elapsed_s": round(elapsed, 1) if elapsed is not None else None,
                "prompt": params.get("prompt") or params.get("caption"),
                "params": params,
            }
        )
    except Exception as exc:
        with _lock:
            _proc = None
            _job["status"] = "error"
            _job["error"] = str(exc)
        _append_history(
            {
                "kind": _job_params.get("kind") or _job.get("kind"),
                "status": "error",
                "output": None,
                "prompt": _job_params.get("prompt") or _job_params.get("caption"),
                "params": dict(_job_params),
                "error": str(exc),
            }
        )


def _run_h3(prompt: str, width: int, height: int, frames: int, steps: int) -> None:
    global _job_params
    with _lock:
        _job_params = {"kind": "h3", "prompt": prompt, "width": width, "height": height, "frames": frames, "steps": steps}
    _unload_llms()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = OUT_DIR / f"h3-{stamp}.mp4"
    cmd = [
        str(MLX_H3),
        prompt,
        "--tokenizer", str(H3_ROOT / "tokenizer" / "tokenizer.json"),
        "--text-encoder", str(H3_ROOT / "mlx-8bit" / "te_qwen3vl_a8g32.safetensors"),
        "--dit", str(H3_ROOT / "mlx-8bit" / "dit_fl2va_a8g32.safetensors"),
        "--ref-dit", str(H3_ROOT / "mlx-8bit" / "dit_ref2va_a8g32.safetensors"),
        "--video-vae", str(H3_ROOT / "bf16" / "vae" / "minimax_h3_video_vae_fp16.safetensors"),
        "--audio-vae", str(H3_ROOT / "bf16" / "vae" / "minimax_h3_audio_vae_fp32.safetensors"),
        "--width", str(width),
        "--height", str(height),
        "--frames", str(frames),
        "--steps", str(steps),
        "--budget", "70",
        "--output", str(output),
    ]
    _run_cmd(cmd, output)


def _run_music(caption: str, lyrics: str, duration: float) -> None:
    global _job_params
    with _lock:
        _job_params = {"kind": "music", "caption": caption, "lyrics": lyrics, "duration": duration, "prompt": caption}
    _unload_llms()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = OUT_DIR / f"music3-{stamp}.wav"
    script = ROOT / "run-music3.py"
    cmd = [
        str(MUSIC_PY),
        str(script),
        "--caption", caption,
        "--lyrics", lyrics,
        "--duration", str(duration),
        "--output", str(output),
    ]
    _run_cmd(cmd, output)


def _load_llm(key: str) -> None:
    global _llm_server
    meta = _catalog_by_key(key)
    if not meta or not Path(meta["path"]).exists():
        with _lock:
            _llm_load.update(status="error", model=key, error="找不到模型目录")
        return
    with _lock:
        if _job["status"] == "running":
            _llm_load.update(status="error", model=key, error="媒体正在运行，拒绝加载 LLM")
            return
        _llm_load.update(status="loading", model=key, error=None)
    _unload_llms()
    with _lock:
        _llm_load.update(status="loading", model=key, error=None)
    log = GUI / "mlx-lm.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as fh:
        proc = subprocess.Popen(
            [
                str(DESK_PY),
                "-m",
                "mlx_lm",
                "server",
                "--model",
                str(meta["path"]),
                "--host",
                "127.0.0.1",
                "--port",
                str(LM_PORT),
                "--allowed-origins",
                "*",
            ],
            stdout=fh,
            stderr=fh,
        )
    _llm_server = proc
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            with _lock:
                _llm_load.update(status="error", error="mlx-lm server 退出，见 mlx-lm.log")
            _llm_server = None
            return
        try:
            urllib.request.urlopen(LM_API + "/models", timeout=1)
            with _lock:
                _llm_load.update(status="loaded", error=None)
            return
        except Exception:
            time.sleep(0.4)
    with _lock:
        _llm_load.update(status="error", error="加载超时")


def _outputs() -> list[dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(OUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in {".mp4", ".wav", ".m4a", ".webm"}:
            items.append({"name": p.name, "size": p.stat().st_size, "mtime": int(p.stat().st_mtime)})
    return items[:50]


def _chat_payload(body: dict, stream: bool) -> tuple[str, bytes] | dict:
    with _lock:
        media_busy = _job["status"] == "running"
    if media_busy:
        return {"error": "媒体正在生成，先等它结束再聊。"}
    if not _llm_alive():
        return {"error": "还没有加载模型。"}
    model = body.get("model")
    if not model:
        loaded = _planner()["loaded"]
        if not loaded:
            return {"error": "还没有加载模型。"}
        model = loaded[0]["id"]
    payload = json.dumps(
        {
            "model": model,
            "messages": body.get("messages") or [],
            "temperature": float(body.get("temperature") or 0.7),
            "max_tokens": int(body.get("max_tokens") or 2048),
            "stream": stream,
        }
    ).encode()
    return model, payload


def _chat(body: dict) -> dict:
    built = _chat_payload(body, stream=False)
    if isinstance(built, dict):
        return built
    model, payload = built
    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "--http1.1",
                "--max-time",
                "120",
                "http://127.0.0.1:8767/v1/chat/completions",
                "-H",
                "Content-Type: application/json",
                "-H",
                "Authorization: Bearer lm-studio",
                "-d",
                payload.decode("utf-8"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return {"error": (proc.stderr or proc.stdout or "curl failed")[:800]}
        data = json.loads(proc.stdout)
    except Exception as exc:
        return {"error": str(exc)}
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    msg = (message.get("content") or "").strip()
    thinking = (message.get("reasoning_content") or message.get("reasoning") or "").strip()
    if not msg:
        msg = thinking
    try:
        CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        messages = list(body.get("messages") or [])
        messages.append({"role": "assistant", "content": msg})
        CHAT_FILE.write_text(
            json.dumps({"model": model, "messages": messages[-40:]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return {"content": msg, "thinking": thinking, "raw": data.get("usage")}


HTML = r"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>本地模型台</title>
<style>
  :root { color-scheme: dark; --bg:#0f1115; --card:#181c24; --line:#2a3140; --fg:#e8edf5; --muted:#8b95a8; --acc:#6ee7b7; --btn:#2563eb; --warn:#fbbf24; --bad:#f87171; }
  * { box-sizing: border-box; }
  body { margin:0; font: 15px/1.45 ui-sans-serif, system-ui; background:var(--bg); color:var(--fg); }
  header { padding:16px 24px 8px; }
  h1 { margin:0; font-size:20px; }
  .plan { margin:8px 24px 12px; padding:12px 14px; border:1px solid var(--line); border-radius:12px; background:var(--card); display:flex; gap:18px; flex-wrap:wrap; align-items:center; }
  .plan b { color:var(--acc); }
  .plan.warn { border-color:#854d0e; }
  nav { display:flex; gap:8px; padding:0 24px 12px; }
  nav button { background:transparent; color:var(--muted); border:1px solid var(--line); border-radius:999px; padding:6px 14px; cursor:pointer; }
  nav button.on { color:var(--bg); background:var(--acc); border-color:var(--acc); }
  main { display:grid; grid-template-columns: 1.15fr .85fr; gap:16px; padding:0 24px 24px; }
  @media (max-width: 960px) { main { grid-template-columns: 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; }
  label { display:block; color:var(--muted); font-size:12px; margin:10px 0 4px; }
  textarea, input, select { width:100%; background:#0d1016; color:var(--fg); border:1px solid var(--line); border-radius:8px; padding:10px; font: inherit; }
  textarea { min-height:90px; resize:vertical; }
  #chatlog { min-height:240px; max-height:360px; overflow:auto; background:#0d1016; border-radius:8px; padding:10px; }
  .msg { margin:0 0 10px; }
  .msg.user { color:#93c5fd; }
  .msg.assistant { color:var(--fg); }
  .think { color:var(--muted); font-size:13px; margin:4px 0 8px; }
  .think summary { cursor:pointer; color:#fbbf24; }
  .row { display:flex; gap:10px; }
  .row > * { flex:1; }
  .go { margin-top:12px; width:100%; background:var(--btn); color:white; border:0; border-radius:10px; padding:12px; font-weight:600; cursor:pointer; }
  .go.secondary { background:#334155; }
  .go:disabled { opacity:.5; cursor:not-allowed; }
  pre { white-space:pre-wrap; background:#0d1016; border-radius:8px; padding:10px; min-height:140px; max-height:240px; overflow:auto; font:12px/1.4 ui-monospace, monospace; color:#c9d4e5; }
  video, audio { width:100%; border-radius:10px; margin-top:10px; background:black; }
  .list button, .list a { display:block; width:100%; text-align:left; color:var(--acc); text-decoration:none; padding:8px 0; border:0; border-bottom:1px solid var(--line); background:transparent; cursor:pointer; font: inherit; }
  .list .meta { color:var(--muted); font-size:12px; }
  .err { color:var(--bad); }
  .hint { color:var(--muted); font-size:13px; }
</style>
<body>
<header>
  <h1>本地模型台</h1>
  <p class="hint" style="margin:6px 0 0">聊天走本机 mlx-lm，视频/音乐走 MLX。开机自启。70B 和 H3 不要同时驻留。</p>
</header>
<div class="plan" id="plan">规划加载中…</div>
<nav>
  <button id="tab-chat" class="on" onclick="tab('chat')">聊天</button>
  <button id="tab-h3" onclick="tab('h3')">H3 视频</button>
  <button id="tab-music" onclick="tab('music')">Music 3</button>
</nav>
<main>
  <section class="card">
    <div id="form-chat">
      <label>模型</label>
      <div class="row">
        <select id="model"></select>
      </div>
      <div class="row">
        <button class="go" id="btn-load" onclick="loadModel()">加载</button>
        <button class="go secondary" onclick="unloadModel()">卸载全部</button>
      </div>
      <label>对话</label>
      <div id="chatlog"></div>
      <textarea id="chatin" placeholder="输入消息，Enter 发送，Shift+Enter 换行"></textarea>
      <button class="go" id="btn-send" onclick="sendChat()">发送</button>
    </div>
    <div id="form-h3" hidden>
      <label>提示词</label>
      <textarea id="prompt">夜晚雨中的城市街道，霓虹倒影在积水里，远处车灯掠过，立体环境声</textarea>
      <div class="row">
        <div><label>画幅</label>
          <select id="size">
            <option value="512x288">512×288 草稿</option>
            <option value="768x448">768×448</option>
            <option value="1024x576">1024×576 宽屏</option>
          </select>
        </div>
        <div><label>帧数</label><input id="frames" type="number" value="73" min="17" max="362"></div>
        <div><label>步数</label><input id="steps" type="number" value="10" min="4" max="40"></div>
      </div>
      <button class="go" id="go-h3" onclick="startH3()">生成视频（会先卸 LLM）</button>
    </div>
    <div id="form-music" hidden>
      <label>风格描述</label>
      <textarea id="caption">温暖民谣，亲密女声，指弹吉他，轻钢琴</textarea>
      <label>歌词</label>
      <textarea id="lyrics">[verse]
晨光穿过房间
一条安静的路带我回家
[chorus]
轻轻地，世界开始呼吸</textarea>
      <label>时长（秒）</label>
      <input id="duration" type="number" value="30" min="5" max="180">
      <button class="go" id="go-music" onclick="startMusic()">生成歌曲（会先卸 LLM）</button>
    </div>
  </section>
  <section class="card">
    <label>作业日志</label>
    <div id="status">空闲</div>
    <pre id="log"></pre>
    <div id="player"></div>
    <label>生成历史</label>
    <div class="list" id="files"></div>
  </section>
</main>
<script>
let kind = 'chat';
const chat = [];
function tab(k){
  kind = k;
  ['chat','h3','music'].forEach(x => {
    document.getElementById('tab-'+x).classList.toggle('on', k===x);
    document.getElementById('form-'+x).hidden = k!==x;
  });
}
async function api(path, opt){
  const r = await fetch(path, opt);
  return r.json();
}
function setMediaBusy(b){
  document.getElementById('go-h3').disabled = b;
  document.getElementById('go-music').disabled = b;
  document.getElementById('btn-load').disabled = b;
  document.getElementById('btn-send').disabled = b || !!window._chatting;
}
async function refreshModels(){
  const models = await api('/api/llm/models');
  const plan = await api('/api/planner');
  const sel = document.getElementById('model');
  const loadedId = plan.loaded[0] && (plan.loaded[0].key || plan.loaded[0].id);
  sel.innerHTML = models.map(m => {
    const tag = (m.heavy ? ' · 打满内存' : '') + (m.vision ? ' · 视觉' : '') + (m.quant ? ' · '+m.quant : '');
    return `<option value="${m.key}">${m.name} (${m.gb}GB${tag})</option>`;
  }).join('');
  if (loadedId && [...sel.options].some(o => o.value===loadedId)) sel.value = loadedId;
  else if (sel.value && [...sel.options].some(o => o.value===sel.value)) {}
  else {
    const light = models.find(m => !m.heavy);
    if (light) sel.value = light.key;
  }
}
async function loadModel(){
  const sel = document.getElementById('model');
  const key = sel.value;
  const opt = sel.selectedOptions[0];
  if (opt && opt.text.includes('打满内存') && !confirm('这个模型会打满 128GB，H3/音乐会先被挤掉。继续加载？')) return;
  await api('/api/llm/load', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key})});
}
async function unloadModel(){
  await api('/api/llm/unload', {method:'POST'});
}
function renderChat(){
  document.getElementById('chatlog').innerHTML = chat.map(m => {
    if (m.role==='user') return `<div class="msg user"><b>你:</b> ${escapeHtml(m.content||'')}</div>`;
    const think = m.thinking ? `<details class="think" ${m.content?'':'open'}><summary>${m.content?'思考':'思考中'}</summary>${escapeHtml(m.thinking)}</details>` : '';
    const body = escapeHtml(m.content||'') || (m.thinking ? '' : '…');
    return `<div class="msg assistant"><b>模型:</b>${think}<div>${body}</div></div>`;
  }).join('');
  const el = document.getElementById('chatlog');
  el.scrollTop = el.scrollHeight;
}
function escapeHtml(s){
  return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
}
async function sendChat(){
  const input = document.getElementById('chatin');
  const text = input.value.trim();
  if (!text) return;
  chat.push({role:'user', content:text});
  const draft = {role:'assistant', content:'', thinking:''};
  chat.push(draft);
  input.value = '';
  renderChat();
  window._chatting = true;
  document.getElementById('btn-send').disabled = true;
  const plan = await api('/api/planner');
  const model = (plan.loaded[0] && plan.loaded[0].id) || document.getElementById('model').value;
  const res = await fetch('http://127.0.0.1:8767/v1/chat/completions', {
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer lm-studio'},
    body: JSON.stringify({
      model,
      messages: chat.filter(m => m !== draft).map(m => ({role:m.role, content:m.content||''})),
      temperature: 0.7,
      max_tokens: 2048,
      stream: true
    })
  });
  if (!res.ok || !res.body) {
    draft.content = '请求失败';
    renderChat();
    window._chatting = false;
    document.getElementById('btn-send').disabled = false;
    return;
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    buf += dec.decode(value, {stream:true});
    const parts = buf.split('\n');
    buf = parts.pop() || '';
    for (const line of parts) {
      const s = line.trim();
      if (!s.startsWith('data:')) continue;
      const data = s.slice(5).trim();
      if (data === '[DONE]') continue;
      let obj;
      try { obj = JSON.parse(data); } catch { continue; }
      if (obj.error) { draft.content = String(obj.error); continue; }
      const delta = ((obj.choices||[{}])[0].delta)||{};
      draft.thinking += delta.reasoning_content || delta.reasoning || '';
      draft.content += delta.content || '';
    }
    renderChat();
  }
  if (!draft.content && draft.thinking) draft.content = draft.thinking;
  if (!draft.content) draft.content = '(空)';
  renderChat();
  window._chatting = false;
  document.getElementById('btn-send').disabled = false;
  fetch('/api/chat/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({model, messages: chat.slice(-40)})});
}
document.getElementById('chatin').addEventListener('keydown', e => {
  if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
async function startH3(){
  const [w,h] = document.getElementById('size').value.split('x').map(Number);
  setMediaBusy(true);
  await api('/api/h3', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    prompt: document.getElementById('prompt').value, width:w, height:h,
    frames: Number(document.getElementById('frames').value),
    steps: Number(document.getElementById('steps').value)
  })});
}
async function startMusic(){
  setMediaBusy(true);
  await api('/api/music', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    caption: document.getElementById('caption').value,
    lyrics: document.getElementById('lyrics').value,
    duration: Number(document.getElementById('duration').value)
  })});
}
function renderPlayer(name){
  if(!name){ document.getElementById('player').innerHTML=''; return; }
  const url = '/file/' + encodeURIComponent(name);
  if(name.endsWith('.mp4') || name.endsWith('.webm'))
    document.getElementById('player').innerHTML = `<video controls src="${url}"></video>`;
  else
    document.getElementById('player').innerHTML = `<audio controls src="${url}"></audio>`;
}
function applyHistory(item){
  if (item.output) { window._playing = item.output; renderPlayer(item.output); }
  const p = item.params || {};
  if (item.kind==='h3') {
    tab('h3');
    if (p.prompt || item.prompt) document.getElementById('prompt').value = p.prompt || item.prompt;
    if (p.width && p.height) document.getElementById('size').value = p.width+'x'+p.height;
    if (p.frames) document.getElementById('frames').value = p.frames;
    if (p.steps) document.getElementById('steps').value = p.steps;
  }
  if (item.kind==='music') {
    tab('music');
    if (p.caption || item.prompt) document.getElementById('caption').value = p.caption || item.prompt;
    if (p.lyrics) document.getElementById('lyrics').value = p.lyrics;
    if (p.duration) document.getElementById('duration').value = p.duration;
  }
}
async function tick(){
  const p = await api('/api/planner');
  const loaded = p.loaded.map(m => m.name + (m.gb?` ${m.gb}GB`:'')).join('、') || '未加载';
  const media = p.media.status==='running' ? (p.media.kind||'media')+' 生成中' : (p.media.status||'空闲');
  const el = document.getElementById('plan');
  el.className = 'plan' + (p.conflict ? ' warn' : '');
  el.innerHTML = `<div><b>内存</b> ${p.ram_gb}GB</div><div><b>LLM</b> ${escapeHtml(loaded)}</div><div><b>媒体</b> ${escapeHtml(media)}</div><div>${escapeHtml(p.advice)}</div>`;
  const s = await api('/api/status');
  document.getElementById('status').textContent = s.status + (s.error ? ' — '+s.error : '');
  document.getElementById('status').className = s.status==='error' ? 'err' : '';
  document.getElementById('log').textContent = s.log || p.llm_load.error || '';
  const busy = s.status==='running' || p.llm_load.status==='loading';
  setMediaBusy(busy);
  if(s.output && s.output !== window._playing) { window._playing = s.output; renderPlayer(s.output); }
  const files = await api('/api/history');
  window._hist = files;
  document.getElementById('files').innerHTML = files.map((f,i) => {
    const title = escapeHtml((f.prompt || f.output || '未命名').slice(0,72));
    const elapsed = f.elapsed_s ? ` · ${f.elapsed_s}s` : '';
    const spec = f.params && f.params.width ? ` · ${f.params.width}x${f.params.height} ${f.params.steps||''}step` : '';
    return `<button type="button" onclick="applyHistory(window._hist[${i}])"><div>${title}</div><div class="meta">${escapeHtml(f.kind||'')} · ${escapeHtml(f.ts||'')}${spec}${elapsed}</div></button>`;
  }).join('') || '<span class="hint">还没有成品</span>';
}
async function restoreChat(){
  const saved = await api('/api/chat/history');
  if (saved && saved.messages) {
    chat.splice(0, chat.length, ...saved.messages);
    renderChat();
  }
}
refreshModels();
restoreChat();
setInterval(tick, 1500);
tick();
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("[gui]", fmt % args)

    def _json(self, code: int, payload) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def _serve_media(self, path: Path) -> None:
        size = path.stat().st_size
        ctype = "video/mp4" if path.suffix == ".mp4" else "audio/wav"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng and rng.startswith("bytes="):
            spec = rng.split("=", 1)[1].split(",")[0].strip()
            left, _, right = spec.partition("-")
            try:
                if left:
                    start = max(0, int(left))
                if right:
                    end = min(size - 1, int(right))
                elif left:
                    end = size - 1
                code = 206
            except ValueError:
                start, end = 0, size - 1
                code = 200
        length = max(0, end - start + 1)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _proxy_chat_sse(self, body: dict) -> None:
        built = _chat_payload(body, stream=True)
        if isinstance(built, dict):
            self._json(409, built)
            return
        model, payload = built
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        answer = ""
        thinking = ""
        proc = subprocess.Popen(
            [
                "curl",
                "-sN",
                "--http1.1",
                "--max-time",
                "600",
                "http://127.0.0.1:8767/v1/chat/completions",
                "-H",
                "Content-Type: application/json",
                "-H",
                "Authorization: Bearer lm-studio",
                "-d",
                payload.decode("utf-8"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        try:
            assert proc.stdout is not None
            while True:
                raw = proc.stdout.readline()
                if not raw:
                    break
                self.wfile.write(raw)
                try:
                    self.wfile.flush()
                except BrokenPipeError:
                    proc.kill()
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = ((obj.get("choices") or [{}])[0].get("delta") or {})
                thinking += delta.get("reasoning_content") or delta.get("reasoning") or ""
                answer += delta.get("content") or ""
        except Exception as exc:
            err = json.dumps({"error": str(exc)})
            try:
                self.wfile.write(f"data: {err}\n\n".encode())
            except BrokenPipeError:
                return
        finally:
            if proc.poll() is None:
                proc.kill()
        final = (answer or thinking).strip()
        try:
            CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
            messages = list(body.get("messages") or [])
            messages.append({"role": "assistant", "content": final, "thinking": thinking})
            CHAT_FILE.write_text(
                json.dumps({"model": model, "messages": messages[-40:]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            data = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/status":
            with _lock:
                self._json(200, dict(_job))
            return
        if parsed.path == "/api/planner":
            self._json(200, _planner())
            return
        if parsed.path == "/api/llm/models":
            self._json(200, _disk_llms())
            return
        if parsed.path == "/api/outputs":
            self._json(200, _outputs())
            return
        if parsed.path == "/api/history":
            self._json(200, _read_history())
            return
        if parsed.path == "/api/chat/history":
            if CHAT_FILE.exists():
                try:
                    self._json(200, json.loads(CHAT_FILE.read_text(encoding="utf-8")))
                    return
                except json.JSONDecodeError:
                    pass
            self._json(200, {"messages": []})
            return
        if parsed.path.startswith("/file/"):
            name = urllib.parse.unquote(parsed.path[len("/file/") :])
            path = (OUT_DIR / Path(name).name).resolve()
            if not str(path).startswith(str(OUT_DIR.resolve())) or not path.is_file():
                self.send_error(404)
                return
            self._serve_media(path)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/api/chat/save":
            try:
                CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
                CHAT_FILE.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as exc:
                self._json(500, {"error": str(exc)})
                return
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/llm/unload":
            _unload_llms()
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/llm/load":
            key = body.get("key") or ""
            threading.Thread(target=_load_llm, args=(key,), daemon=True).start()
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/llm/chat":
            self._json(200, _chat(body))
            return
        if parsed.path == "/api/llm/chat/stream":
            self._proxy_chat_sse(body)
            return
        with _lock:
            if _job["status"] == "running":
                self._json(409, {"error": "already running"})
                return
            _job.update(status="running", log="", output=None, error=None, started=time.time())
        if parsed.path == "/api/h3":
            _job["kind"] = "h3"
            threading.Thread(
                target=_run_h3,
                args=(
                    body.get("prompt") or "cinematic rain",
                    int(body.get("width") or 512),
                    int(body.get("height") or 288),
                    int(body.get("frames") or 73),
                    int(body.get("steps") or 10),
                ),
                daemon=True,
            ).start()
            self._json(200, {"ok": True})
            return
        if parsed.path == "/api/music":
            _job["kind"] = "music"
            threading.Thread(
                target=_run_music,
                args=(
                    body.get("caption") or "warm acoustic folk",
                    body.get("lyrics") or "[verse]\nhello",
                    float(body.get("duration") or 30),
                ),
                daemon=True,
            ).start()
            self._json(200, {"ok": True})
            return
        with _lock:
            _job["status"] = "idle"
        self.send_error(404)


def main() -> None:
    if not MLX_H3.exists():
        raise SystemExit(f"mlx-h3 not found: {MLX_H3}")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"本地模型台  http://{HOST}:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
