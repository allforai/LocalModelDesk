# 看手气 / 优化提示词 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 视频与音乐面板各加两个按钮：「看手气」让已加载的聊天模型随机写一份生成提示词（会替换输入框，替换前提醒、替换后可恢复）；「优化提示词」把用户已经写在输入框里的内容交给模型改写得更适合生成。

**Architecture:** 服务端新增纯函数模块 `desk/llm/prompts.py`（校验请求 → 组装消息 → 解析回复），经 `LlmService.chat_completion` 调用驻留模型，路由 `POST /api/llm/prompt-assist` 挂在已有 `build_llm_routes` 上（生产 runtime 与测试 harness 自动一起装配）。前端新增一个与面板无关的小组件 `widgets/prompt_assist.js`，视频与音乐面板各实例化一次；可用性由 `main.js` 的 2 秒 tick 按"聊天模型已加载且无媒体作业"推送。

**Tech Stack:** Python 3.13 stdlib（`json`、`re`、`random`）· 零依赖 ES modules · pytest · node:test · Playwright

**Spec:** 用户需求原话（2026-09-13 盘问中途提出）：「还想增加一个功能，叫做看手气，就是随便调用llm生成生视频生音乐用的prompt，因为会清提示框，所以，需要提醒用户，还有增加一个生成prompt的功能，用户输入到textbox，直接拿这个提示词进行优化」。设计决定（本计划自拟，执行前可调整）：

- 两个动作都要求聊天模型已加载；没加载时按钮禁用并写明「先在「聊天」页加载一个模型」。媒体作业进行中同样禁用（模型会被驱逐）。
- 「看手气」仅在输入框非空时弹确认（「替换」/「取消」），空输入框直接写入。「优化提示词」要求输入框非空。
- 两个动作写入后都显示「恢复原文」，点一次恢复写入前的内容。
- 音乐：「看手气」同时写风格描述与歌词；「优化提示词」改写风格描述，用户已有歌词原样保留，歌词为空时顺带按风格写歌词。
- 视频提示词随「生成方式」（文生 / 图生 / 视频参考）调整写法。
- 输出语言：看手气用中文；优化与原文同语言。
- 模型调用 `max_tokens = 4096`（推理模型要留思考预算）；看手气 `temperature = 1.0` 并从题材表随机取一个题材，优化 `temperature = 0.5`。

**Depends on:** Plan B Task 1 已让 `chat_completion` 默认带 `max_tokens`；本计划显式传 4096，不依赖默认值。Plan B Task 6 给 `api.js` 的 `request()` 加了 `keepalive`；本计划 Task 3 加 `timeoutMs`——两者都保留。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）。
- 前端：零依赖 ES modules；`createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文；错误码不作唯一解释。
- 界面自适应：按钮行在 800px 宽时可换行，不产生横向溢出。
- 测试命令：`python3 -m pytest -q`、`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`。
- 验证门必须包含 e2e（`desk/static/` 改动）。
- 测试永不触碰 `~/LocalModelDesk` 或真实数据根；模型一律 fake backend。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 职责 |
|---|---|
| `desk/llm/prompts.py`（新） | `parse_request`、`build_messages`、`parse_reply`、`assist`、`PromptAssistError` |
| `desk/llm/routes.py` | `POST /api/llm/prompt-assist` |
| `desk/static/js/api.js` | `request({timeoutMs})`、`promptAssist(body)` |
| `desk/static/js/widgets/prompt_assist.js`（新） | 按钮、确认、恢复原文、可用性与错误文案 |
| `desk/static/js/panes/video.js`、`music.js` | 实例化组件，暴露 `setAssistAvailable` |
| `desk/static/js/main.js` | tick 推送可用性 |
| `desk/static/index.html`、`app.css` | 按钮行容器与布局 |

---

### Task 1: 提示词请求的校验、组装与解析（纯函数）

**Files:**
- Create: `desk/llm/prompts.py`
- Test: `tests/llm/test_llm_prompts.py`（新）

**Interfaces:**
- Produces: `class PromptAssistError(Exception)`，属性 `code: str`、`message: str`、`http_status: int`
- Produces: `@dataclass(frozen=True) class AssistRequest: task: str; action: str; mode: str; text: str; lyrics: str`
- Produces: `parse_request(body: dict) -> AssistRequest`
  - `task ∈ {"video","music"}`，否则 `invalid_task`；`action ∈ {"lucky","refine"}`，否则 `invalid_action`
  - `mode` 缺省 `"text"`；视频时须 ∈ `{"text","image","reference"}`，否则 `invalid_mode`
  - `text`、`lyrics` 缺省空串，非字符串 → `invalid_text`；任一超过 4000 字 → `text_too_long`
  - `refine` 且 `text` 去空白后为空 → `text_required`「先在输入框里写点东西，再点「优化提示词」」
- Produces: `build_messages(req: AssistRequest, *, rng=random) -> list[dict]`（`[{"role":"system",...},{"role":"user",...}]`；看手气题材用 `rng.choice(...)`）
- Produces: `parse_reply(req: AssistRequest, content: str) -> dict` → 视频 `{"text": str}`；音乐 `{"text": caption, "lyrics": str}`；去掉 `<think>…</think>` 与代码块围栏；空 → `PromptAssistError("empty_reply", ..., 502)`
- Produces: `assist(service, body: dict, *, rng=random) -> dict` → `{"task", "action", "text", ["lyrics"]}`；调用 `service.chat_completion({"messages", "max_tokens": 4096, "temperature"})`
- Produces: 常量 `ASSIST_MAX_TOKENS = 4096`

- [ ] **Step 1: Write the failing tests**

新建 `tests/llm/test_llm_prompts.py`：

```python
"""看手气 / 优化提示词：请求校验、消息组装与回复解析。"""
import pytest

from desk.llm.prompts import (
    ASSIST_MAX_TOKENS, AssistRequest, PromptAssistError, assist, build_messages, parse_reply, parse_request,
)


class FirstChoice:
    def choice(self, seq):
        return seq[0]


def _req(**kw):
    base = {"task": "video", "action": "lucky", "mode": "text", "text": "", "lyrics": ""}
    base.update(kw)
    return AssistRequest(**base)


@pytest.mark.parametrize("body,code", [
    ({"task": "image", "action": "lucky"}, "invalid_task"),
    ({"task": "video", "action": "rewrite"}, "invalid_action"),
    ({"task": "video", "action": "lucky", "mode": "sketch"}, "invalid_mode"),
    ({"task": "video", "action": "refine", "text": 42}, "invalid_text"),
    ({"task": "video", "action": "refine", "text": "字" * 4001}, "text_too_long"),
    ({"task": "music", "action": "refine", "text": "   "}, "text_required"),
])
def test_parse_request_rejects_with_a_code(body, code):
    with pytest.raises(PromptAssistError) as err:
        parse_request(body)
    assert err.value.code == code
    assert err.value.http_status == 400


def test_parse_request_defaults_and_trims():
    req = parse_request({"task": "music", "action": "refine", "text": "  民谣 ", "lyrics": " 啦啦 "})
    assert req == AssistRequest("music", "refine", "text", "民谣", "啦啦")


def test_video_lucky_messages_carry_a_theme_and_mode_note():
    messages = build_messages(_req(mode="image"), rng=FirstChoice())
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "图生视频" in messages[0]["content"]
    assert "雨夜城市街角" in messages[1]["content"]


def test_video_refine_quotes_the_user_text():
    messages = build_messages(_req(action="refine", text="一只猫在屋顶"))
    assert "一只猫在屋顶" in messages[1]["content"]
    assert "相同的语言" in messages[1]["content"]


def test_music_refine_keeps_user_lyrics_out_of_the_rewrite():
    with_lyrics = build_messages(_req(task="music", action="refine", text="民谣", lyrics="第一行"))
    assert "lyrics 字段留空" in with_lyrics[1]["content"]
    without = build_messages(_req(task="music", action="refine", text="民谣"))
    assert "写 8 到 16 行歌词" in without[1]["content"]


def test_parse_reply_video_strips_thinking_fences_and_quotes():
    content = "<think>想想</think>\n```\n“夜晚的海边，浪花拍岸，远处灯塔闪烁。”\n```"
    assert parse_reply(_req(), content) == {"text": "夜晚的海边，浪花拍岸，远处灯塔闪烁。"}


def test_parse_reply_music_json_and_fallback():
    req = _req(task="music")
    assert parse_reply(req, '好的：{"caption": "温柔民谣", "lyrics": "第一行\\n第二行"}') == {
        "text": "温柔民谣", "lyrics": "第一行\n第二行"}
    assert parse_reply(req, "温柔民谣\n第一行\n第二行") == {"text": "温柔民谣", "lyrics": "第一行\n第二行"}


def test_parse_reply_music_refine_returns_the_users_own_lyrics():
    req = _req(task="music", action="refine", text="民谣", lyrics="我写的歌词")
    assert parse_reply(req, '{"caption": "木吉他民谣", "lyrics": "模型改的"}') == {
        "text": "木吉他民谣", "lyrics": "我写的歌词"}


def test_parse_reply_empty_is_a_502():
    with pytest.raises(PromptAssistError) as err:
        parse_reply(_req(), "<think>只想不写")
    assert err.value.code == "empty_reply"
    assert err.value.http_status == 502


def test_assist_calls_the_resident_model_with_budget_and_temperature():
    calls = []

    class Service:
        def chat_completion(self, request):
            calls.append(request)
            return {"content": "雨夜街角，霓虹反光。", "reasoning": None, "usage": {}, "finish_reason": "stop", "model": "glm"}

    result = assist(Service(), {"task": "video", "action": "lucky"}, rng=FirstChoice())

    assert result == {"task": "video", "action": "lucky", "text": "雨夜街角，霓虹反光。"}
    assert calls[0]["max_tokens"] == ASSIST_MAX_TOKENS == 4096
    assert calls[0]["temperature"] == 1.0
    assert assist(Service(), {"task": "video", "action": "refine", "text": "猫"})["action"] == "refine"
    assert calls[1]["temperature"] == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/llm/test_llm_prompts.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'desk.llm.prompts'`

- [ ] **Step 3: Write the implementation**

新建 `desk/llm/prompts.py`：

```python
"""看手气 / 优化提示词: turn the resident chat model into a writer of media generation prompts."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

TASKS = ("video", "music")
ACTIONS = ("lucky", "refine")
VIDEO_MODES = ("text", "image", "reference")
MAX_INPUT_CHARS = 4000
ASSIST_MAX_TOKENS = 4096

VIDEO_THEMES = (
    "雨夜城市街角", "清晨雾中的山谷", "深海里发光的生物", "沙漠公路上的旅行", "老式厨房里做饭",
    "冬天的火车站台", "赛博朋克夜市", "森林里的小动物", "暴风雨中的海边灯塔", "工作室里做陶艺",
    "太空站舷窗外的地球", "古镇石板路上的早市",
)
MUSIC_THEMES = (
    "夏夜乡村民谣", "都市夜晚的爵士", "电子舞曲", "温柔的钢琴抒情", "公路摇滚", "国风古筝",
    "Lo-fi 学习背景", "海滩雷鬼", "史诗管弦", "复古合成器流行", "蓝调小酒馆", "童谣",
)

VIDEO_SYSTEM = (
    "你为本地视频生成模型写提示词。好的提示词写清：主体与动作、镜头（景别与运动）、光线与色调、环境声音。"
    "只输出提示词正文，不要标题、编号、引号或任何解释。"
)
VIDEO_MODE_NOTES = {
    "text": "",
    "image": "这是图生视频：画面外观来自用户上传的图片，提示词重点写图片如何动起来（动作、镜头变化）和声音，不要重新描述静态外观。",
    "reference": "这是视频参考生成：提示词写要保留参考视频的哪些内容，以及想得到的新画面与声音。",
}
MUSIC_SYSTEM = (
    "你为本地歌曲生成模型写输入。caption 是风格描述：曲风、配器、人声、速度与情绪，30 到 60 字；"
    "lyrics 是歌词，段落之间空一行。只输出一个 JSON 对象：{\"caption\": \"…\", \"lyrics\": \"…\"}，不要代码块或解释。"
)

_THINK = re.compile(r"<think>.*?(</think>|$)", re.S)
_FENCE = re.compile(r"^```[\w-]*\s*|\s*```$")
_QUOTES = "\"'“”「」"


class PromptAssistError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.http_status = code, message, http_status


@dataclass(frozen=True)
class AssistRequest:
    task: str
    action: str
    mode: str
    text: str
    lyrics: str


def parse_request(body: dict[str, Any]) -> AssistRequest:
    task, action = body.get("task"), body.get("action")
    if task not in TASKS:
        raise PromptAssistError("invalid_task", "task 只能是 video 或 music")
    if action not in ACTIONS:
        raise PromptAssistError("invalid_action", "action 只能是 lucky 或 refine")
    mode = body.get("mode") or "text"
    if task == "video" and mode not in VIDEO_MODES:
        raise PromptAssistError("invalid_mode", "生成方式无效")
    text, lyrics = body.get("text", ""), body.get("lyrics", "")
    text = "" if text is None else text
    lyrics = "" if lyrics is None else lyrics
    if not isinstance(text, str) or not isinstance(lyrics, str):
        raise PromptAssistError("invalid_text", "text 与 lyrics 必须是字符串")
    if len(text) > MAX_INPUT_CHARS or len(lyrics) > MAX_INPUT_CHARS:
        raise PromptAssistError("text_too_long", f"输入超过 {MAX_INPUT_CHARS} 字，先删减一些再试")
    if action == "refine" and not text.strip():
        raise PromptAssistError("text_required", "先在输入框里写点东西，再点「优化提示词」")
    return AssistRequest(task, action, mode, text.strip(), lyrics.strip())


def build_messages(req: AssistRequest, *, rng=random) -> list[dict[str, str]]:
    if req.task == "video":
        system = " ".join(filter(None, (VIDEO_SYSTEM, VIDEO_MODE_NOTES[req.mode])))
        if req.action == "lucky":
            user = f"随便写一个视频提示词，题材：{rng.choice(VIDEO_THEMES)}。80 到 150 字，中文。"
        else:
            user = ("优化下面这段视频提示词：保留原意和主体，补全缺少的动作、镜头、光线和声音细节，"
                    f"不超过 200 字，使用与原文相同的语言。\n\n原文：\n{req.text}")
    else:
        system = MUSIC_SYSTEM
        if req.action == "lucky":
            user = f"随便写一首歌，题材：{rng.choice(MUSIC_THEMES)}。歌词 8 到 16 行，中文。"
        elif req.lyrics:
            user = ("优化下面的风格描述：保留原意，补全曲风、配器、人声、速度与情绪，使用与原文相同的语言。"
                    f"用户已有歌词，lyrics 字段留空字符串。\n\n风格描述：\n{req.text}")
        else:
            user = ("优化下面的风格描述：保留原意，补全曲风、配器、人声、速度与情绪，使用与原文相同的语言；"
                    f"并按这个风格写 8 到 16 行歌词。\n\n风格描述：\n{req.text}")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _clean(content: str | None) -> str:
    text = _THINK.sub("", content or "").strip()
    return _FENCE.sub("", text).strip()


def _music_fields(text: str) -> tuple[str, str]:
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return str(data.get("caption") or "").strip(), str(data.get("lyrics") or "").strip()
    first, _, rest = text.partition("\n")
    return first.strip(), rest.strip()


def parse_reply(req: AssistRequest, content: str | None) -> dict[str, str]:
    text = _clean(content)
    if req.task == "video":
        prompt = text.strip(_QUOTES).strip()
        if not prompt:
            raise PromptAssistError("empty_reply", "模型没有写出提示词，再试一次", 502)
        return {"text": prompt}
    caption, lyrics = _music_fields(text)
    caption = caption.strip(_QUOTES).strip()
    if not caption:
        raise PromptAssistError("empty_reply", "模型没有写出风格描述，再试一次", 502)
    if req.action == "refine" and req.lyrics:
        lyrics = req.lyrics
    return {"text": caption, "lyrics": lyrics}


def assist(service, body: dict[str, Any], *, rng=random) -> dict[str, str]:
    req = parse_request(body)
    result = service.chat_completion({
        "messages": build_messages(req, rng=rng),
        "max_tokens": ASSIST_MAX_TOKENS,
        "temperature": 1.0 if req.action == "lucky" else 0.5,
    })
    return {"task": req.task, "action": req.action, **parse_reply(req, result.get("content"))}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/llm/test_llm_prompts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/llm/prompts.py tests/llm/test_llm_prompts.py
git commit -m "feat(llm): prompt-assist request parsing, messages and reply parsing"
```

---

### Task 2: `POST /api/llm/prompt-assist` 路由

**Files:**
- Modify: `desk/llm/routes.py`
- Test: `tests/llm/test_llm_routes.py`、`tests/test_production_runtime.py`

**Interfaces:**
- Consumes: `assist`、`PromptAssistError`（Task 1）
- Produces: 200 `{"task","action","text",["lyrics"]}`；`PromptAssistError` → 其 `http_status` + `{"error":{"code","message"}}`；`LlmRejected`（`no_model_loaded` 503、`media_busy` 409）照 `_rejected`；`UpstreamError` → 502 `upstream_error`。

- [ ] **Step 1: Write the failing tests**

`tests/llm/test_llm_routes.py` 末尾追加：

```python
def _route(service, path):
    return next(route for route in build_routes(service) if route.path == path)


def test_prompt_assist_route_returns_fields(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": {
        "choices": [{"message": {"content": '{"caption": "温柔民谣", "lyrics": "第一行"}'}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 9},
    }})
    result = _route(testbed.service, "/api/llm/prompt-assist").handler({"task": "music", "action": "lucky"})
    assert result.status == 200
    assert result.body == {"task": "music", "action": "lucky", "text": "温柔民谣", "lyrics": "第一行"}


def test_prompt_assist_route_maps_errors(tmp_path):
    idle = make_service(tmp_path)
    handler = _route(idle.service, "/api/llm/prompt-assist").handler
    no_model = handler({"task": "video", "action": "lucky"})
    assert no_model.status == 503
    assert no_model.body["error"]["code"] == "no_model_loaded"
    bad = handler({"task": "video", "action": "refine", "text": ""})
    assert bad.status == 400
    assert bad.body["error"] == {"code": "text_required", "message": "先在输入框里写点东西，再点「优化提示词」"}
```

`tests/test_production_runtime.py` 末尾追加：

```python
def test_prompt_assist_is_mounted_in_production(tmp_path, monkeypatch):
    _configured_data_root(tmp_path, monkeypatch)
    runtime = build_runtime(port=0)
    runtime.start_background()
    try:
        status, payload = http_call(runtime, "POST", "/api/llm/prompt-assist", {"task": "video", "action": "lucky"})
        assert status == 503
        assert payload["error"]["code"] == "no_model_loaded"
    finally:
        runtime.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/llm/test_llm_routes.py -k prompt_assist tests/test_production_runtime.py -k prompt_assist -q`
Expected: FAIL（`StopIteration`：没有该路由；生产 404）

- [ ] **Step 3: Write the implementation**

`desk/llm/routes.py`：import 区加 `from .prompts import PromptAssistError, assist`；`build_routes` 列表末尾加：

```python
        Route("POST", "/api/llm/prompt-assist", lambda body: _prompt_assist(service, body)),
```

文件末尾加：

```python
def _prompt_assist(service, body: dict) -> RouteResult:
    try:
        return RouteResult(200, assist(service, body or {}))
    except PromptAssistError as exc:
        return RouteResult(exc.http_status, {"error": {"code": exc.code, "message": exc.message}})
    except LlmRejected as exc:
        return _rejected(exc)
    except UpstreamError as exc:
        return RouteResult(502, {"error": {"code": ERR_UPSTREAM_ERROR, "message": exc.message}})
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/llm tests/test_production_runtime.py tests/test_e2e_harness_assembly.py -q`
Expected: PASS（harness 与生产用同一 `build_llm_routes`，路由集合对比测试若逐条列举路径，把新路径加入期望列表）

- [ ] **Step 5: Commit**

```bash
git add desk/llm/routes.py tests/llm/test_llm_routes.py tests/test_production_runtime.py tests/test_e2e_harness_assembly.py
git commit -m "feat(llm): POST /api/llm/prompt-assist"
```

---

### Task 3: 前端组件（看手气、优化、恢复原文、提醒与禁用原因）

**Files:**
- Modify: `desk/static/js/api.js`（`request` 的 `timeoutMs`；`promptAssist`）
- Create: `desk/static/js/widgets/prompt_assist.js`
- Test: `tests/js/prompt_assist.test.js`（新）、`tests/js/api.test.js`

**Interfaces:**
- Produces: `request(path, { method, body, stream, keepalive, timeoutMs = REQUEST_TIMEOUT_MS })`；超时文案 `请求超时（${timeoutMs / 1000} 秒无响应）`
- Produces: `api.promptAssist(body) -> Promise<{task, action, text, lyrics?}>`，超时 180 秒
- Produces: `createPromptAssist(doc, container, { task, read, write, mode = () => "text", confirm })`
  - `read() -> {text: string, lyrics?: string}`；`write({text, lyrics?})`
  - 返回 `{ setAvailable(allowed: boolean, reason: string) }`
  - 在 `container` 内依次创建 `button[data-assist-lucky]`「看手气」、`button[data-assist-refine]`「优化提示词」、`button[data-assist-undo]`「恢复原文」（初始隐藏）、`span.hint[data-assist-hint]`
  - 初始不可用，提示「先在「聊天」页加载一个模型」

- [ ] **Step 1: Write the failing tests**

新建 `tests/js/prompt_assist.test.js`：

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { createPromptAssist } from "../../desk/static/js/widgets/prompt_assist.js";

class El {
  constructor(tag = "div") { this.tagName = tag; this.children = []; this.listeners = {}; this.hidden = false; this.disabled = false; this.textContent = ""; this.className = ""; this.dataset = {}; }
  append(...nodes) { this.children.push(...nodes); }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  click() { return this.listeners.click?.(); }
}
const doc = { createElement: (tag) => new El(tag) };
const byData = (container, key) => container.children.find((node) => node.dataset[key]);

function setup({ fields = { text: "" }, confirmAnswer = true, task = "video" } = {}) {
  const container = new El();
  const state = { ...fields };
  const asked = [];
  const assist = createPromptAssist(doc, container, {
    task,
    read: () => ({ ...state }),
    write: (next) => Object.assign(state, next),
    mode: () => "image",
    confirm: async (options) => { asked.push(options); return confirmAnswer; },
  });
  return { container, state, asked, assist };
}

async function withFetch(reply, run) {
  const previous = globalThis.fetch; const bodies = [];
  globalThis.fetch = async (_url, options) => { bodies.push(JSON.parse(options.body)); return reply(); };
  try { await run(bodies); } finally { globalThis.fetch = previous; }
}
const ok = (payload) => new Response(JSON.stringify(payload), { status: 200 });

test("初始禁用并说明原因；可用后启用", () => {
  const { container, assist } = setup();
  assert.equal(byData(container, "assistLucky").disabled, true);
  assert.equal(byData(container, "assistHint").textContent, "先在「聊天」页加载一个模型");
  assert.equal(byData(container, "assistUndo").hidden, true);
  assist.setAvailable(true, "");
  assert.equal(byData(container, "assistLucky").disabled, false);
  assert.equal(byData(container, "assistHint").textContent, "");
});

test("看手气：空输入框直接写入，不打扰；带着生成方式请求", async () => {
  const { container, state, asked, assist } = setup();
  assist.setAvailable(true, "");
  await withFetch(() => ok({ task: "video", action: "lucky", text: "雨夜街角" }), async (bodies) => {
    await byData(container, "assistLucky").click();
    assert.deepEqual(bodies[0], { task: "video", action: "lucky", mode: "image", text: "" });
  });
  assert.equal(asked.length, 0);
  assert.equal(state.text, "雨夜街角");
  assert.equal(byData(container, "assistUndo").hidden, false);
});

test("看手气：输入框有内容时先提醒会被替换；取消则不请求", async () => {
  const { container, state, asked, assist } = setup({ fields: { text: "我写的" }, confirmAnswer: false });
  assist.setAvailable(true, "");
  await withFetch(() => { throw new Error("不应请求"); }, async () => {
    await byData(container, "assistLucky").click();
  });
  assert.equal(asked.length, 1);
  assert.equal(asked[0].confirmLabel, "替换");
  assert.match(asked[0].message, /替换输入框里现有的内容/);
  assert.equal(state.text, "我写的");
});

test("优化提示词：空输入框只提示不请求；有内容则替换并可恢复原文", async () => {
  const empty = setup();
  empty.assist.setAvailable(true, "");
  await withFetch(() => { throw new Error("不应请求"); }, async () => { await byData(empty.container, "assistRefine").click(); });
  assert.equal(byData(empty.container, "assistHint").textContent, "先在输入框里写点东西，再点「优化提示词」");

  const { container, state, assist } = setup({ fields: { text: "猫", lyrics: "啦" }, task: "music" });
  assist.setAvailable(true, "");
  await withFetch(() => ok({ task: "music", action: "refine", text: "木吉他民谣", lyrics: "啦" }), async (bodies) => {
    await byData(container, "assistRefine").click();
    assert.deepEqual(bodies[0], { task: "music", action: "refine", mode: "image", text: "猫", lyrics: "啦" });
  });
  assert.equal(state.text, "木吉他民谣");
  await byData(container, "assistUndo").click();
  assert.equal(state.text, "猫");
  assert.equal(byData(container, "assistUndo").hidden, true);
});

test("失败时写明原因、按钮恢复可用、输入框不变", async () => {
  const { container, state, assist } = setup({ fields: { text: "猫" } });
  assist.setAvailable(true, "");
  await withFetch(() => new Response(JSON.stringify({ error: { code: "no_model_loaded", message: "当前没有加载模型" } }), { status: 503 }), async () => {
    await byData(container, "assistRefine").click();
  });
  assert.equal(byData(container, "assistHint").textContent, "先在「聊天」页加载一个模型");
  assert.equal(byData(container, "assistRefine").disabled, false);
  assert.equal(state.text, "猫");
});
```

`tests/js/api.test.js` 末尾追加：

```javascript
test("promptAssist 以 POST 发往 prompt-assist，且不受 8 秒默认超时限制", async () => {
  const oldFetch = globalThis.fetch;
  const oldSetTimeout = globalThis.setTimeout;
  const delays = [];
  globalThis.setTimeout = (fn, ms) => { delays.push(ms); return oldSetTimeout(() => {}, 0); };
  globalThis.fetch = async (path, options) => new Response(JSON.stringify({ path, method: options.method }), { status: 200 });
  try {
    const api = await import("../../desk/static/js/api.js");
    const result = await api.promptAssist({ task: "video", action: "lucky" });
    assert.deepEqual(result, { path: "/api/llm/prompt-assist", method: "POST" });
    assert.deepEqual(delays, [180000]);
  } finally { globalThis.fetch = oldFetch; globalThis.setTimeout = oldSetTimeout; }
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/prompt_assist.test.js tests/js/api.test.js`
Expected: FAIL（模块与导出不存在）

- [ ] **Step 3: api.js**

`ROUTES` 里 `chatStream: ...` 之后加 `promptAssist: "/api/llm/prompt-assist",`。`request` 改为（保留 Plan B 的 `keepalive`）：

```javascript
async function request(path, { method = "GET", body, stream = false, keepalive = false, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const options = { method };
  if (keepalive) options.keepalive = true;
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  let timer = null;
  if (!stream && typeof AbortController === "function") {
    const controller = new AbortController();
    options.signal = controller.signal;
    timer = setTimeout(() => controller.abort(), timeoutMs);
  }
  let response;
  try {
    response = await globalThis.fetch(path, options);
  } catch (error) {
    if (error?.name === "AbortError") throw new DeskApiError(0, "timeout", `请求超时（${timeoutMs / 1000} 秒无响应）`);
    throw error;
  } finally { if (timer) clearTimeout(timer); }
  if (!response.ok) throw await toError(response);
  return stream ? response.body : response.json();
}
```

导出区 `chatStream` 之后加：

```javascript
// A reasoning model may think for a while before it writes the prompt.
export const promptAssist = (body) => request(ROUTES.promptAssist, { method: "POST", body, timeoutMs: 180_000 });
```

- [ ] **Step 4: The widget**

新建 `desk/static/js/widgets/prompt_assist.js`：

```javascript
// ui:promptAssist —— 看手气 / 优化提示词：让已加载的聊天模型写或改媒体生成提示词。
import * as api from "../api.js";
import { confirmDialog } from "./confirm.js";

const NEED_MODEL = "先在「聊天」页加载一个模型";
const REASON_BY_CODE = { no_model_loaded: NEED_MODEL, media_busy: "媒体作业进行中，暂时不能调用模型" };
const isBlank = (fields) => Object.values(fields).every((value) => !String(value ?? "").trim());

export function createPromptAssist(doc, container, { task, read, write, mode = () => "text", confirm }) {
  const button = (label, key) => {
    const node = doc.createElement("button");
    node.type = "button";
    node.textContent = label;
    (node.dataset ??= {})[key] = "1";
    return node;
  };
  const lucky = button("看手气", "assistLucky");
  const refine = button("优化提示词", "assistRefine");
  const undo = button("恢复原文", "assistUndo");
  const hint = doc.createElement("span");
  hint.className = "hint";
  (hint.dataset ??= {}).assistHint = "1";
  undo.hidden = true;
  container.append(lucky, refine, undo, hint);

  let available = false;
  let reason = NEED_MODEL;
  let busy = false;
  let original = null;
  let lastMessage = "";
  const ask = confirm ?? ((options) => confirmDialog(doc, options));

  // The 2 s tick calls setAvailable() constantly; keep the last action message
  // ("已优化") on screen instead of wiping it on every tick.
  function render(message = lastMessage) {
    lastMessage = message;
    lucky.disabled = refine.disabled = !available || busy;
    hint.textContent = busy ? "模型正在写提示词…" : !available ? reason : message;
  }

  async function run(action) {
    if (!available || busy) return;
    const before = read();
    if (action === "refine" && !String(before.text ?? "").trim()) { render("先在输入框里写点东西，再点「优化提示词」"); return; }
    if (action === "lucky" && !isBlank(before)) {
      const go = await ask({
        title: "看手气",
        message: "看手气会让模型随机写一份新的提示词，替换输入框里现有的内容。替换后可以点「恢复原文」找回。",
        confirmLabel: "替换",
        danger: false,
      });
      if (!go) return;
    }
    busy = true;
    render();
    let message = "";
    try {
      const result = await api.promptAssist({ task, action, mode: mode(), ...before });
      original = before;
      const next = { text: result.text };
      if (result.lyrics !== undefined) next.lyrics = result.lyrics;
      write(next);
      undo.hidden = false;
      message = action === "lucky" ? "已换上新的提示词" : "已优化";
    } catch (error) {
      message = REASON_BY_CODE[error.code] ?? error.message;
    } finally {
      busy = false;
      render(message);
    }
  }

  lucky.addEventListener("click", () => run("lucky"));
  refine.addEventListener("click", () => run("refine"));
  undo.addEventListener("click", () => {
    if (!original) return;
    write(original);
    original = null;
    undo.hidden = true;
    render("已恢复原文");
  });
  render();

  return {
    setAvailable(allowed, why = "") {
      available = allowed;
      reason = why || NEED_MODEL;
      if (!busy) render();
    },
  };
}
```

- [ ] **Step 5: Run tests**

Run: `node --test tests/js/*.test.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/api.js desk/static/js/widgets/prompt_assist.js tests/js/prompt_assist.test.js tests/js/api.test.js
git commit -m "feat(ui): prompt-assist widget with replace warning and restore"
```

---

### Task 4: 接进视频与音乐面板，tick 推送可用性

**Files:**
- Modify: `desk/static/index.html`（视频提示词下、音乐歌词下各一个容器）
- Modify: `desk/static/app.css`
- Modify: `desk/static/js/panes/video.js`、`desk/static/js/panes/music.js`
- Modify: `desk/static/js/main.js`（`tick`）
- Test: `tests/js/media_panes.test.js`、`tests/e2e/test_prompt_assist.py`（新）

**Interfaces:**
- Consumes: `createPromptAssist`（Task 3）
- Produces: `videoPane.setAssistAvailable(allowed, reason)`、`musicPane.setAssistAvailable(allowed, reason)`
- Produces: 可用条件 `llm.state.status === "loaded" && !deskState.media_busy`；不可用原因：未加载 →「先在「聊天」页加载一个模型」，媒体忙 →「媒体作业进行中，暂时不能调用模型」

- [ ] **Step 1: Write the failing unit test**

`tests/js/media_panes.test.js` 末尾追加（复用文件内 `pane`、`Element`）：

```javascript
test("视频/音乐面板各有看手气与优化提示词，写回各自的输入框", async () => {
  const video = pane({ "video-prompt": "", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "", "video-assist": "" });
  const music = pane({ "music-caption": "民谣", "music-lyrics": "", "music-duration": "60", "music-start": "", "music-assist": "" });
  const videoPane = createVideoPane(video);
  const musicPane = createMusicPane(music);
  const videoButtons = video.parts["video-assist"].children;
  const musicButtons = music.parts["music-assist"].children;
  assert.deepEqual(videoButtons.slice(0, 3).map((b) => b.textContent), ["看手气", "优化提示词", "恢复原文"]);
  assert.deepEqual(musicButtons.slice(0, 2).map((b) => b.textContent), ["看手气", "优化提示词"]);

  videoPane.setAssistAvailable(true, "");
  musicPane.setAssistAvailable(true, "");
  const previous = globalThis.fetch;
  const replies = [{ task: "video", action: "lucky", text: "雨夜街角" }, { task: "music", action: "refine", text: "木吉他民谣", lyrics: "第一行" }];
  globalThis.fetch = async () => new Response(JSON.stringify(replies.shift()), { status: 200 });
  try {
    await videoButtons[0].click();
    await musicButtons[1].click();
  } finally { globalThis.fetch = previous; }
  assert.equal(video.parts["video-prompt"].value, "雨夜街角");
  assert.equal(music.parts["music-caption"].value, "木吉他民谣");
  assert.equal(music.parts["music-lyrics"].value, "第一行");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/media_panes.test.js`
Expected: FAIL

- [ ] **Step 3: Markup and CSS**

`desk/static/index.html:29` 在 `<textarea data-video-prompt ...></textarea>` 之后紧接插入：

```html
<div class="assist-row" data-video-assist></div>
```

`desk/static/index.html:30` 在歌词 `<label>歌词（必填） <textarea data-music-lyrics ...></textarea></label>` 之后紧接插入：

```html
<div class="assist-row" data-music-assist></div>
```

`desk/static/app.css` 末尾追加：

```css
.assist-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.assist-row .hint{flex:1 1 12em;min-width:0}
```

- [ ] **Step 4: Pane wiring**

`desk/static/js/panes/video.js`：import 区加 `import { createPromptAssist } from "../widgets/prompt_assist.js";`；在 `mode?.addEventListener("change", updateMode);` 之后加：

```javascript
  const assistRoot = root.querySelector("[data-video-assist]");
  const assist = assistRoot ? createPromptAssist(root.ownerDocument, assistRoot, {
    task: "video",
    read: () => ({ text: els.prompt.value }),
    write: ({ text }) => { els.prompt.value = text; },
    mode: () => mode?.value || "text",
    confirm: ctx.confirm ? (options) => ctx.confirm(root.ownerDocument, options) : undefined,
  }) : null;
```

返回值改为：

```javascript
  return { fill, jobView, setHeavyAllowed, setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason) };
```

`desk/static/js/panes/music.js`：同样 import；在 `const jobView = ...` 之后加：

```javascript
  const assistRoot = root.querySelector("[data-music-assist]");
  const assist = assistRoot ? createPromptAssist(root.ownerDocument, assistRoot, {
    task: "music",
    read: () => ({ text: els.caption.value, lyrics: els.lyrics.value }),
    write: ({ text, lyrics }) => { els.caption.value = text; if (lyrics !== undefined) els.lyrics.value = lyrics; },
    confirm: ctx.confirm ? (options) => ctx.confirm(root.ownerDocument, options) : undefined,
  }) : null;
```

返回值改为 `return { fill, jobView, setHeavyAllowed, setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason) };`。

（面板里 `ctx.confirm` 的约定是 `(doc, options)`，组件的 `confirm` 是 `(options)`，上面做了一层适配。）

`desk/static/js/main.js` 的 `tick()` 中 `panes.chat.applyLlmStatus(...)` 之后加：

```javascript
    const assistReason = llm.state?.status !== "loaded" ? "先在「聊天」页加载一个模型"
      : deskState.media_busy ? "媒体作业进行中，暂时不能调用模型" : "";
    panes.video.setAssistAvailable(!assistReason, assistReason);
    panes.music.setAssistAvailable(!assistReason, assistReason);
```

- [ ] **Step 5: Run unit tests**

Run: `node --test tests/js/*.test.js`
Expected: PASS

- [ ] **Step 6: Write the e2e test**

新建 `tests/e2e/test_prompt_assist.py`：

```python
"""看手气 warns before replacing text, writes the model's prompt, and can restore the original."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done

USAGE = {"prompt_tokens": 5, "completion_tokens": 9, "total_tokens": 14}


def _load_chat_model(page, harness):
    page.goto(harness.base_url)
    pane = page.locator("#pane-chat")
    pane.locator("[data-model-select]").select_option("glm")
    pane.get_by_role("button", name="加载").click()
    expect(pane.locator("[data-model-state]")).to_contain_text("已加载")


def test_video_lucky_warns_replaces_and_restores(page, tmp_path, audit_violations):
    script = ChatScript([Delta(reasoning="想一个场景"), Delta(content="雨夜的城市街角，霓虹在积水里反光，镜头缓慢推近，远处传来雷声。"), Done(usage=USAGE)])
    with launch_test_harness(tmp_path, chat_script=script) as harness:
        _load_chat_model(page, harness)
        page.locator("#tabs [data-tab=video]").click()
        video = page.locator("#pane-video")
        prompt = video.locator("[data-video-prompt]")
        prompt.fill("我自己写的")
        lucky = video.get_by_role("button", name="看手气")
        expect(lucky).to_be_enabled(timeout=5000)

        lucky.click()
        dialog = page.get_by_role("dialog", name="看手气")
        expect(dialog).to_contain_text("替换输入框里现有的内容")
        dialog.get_by_role("button", name="替换").click()

        expect(prompt).to_have_value("雨夜的城市街角，霓虹在积水里反光，镜头缓慢推近，远处传来雷声。")
        video.get_by_role("button", name="恢复原文").click()
        expect(prompt).to_have_value("我自己写的")
        assert harness.chat_script.requests[0]["max_tokens"] == 4096
    assert audit_violations == []


def test_music_refine_keeps_user_lyrics(page, tmp_path, audit_violations):
    script = ChatScript([Delta(content='{"caption": "木吉他民谣，温柔女声，慢速", "lyrics": ""}'), Done(usage=USAGE)])
    with launch_test_harness(tmp_path, chat_script=script) as harness:
        _load_chat_model(page, harness)
        page.locator("#tabs [data-tab=music]").click()
        music = page.locator("#pane-music")
        music.locator("[data-music-caption]").fill("民谣")
        music.locator("[data-music-lyrics]").fill("我写的第一行")
        refine = music.get_by_role("button", name="优化提示词")
        expect(refine).to_be_enabled(timeout=5000)

        refine.click()

        expect(music.locator("[data-music-caption]")).to_have_value("木吉他民谣，温柔女声，慢速")
        expect(music.locator("[data-music-lyrics]")).to_have_value("我写的第一行")
    assert audit_violations == []


def test_buttons_explain_why_they_are_disabled_without_a_model(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        video = page.locator("#pane-video")
        expect(video.get_by_role("button", name="看手气")).to_be_disabled()
        expect(video.locator("[data-video-assist] .hint")).to_have_text("先在「聊天」页加载一个模型")
    assert audit_violations == []
```

- [ ] **Step 7: Run e2e and a responsive check**

Run: `python3 -m pytest tests/e2e/test_prompt_assist.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

然后在 800×832 视口下打开 `#tab=video` 与 `#tab=music`，确认 `document.documentElement.scrollWidth <= innerWidth`（可临时在 `tests/e2e/test_prompt_assist.py` 里加一条 `page.set_viewport_size({"width": 800, "height": 832})` 的断言用例，保留提交）。

- [ ] **Step 8: Commit**

```bash
git add desk/static/index.html desk/static/app.css desk/static/js/panes/video.js desk/static/js/panes/music.js desk/static/js/main.js tests/js/media_panes.test.js tests/e2e/test_prompt_assist.py
git commit -m "feat(ui): 看手气 and 优化提示词 in the video and music panes"
```

---

### Task 5: 真机试用（真实模型，不改任何权重）

**Files:** 无代码改动。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 2: 隔离副本里用真实聊天模型各点一次**

构建隔离副本（`--output /tmp/lmd-planF`，`ditto` 到 `/tmp/lmd-planF-iso`，数据根 `/tmp/lmd-planF-iso/data`，模型根沿用 `~/LocalModelDesk`，`LMD_SHELL_PORT=8839`），在聊天页加载一个已下载的聊天模型（优先 `glm`；再用 `superqwen` 各试一次以覆盖推理模型）。

逐项记录（截图存 `/tmp/lmd-planF-notes/`，不入库）：
- 视频·文生：空输入框点「看手气」→ 不弹确认，10–60 秒内写入一段 80–150 字中文提示词；再点一次 → 弹「替换」确认。
- 视频·图生：切到图生视频，点「看手气」→ 提示词写的是动作/镜头/声音，不是静态外观。
- 视频：写「一只猫」点「优化提示词」→ 保留"猫"，补全镜头与声音；「恢复原文」回到「一只猫」。
- 音乐：空风格与歌词点「看手气」→ 两个框都被写入；写好歌词后点「优化提示词」→ 只改风格描述。
- 把得到的视频/音乐提示词各真实生成一次最短作业，确认生成能开始（模型会被驱逐，属预期）。

Expected: 以上全部成立；若推理模型回复里出现 `<think>` 文本或 JSON 解析失败，记录原始回复（服务日志 `logs/desk.log`）并回到 Task 1 补解析用例。

- [ ] **Step 3: 清理**

```bash
pkill -f 'lmd-planF-iso' ; rm -rf /tmp/lmd-planF /tmp/lmd-planF-iso
```
