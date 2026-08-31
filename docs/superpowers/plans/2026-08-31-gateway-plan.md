# gateway 实施计划（TDD）

**日期** 2026-08-31
**模块** gateway —— OpenAI + Anthropic 兼容对外推理接口
**spec** `docs/superpowers/specs/2026-08-31-gateway-spec.md`（R-gateway-01 … R-gateway-10）
**design** `docs/superpowers/specs/2026-08-31-gateway-design.md`
**暴露** `api:openaiListModels`、`api:openaiChatCompletions`、`api:anthropicMessages`、`api:gatewayConfig`、`data:gatewayStatus`
**消费** `api:chatStream`、`api:chatCompletion`、`api:llmStatus`、`data:llmState`、`data:loadedModel`、`data:deskState`、`api:canStartHeavy`、`api:readConfig`、`data:deskConfig`

## 执行约定

- 每个任务严格走：写失败测试 → 跑确认失败 → 写实现 → 跑确认通过 → commit。
- 所有命令在仓库根 `/Users/aa/LocalModelDesk` 执行；`python3 -m pytest` 把 cwd 注入 `sys.path`，`import desk.gateway` 因此可用，不需要安装。
- 测试全部注入 `FakeBackend`、绑 `127.0.0.1` + 端口 0（LAN 用例除外，见 T-09），无真模型、无 0.0.0.0 常驻、秒级跑完。
- 消费的兄弟接口全部收敛在 `GatewayBackend` 协议（进程内注入）；gateway 包内不 import 任何兄弟模块实现。组合根（装配真实 llm/arbiter/foundation 进 backend）属 desk 服务启动代码，**不在本模块任务内**。
- 硬红线：不触碰 `llms/`、`minimax-h3/`、`minimax-music3/`、`outputs/`；不写 `/Applications`；错误就是错误，任何路径不产出伪造的成功响应。

## 文件布局（本计划产出）

```
desk/
  __init__.py                  # 空包标记（foundation 也会创建；先到先建）
  gateway/
    __init__.py                # 公开入口：GatewayService、GatewayBackend、原因码
    errors.py                  # GatewayReject、原因码、两方言错误信封        (T-01)
    openai_dialect.py          # OpenAI 方言纯函数                            (T-02)
    anthropic_dialect.py       # Anthropic 方言纯函数 + 事件状态机            (T-03, T-04)
    backend.py                 # GatewayBackend 协议（消费契约的唯一假设点）  (T-05)
    guard.py                   # 准入判定：503 决策、模型标识匹配             (T-05)
    http_server.py             # ThreadingHTTPServer + 路由 + SSE 写出        (T-06, T-07, T-08)
    service.py                 # 生命周期 + data:gatewayStatus + gatewayConfig(T-09, T-10)
tests/
  gateway_fakes.py             # FakeBackend（记录调用、可编程）              (T-05)
  gateway_client.py            # 起临时服务器 / 发请求 / 读 SSE 帧            (T-06)
  test_gateway_errors.py       # T-01
  test_gateway_openai.py       # T-02, T-06, T-07
  test_gateway_anthropic.py    # T-03, T-04, T-08
  test_gateway_guard.py        # T-05
  test_gateway_service.py      # T-09, T-10
```

## 任务 DAG

```
T-01 errors ─┬─ T-02 openai 纯函数 ──────┬─ T-06 http 核心 + /v1/models ─┬─ T-07 /v1/chat/completions
             ├─ T-03 anthropic 解析/响应 ─┴┐                             ├─ T-08 /v1/messages（还依赖 T-04）
             │      └─ T-04 anthropic 事件状态机 ┘                       └─ T-09 GatewayService ── T-10 gatewayConfig
             └─ T-05 FakeBackend + guard ──┘（T-06 依赖 T-02、T-05）
```

---

## T-gateway-01 错误词汇与两方言信封（`errors.py`）

**红**：写 `tests/test_gateway_errors.py`，跑 `python3 -m pytest tests/test_gateway_errors.py -q` 确认 `ModuleNotFoundError` / 收集失败。

```python
# tests/test_gateway_errors.py
"""errors.py：拒绝异常、原因码、按路径选方言、两方言错误信封（R-gateway-09）。"""
from desk.gateway.errors import (
    ANTHROPIC,
    OPENAI,
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_NO_MODEL_LOADED,
    RETRY_AFTER_SECONDS,
    GatewayReject,
    dialect_for_path,
    error_envelope,
)


def test_reject_carries_code_http_message():
    r = GatewayReject("no_model_loaded", 503, "no chat model is loaded")
    assert isinstance(r, Exception)
    assert (r.code, r.http, r.message) == ("no_model_loaded", 503, "no chat model is loaded")


def test_constants():
    assert RETRY_AFTER_SECONDS == 30
    assert REASON_HEADER == "X-LocalModelDesk-Reason"
    assert REASON_NO_MODEL_LOADED == "no_model_loaded"
    assert REASON_INVALID_REQUEST == "invalid_request"


def test_dialect_for_path():
    assert dialect_for_path("/v1/messages") == ANTHROPIC
    assert dialect_for_path("/v1/messages/count_tokens") == ANTHROPIC
    assert dialect_for_path("/v1/chat/completions") == OPENAI
    assert dialect_for_path("/v1/models") == OPENAI
    assert dialect_for_path("/no/such/path") == OPENAI  # 未知路径用 OpenAI 信封


def test_openai_envelope_400():
    env = error_envelope(OPENAI, GatewayReject("invalid_request", 400, "bad body"))
    assert env == {"error": {"message": "bad body", "type": "invalid_request_error", "code": "invalid_request"}}


def test_openai_envelope_503_type():
    env = error_envelope(OPENAI, GatewayReject("no_model_loaded", 503, "nothing loaded"))
    assert env["error"]["type"] == "service_unavailable_error"
    assert env["error"]["code"] == "no_model_loaded"


def test_anthropic_envelope_503_is_overloaded():
    env = error_envelope(ANTHROPIC, GatewayReject("no_model_loaded", 503, "nothing loaded"))
    assert env == {"type": "error", "error": {"type": "overloaded_error", "message": "nothing loaded"}}


def test_anthropic_envelope_404_is_not_found():
    env = error_envelope(ANTHROPIC, GatewayReject("not_found", 404, "unknown path"))
    assert env["error"]["type"] == "not_found_error"


def test_anthropic_envelope_400():
    env = error_envelope(ANTHROPIC, GatewayReject("invalid_request", 400, "max_tokens is required"))
    assert env["error"]["type"] == "invalid_request_error"
```

**绿**：创建 `desk/__init__.py`（空）、`desk/gateway/__init__.py`（暂只挂文档字符串与 errors 再导出）、`desk/gateway/errors.py`：

```python
# desk/gateway/errors.py
"""gateway 错误词汇的唯一产地：拒绝异常、原因码、两方言错误信封（R-gateway-08/09）。"""
from __future__ import annotations

# 机器可读原因码（X-LocalModelDesk-Reason 头；OpenAI 信封的 error.code）
REASON_MEDIA_JOB_RUNNING = "media_job_running"   # 兜底值；优先用 arbiter 原因码
REASON_NO_MODEL_LOADED = "no_model_loaded"
REASON_MODEL_NOT_LOADED = "model_not_loaded"
REASON_INVALID_REQUEST = "invalid_request"
REASON_NOT_FOUND = "not_found"
REASON_METHOD_NOT_ALLOWED = "method_not_allowed"
REASON_UPSTREAM_ERROR = "upstream_error"

RETRY_AFTER_SECONDS = 30                          # 诚实的保守常量：媒体作业无可靠 ETA
REASON_HEADER = "X-LocalModelDesk-Reason"

OPENAI = "openai"
ANTHROPIC = "anthropic"

_OPENAI_TYPE_BY_HTTP = {
    400: "invalid_request_error",
    404: "invalid_request_error",
    405: "invalid_request_error",
    500: "api_error",
    503: "service_unavailable_error",
}
_ANTHROPIC_TYPE_BY_HTTP = {
    400: "invalid_request_error",
    404: "not_found_error",
    405: "invalid_request_error",
    500: "api_error",
    503: "overloaded_error",
}


class GatewayReject(Exception):
    """请求被拒。code 机器可读，http 是状态码，message 给人看。"""

    def __init__(self, code: str, http: int, message: str):
        super().__init__(message)
        self.code = code
        self.http = http
        self.message = message


def dialect_for_path(path: str) -> str:
    """按路径选错误方言：/v1/messages* 用 Anthropic，其余（含未知路径）用 OpenAI。"""
    if path == "/v1/messages" or path.startswith("/v1/messages/"):
        return ANTHROPIC
    return OPENAI


def error_envelope(dialect: str, reject: GatewayReject) -> dict:
    """方言原生错误信封。任何路径不产出伪造的成功响应（R-gateway-09）。"""
    if dialect == ANTHROPIC:
        return {
            "type": "error",
            "error": {
                "type": _ANTHROPIC_TYPE_BY_HTTP.get(reject.http, "api_error"),
                "message": reject.message,
            },
        }
    return {
        "error": {
            "message": reject.message,
            "type": _OPENAI_TYPE_BY_HTTP.get(reject.http, "api_error"),
            "code": reject.code,
        }
    }
```

```python
# desk/gateway/__init__.py（T-01 时点；T-09 再补 GatewayService / GatewayBackend 导出）
"""gateway：OpenAI + Anthropic 兼容对外推理接口（纯翻译层，不加载、不排队）。"""
from .errors import (  # noqa: F401
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_MEDIA_JOB_RUNNING,
    REASON_METHOD_NOT_ALLOWED,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    REASON_NOT_FOUND,
    REASON_UPSTREAM_ERROR,
    RETRY_AFTER_SECONDS,
    GatewayReject,
)
```

`desk/__init__.py` 内容为一行注释 `# desk 包`（foundation 并行开发也会建它；内容为空即无冲突实质）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_errors.py -q`
**commit** `gateway: errors.py 拒绝异常、原因码与两方言错误信封`

---

## T-gateway-02 OpenAI 方言纯函数（`openai_dialect.py`）

**红**：写 `tests/test_gateway_openai.py`（本任务只有纯函数段；HTTP 段在 T-06/T-07 追加到同文件）。

```python
# tests/test_gateway_openai.py
"""OpenAI 方言：解析/校验、/v1/models 载荷、非流式响应、SSE 分块（R-gateway-01/02/03/09/10）。"""
import json

import pytest

from desk.gateway import openai_dialect
from desk.gateway.errors import REASON_INVALID_REQUEST, GatewayReject

LOADED = {
    "state": "loaded",
    "loaded": {"key": "qwen3-30b", "served_id": "mlx-community/Qwen3-30B-A3B-8bit",
               "loaded_at": 1756600000.0, "meta": {}},
}
RESULT = {"content": "你好！", "reasoning": "用户在打招呼。",
          "finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}}
EVENTS = [("reasoning", "用户在"), ("reasoning", "打招呼。"), ("content", "你"), ("content", "好！"),
          ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}})]


def _reject(body) -> GatewayReject:
    with pytest.raises(GatewayReject) as e:
        openai_dialect.parse_request(body)
    return e.value


# ---- parse_request ----

def test_parse_minimal_defaults():
    parsed = openai_dialect.parse_request({"messages": [{"role": "user", "content": "hi"}]})
    assert parsed == {
        "model": None,
        "stream": False,
        "chat_request": {"messages": [{"role": "user", "content": "hi"}],
                         "max_tokens": 2048, "temperature": None, "top_p": None},
    }


def test_parse_full_fields_passthrough():
    parsed = openai_dialect.parse_request({
        "model": "qwen3-30b", "stream": True, "max_tokens": 64,
        "temperature": 0.2, "top_p": 0.9,
        "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        "metadata": {"ignored": True},   # 未识别顶层字段静默忽略
    })
    assert parsed["model"] == "qwen3-30b"
    assert parsed["stream"] is True
    assert parsed["chat_request"]["max_tokens"] == 64
    assert parsed["chat_request"]["temperature"] == 0.2
    assert parsed["chat_request"]["top_p"] == 0.9
    assert [m["role"] for m in parsed["chat_request"]["messages"]] == ["system", "user"]


def test_parse_stream_must_be_boolean():
    r = _reject({"stream": "yes", "messages": [{"role": "user", "content": "hi"}]})
    assert (r.code, r.http) == (REASON_INVALID_REQUEST, 400)


def test_parse_messages_required():
    assert _reject({}).http == 400
    assert _reject({"messages": "not a list"}).http == 400
    assert _reject({"messages": []}).http == 400
    assert _reject({"messages": [{"role": "user"}]}).http == 400  # content 缺失


def test_parse_tools_rejected_but_empty_tools_ignored():
    body = {"messages": [{"role": "user", "content": "hi"}]}
    assert _reject({**body, "tools": [{"type": "function"}]}).http == 400
    assert _reject({**body, "tool_choice": "auto"}).http == 400
    assert _reject({**body, "functions": [{}]}).http == 400
    # 空列表按「未提供」处理，不拒
    assert openai_dialect.parse_request({**body, "tools": []})["stream"] is False


# ---- models_list（R-gateway-01/10） ----

def test_models_list_empty_when_not_loaded():
    assert openai_dialect.models_list({"state": "idle", "loaded": None}) == {"object": "list", "data": []}
    assert openai_dialect.models_list({"state": "loading", "loaded": None}) == {"object": "list", "data": []}


def test_models_list_two_ids_when_loaded():
    payload = openai_dialect.models_list(LOADED)
    assert payload["object"] == "list"
    assert payload["data"] == [
        {"id": "qwen3-30b", "object": "model", "created": 1756600000, "owned_by": "localmodeldesk"},
        {"id": "mlx-community/Qwen3-30B-A3B-8bit", "object": "model",
         "created": 1756600000, "owned_by": "localmodeldesk"},
    ]


def test_models_list_dedupes_identical_ids():
    status = {"state": "loaded",
              "loaded": {"key": "same", "served_id": "same", "loaded_at": 5.0, "meta": {}}}
    assert [m["id"] for m in openai_dialect.models_list(status)["data"]] == ["same"]


# ---- completion_response（R-gateway-02） ----

def test_completion_response_shape():
    resp = openai_dialect.completion_response(RESULT, "qwen3-30b", "chatcmpl-fixed", 1756605000)
    assert resp == {
        "id": "chatcmpl-fixed",
        "object": "chat.completion",
        "created": 1756605000,
        "model": "qwen3-30b",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "你好！", "reasoning_content": "用户在打招呼。"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
    }


def test_completion_response_omits_empty_reasoning():
    result = {**RESULT, "reasoning": ""}
    msg = openai_dialect.completion_response(result, "m", "id", 1)["choices"][0]["message"]
    assert "reasoning_content" not in msg


def test_completion_response_length_finish():
    result = {**RESULT, "finish_reason": "length"}
    resp = openai_dialect.completion_response(result, "m", "id", 1)
    assert resp["choices"][0]["finish_reason"] == "length"


# ---- stream_chunks（R-gateway-03） ----

def _decode(frames):
    out = []
    for frame in frames:
        line = frame.decode("utf-8")
        assert line.startswith("data: ") and line.endswith("\n\n")
        payload = line[len("data: "):-2]
        out.append(payload if payload == "[DONE]" else json.loads(payload))
    return out


def test_stream_chunks_full_replay():
    frames = list(openai_dialect.stream_chunks(iter(EVENTS), "chatcmpl-fixed", 1756605000, "qwen3-30b"))
    decoded = _decode(frames)
    assert decoded[-1] == "[DONE]"
    chunks = decoded[:-1]
    for c in chunks:
        assert (c["id"], c["object"], c["created"], c["model"]) == (
            "chatcmpl-fixed", "chat.completion.chunk", 1756605000, "qwen3-30b")
    deltas = [c["choices"][0]["delta"] for c in chunks]
    finishes = [c["choices"][0]["finish_reason"] for c in chunks]
    assert deltas == [
        {"role": "assistant"},
        {"reasoning_content": "用户在"},
        {"reasoning_content": "打招呼。"},
        {"content": "你"},
        {"content": "好！"},
        {},
    ]
    assert finishes == [None, None, None, None, None, "stop"]


def test_stream_chunks_midway_error_no_done():
    def events():
        yield ("content", "部分")
        raise RuntimeError("mlx-lm died")
    frames = list(openai_dialect.stream_chunks(events(), "id", 1, "m"))
    decoded = _decode(frames)
    assert "[DONE]" not in decoded
    assert decoded[-1] == {"error": {"message": "mlx-lm died", "type": "api_error"}}


def test_stream_chunks_missing_finish_is_error_not_done():
    frames = list(openai_dialect.stream_chunks(iter([("content", "x")]), "id", 1, "m"))
    decoded = _decode(frames)
    assert "[DONE]" not in decoded
    assert decoded[-1]["error"]["type"] == "api_error"
```

**绿**：

```python
# desk/gateway/openai_dialect.py
"""OpenAI 方言纯函数：解析/校验、/v1/models、非流式响应、SSE 分块。无 IO、无时钟依赖。"""
from __future__ import annotations

import json
from typing import Iterable, Iterator

from .errors import REASON_INVALID_REQUEST, GatewayReject

DEFAULT_MAX_TOKENS = 2048          # 沿现行为（design Assumption 6）
_REJECTED_TOOL_FIELDS = ("tools", "tool_choice", "functions")


def _bad(message: str) -> GatewayReject:
    return GatewayReject(REASON_INVALID_REQUEST, 400, message)


def parse_request(body) -> dict:
    """请求体 dict → {"model", "stream", "chat_request"}；非法 → GatewayReject(400)。"""
    if not isinstance(body, dict):
        raise _bad("request body must be a JSON object")
    stream = body.get("stream", False)
    if not isinstance(stream, bool):
        raise _bad("'stream' must be a boolean")
    for field in _REJECTED_TOOL_FIELDS:
        if body.get(field):
            # 静默忽略工具定义会让客户端拿到语义错误的「成功」——违背不伪造原则
            raise _bad(f"'{field}' is not supported by this gateway")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _bad("'messages' must be a non-empty array")
    parsed_messages = []
    for i, msg in enumerate(messages):
        if (not isinstance(msg, dict)
                or not isinstance(msg.get("role"), str)
                or not isinstance(msg.get("content"), str)):
            raise _bad(f"messages[{i}] must be an object with string 'role' and string 'content'")
        parsed_messages.append({"role": msg["role"], "content": msg["content"]})
    max_tokens = body.get("max_tokens", DEFAULT_MAX_TOKENS)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise _bad("'max_tokens' must be a positive integer")
    model = body.get("model")
    if model is not None and not isinstance(model, str):
        raise _bad("'model' must be a string")
    return {
        "model": model or None,
        "stream": stream,
        "chat_request": {
            "messages": parsed_messages,
            "max_tokens": max_tokens,
            "temperature": body.get("temperature"),
            "top_p": body.get("top_p"),
        },
    }


def models_list(llm_status: dict) -> dict:
    """api:llmStatus 载荷 → GET /v1/models 响应。未加载 → 空列表而非报错（R-gateway-01）。"""
    loaded = llm_status.get("loaded")
    if llm_status.get("state") != "loaded" or not loaded:
        return {"object": "list", "data": []}
    created = int(loaded["loaded_at"])     # 唯一时间来源：data:llmState.loaded_at，不自记时钟
    ids = [loaded["key"]]
    if loaded["served_id"] != loaded["key"]:
        ids.append(loaded["served_id"])    # 两个可接受标识各列一条（R-gateway-10）
    return {"object": "list",
            "data": [{"id": mid, "object": "model", "created": created, "owned_by": "localmodeldesk"}
                     for mid in ids]}


def completion_response(result: dict, model: str, completion_id: str, created: int) -> dict:
    """ChatResult → OpenAI 非流式响应（R-gateway-02）。"""
    message = {"role": "assistant", "content": result["content"]}
    if result.get("reasoning"):
        message["reasoning_content"] = result["reasoning"]
    usage = result["usage"]
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": result["finish_reason"]}],
        "usage": {
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
        },
    }


def _chunk(completion_id: str, created: int, model: str, delta: dict, finish_reason=None) -> bytes:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return b"data: " + json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n\n"


def _error_frame(message: str) -> bytes:
    envelope = {"error": {"message": message, "type": "api_error"}}
    return b"data: " + json.dumps(envelope, ensure_ascii=False).encode("utf-8") + b"\n\n"


def stream_chunks(events: Iterable[tuple], completion_id: str, created: int, model: str) -> Iterator[bytes]:
    """ChatEvent 元组流 → OpenAI SSE 帧流（R-gateway-03）。

    下游中途抛错：写一块 error 后终止，不发 [DONE]——失败流不冒充完整（R-gateway-09）。
    """
    yield _chunk(completion_id, created, model, {"role": "assistant"})
    try:
        for kind, payload in events:
            if kind == "content":
                yield _chunk(completion_id, created, model, {"content": payload})
            elif kind == "reasoning":
                yield _chunk(completion_id, created, model, {"reasoning_content": payload})
            elif kind == "finish":
                yield _chunk(completion_id, created, model, {}, finish_reason=payload["finish_reason"])
                yield b"data: [DONE]\n\n"
                return
    except Exception as exc:  # noqa: BLE001 —— 错误就是错误，原样上报
        yield _error_frame(str(exc))
        return
    # 流终止却没有 finish 事件：按上游故障处理，不数 token、不伪造用量
    yield _error_frame("upstream stream ended without a finish event")
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_openai.py -q`
**commit** `gateway: OpenAI 方言纯函数（解析/models/非流式/SSE 分块）`

---

## T-gateway-03 Anthropic 解析与非流式响应（`anthropic_dialect.py`）

**红**：写 `tests/test_gateway_anthropic.py`（本任务纯解析/响应段；事件状态机在 T-04、HTTP 在 T-08 追加）。

```python
# tests/test_gateway_anthropic.py
"""Anthropic 方言：解析（system 两形态、内容块）、非流式响应、事件序列（R-gateway-04/05/06/09）。"""
import json

import pytest

from desk.gateway import anthropic_dialect
from desk.gateway.errors import REASON_INVALID_REQUEST, GatewayReject

RESULT = {"content": "你好！", "reasoning": "用户在打招呼。",
          "finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}}
BASE = {"max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]}


def _reject(body) -> GatewayReject:
    with pytest.raises(GatewayReject) as e:
        anthropic_dialect.parse_request(body)
    return e.value


# ---- parse_request（R-gateway-06） ----

def test_parse_minimal():
    parsed = anthropic_dialect.parse_request(dict(BASE))
    assert parsed == {
        "model": None,
        "stream": False,
        "chat_request": {"messages": [{"role": "user", "content": "hi"}],
                         "max_tokens": 100, "temperature": None, "top_p": None},
    }


def test_parse_max_tokens_required():
    r = _reject({"messages": [{"role": "user", "content": "hi"}]})
    assert (r.code, r.http) == (REASON_INVALID_REQUEST, 400)
    assert _reject({**BASE, "max_tokens": "100"}).http == 400
    assert _reject({**BASE, "max_tokens": 0}).http == 400


def test_parse_system_string_prepended():
    parsed = anthropic_dialect.parse_request({**BASE, "system": "你是台面助手"})
    assert parsed["chat_request"]["messages"][0] == {"role": "system", "content": "你是台面助手"}
    assert parsed["chat_request"]["messages"][1] == {"role": "user", "content": "hi"}


def test_parse_system_block_array_concatenated():
    parsed = anthropic_dialect.parse_request({
        **BASE, "system": [{"type": "text", "text": "你是"}, {"type": "text", "text": "台面助手"}]})
    assert parsed["chat_request"]["messages"][0] == {"role": "system", "content": "你是台面助手"}


def test_parse_multiturn_order_preserved_with_block_content():
    parsed = anthropic_dialect.parse_request({
        "max_tokens": 50,
        "system": "s",
        "messages": [
            {"role": "user", "content": "第一轮"},
            {"role": "assistant", "content": [{"type": "text", "text": "回"}, {"type": "text", "text": "答"}]},
            {"role": "user", "content": "第二轮"},
        ],
    })
    msgs = parsed["chat_request"]["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [
        ("system", "s"), ("user", "第一轮"), ("assistant", "回答"), ("user", "第二轮")]


def test_parse_non_text_block_rejected():
    r = _reject({**BASE, "messages": [
        {"role": "user", "content": [{"type": "image", "source": {}}]}]})
    assert r.http == 400  # 不支持即明说，不静默丢弃


def test_parse_stream_must_be_boolean_and_tools_rejected():
    assert _reject({**BASE, "stream": "yes"}).http == 400
    assert _reject({**BASE, "tools": [{"name": "t"}]}).http == 400
    assert _reject({**BASE, "tool_choice": {"type": "auto"}}).http == 400
    # 未识别顶层字段静默忽略
    parsed = anthropic_dialect.parse_request({**BASE, "metadata": {"user_id": "x"}, "top_k": 5})
    assert parsed["stream"] is False


# ---- message_response（R-gateway-04/06） ----

def test_message_response_shape():
    resp = anthropic_dialect.message_response(RESULT, "qwen3-30b", "msg_fixed")
    assert resp == {
        "id": "msg_fixed",
        "type": "message",
        "role": "assistant",
        "model": "qwen3-30b",
        "content": [
            {"type": "thinking", "thinking": "用户在打招呼。"},
            {"type": "text", "text": "你好！"},
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 12, "output_tokens": 7},
    }


def test_message_response_length_maps_to_max_tokens():
    resp = anthropic_dialect.message_response({**RESULT, "finish_reason": "length"}, "m", "msg_1")
    assert resp["stop_reason"] == "max_tokens"


def test_message_response_no_thinking_block_when_reasoning_empty():
    resp = anthropic_dialect.message_response({**RESULT, "reasoning": ""}, "m", "msg_1")
    assert resp["content"] == [{"type": "text", "text": "你好！"}]
```

**绿**：

```python
# desk/gateway/anthropic_dialect.py
"""Anthropic 方言纯函数：解析（system 两形态、内容块数组）、非流式响应、SSE 事件序列。无 IO、无时钟。"""
from __future__ import annotations

import json
from typing import Iterable, Iterator

from .errors import REASON_INVALID_REQUEST, GatewayReject

_REJECTED_TOOL_FIELDS = ("tools", "tool_choice")
_STOP_REASON = {"stop": "end_turn", "length": "max_tokens"}


def _bad(message: str) -> GatewayReject:
    return GatewayReject(REASON_INVALID_REQUEST, 400, message)


def _text_from_blocks(blocks, where: str) -> str:
    parts = []
    for i, block in enumerate(blocks):
        if (not isinstance(block, dict) or block.get("type") != "text"
                or not isinstance(block.get("text"), str)):
            raise _bad(f"{where}[{i}]: only 'text' content blocks are supported")
        parts.append(block["text"])
    return "".join(parts)


def parse_request(body) -> dict:
    """请求体 dict → {"model", "stream", "chat_request"}；非法 → GatewayReject(400)。

    max_tokens 必填（Anthropic 方言硬约定）；system 收字符串或 text 块数组，
    并入下游首条 system 消息；非 text 内容块一律 400，不静默丢弃。
    """
    if not isinstance(body, dict):
        raise _bad("request body must be a JSON object")
    stream = body.get("stream", False)
    if not isinstance(stream, bool):
        raise _bad("'stream' must be a boolean")
    for field in _REJECTED_TOOL_FIELDS:
        if body.get(field):
            raise _bad(f"'{field}' is not supported by this gateway")
    max_tokens = body.get("max_tokens")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise _bad("'max_tokens' is required and must be a positive integer")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _bad("'messages' must be a non-empty array")

    parsed = []
    system = body.get("system")
    if system is not None:
        if isinstance(system, str):
            system_text = system
        elif isinstance(system, list):
            system_text = _text_from_blocks(system, "system")
        else:
            raise _bad("'system' must be a string or an array of text blocks")
        parsed.append({"role": "system", "content": system_text})
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict) or not isinstance(msg.get("role"), str):
            raise _bad(f"messages[{i}] must be an object with a string 'role'")
        content = msg.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = _text_from_blocks(content, f"messages[{i}].content")
        else:
            raise _bad(f"messages[{i}].content must be a string or an array of content blocks")
        parsed.append({"role": msg["role"], "content": text})

    model = body.get("model")
    if model is not None and not isinstance(model, str):
        raise _bad("'model' must be a string")
    return {
        "model": model or None,
        "stream": stream,
        "chat_request": {
            "messages": parsed,
            "max_tokens": max_tokens,
            "temperature": body.get("temperature"),
            "top_p": body.get("top_p"),
        },
    }


def message_response(result: dict, model: str, message_id: str) -> dict:
    """ChatResult → Anthropic 非流式响应（R-gateway-04/06）。

    reasoning 非空 → thinking 块置于 text 块之前；text 块永远在（空正文如实给空串）。
    """
    content = []
    if result.get("reasoning"):
        content.append({"type": "thinking", "thinking": result["reasoning"]})
    content.append({"type": "text", "text": result["content"]})
    usage = result["usage"]
    return {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": _STOP_REASON[result["finish_reason"]],
        "stop_sequence": None,
        "usage": {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]},
    }
```

（`stream_events` 在 T-04 加入同一文件。）

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_anthropic.py -q`
**commit** `gateway: Anthropic 方言解析与非流式响应`

---

## T-gateway-04 Anthropic 流式事件状态机（`stream_events`）

**红**：在 `tests/test_gateway_anthropic.py` 追加：

```python
# tests/test_gateway_anthropic.py 追加

EVENTS = [("reasoning", "用户在"), ("reasoning", "打招呼。"), ("content", "你"), ("content", "好！"),
          ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}})]


def _decode_frames(frames):
    """断言每帧恰好 event:/data: 两行，返回 [(事件名, data dict)]。"""
    out = []
    for frame in frames:
        text = frame.decode("utf-8")
        assert text.endswith("\n\n")
        lines = text[:-2].split("\n")
        assert len(lines) == 2, f"每个事件必须恰好两行: {lines!r}"
        assert lines[0].startswith("event: ") and lines[1].startswith("data: ")
        out.append((lines[0][len("event: "):], json.loads(lines[1][len("data: "):])))
    return out


def test_stream_events_full_sequence():
    frames = list(anthropic_dialect.stream_events(iter(EVENTS), "msg_fixed", "qwen3-30b"))
    decoded = _decode_frames(frames)
    assert [name for name, _ in decoded] == [
        "message_start",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "message_delta", "message_stop",
    ]
    start = decoded[0][1]
    assert start["type"] == "message_start"
    assert start["message"]["id"] == "msg_fixed"
    assert start["message"]["model"] == "qwen3-30b"
    assert start["message"]["content"] == []
    assert start["message"]["usage"] == {"input_tokens": 0, "output_tokens": 0}  # 占位，真值在 message_delta

    thinking_start = decoded[1][1]
    assert thinking_start == {"type": "content_block_start", "index": 0,
                              "content_block": {"type": "thinking", "thinking": ""}}
    assert decoded[2][1] == {"type": "content_block_delta", "index": 0,
                             "delta": {"type": "thinking_delta", "thinking": "用户在"}}
    assert decoded[4][1] == {"type": "content_block_stop", "index": 0}

    text_start = decoded[5][1]
    assert text_start == {"type": "content_block_start", "index": 1,
                          "content_block": {"type": "text", "text": ""}}
    assert decoded[6][1] == {"type": "content_block_delta", "index": 1,
                             "delta": {"type": "text_delta", "text": "你"}}
    assert decoded[8][1] == {"type": "content_block_stop", "index": 1}

    delta = decoded[9][1]
    assert delta["delta"] == {"stop_reason": "end_turn", "stop_sequence": None}
    assert delta["usage"] == {"input_tokens": 12, "output_tokens": 7}
    assert decoded[10][1] == {"type": "message_stop"}


def test_stream_events_content_only_starts_at_index_zero():
    events = [("content", "hi"),
              ("finish", {"finish_reason": "length", "usage": {"prompt_tokens": 1, "completion_tokens": 2}})]
    decoded = _decode_frames(list(anthropic_dialect.stream_events(iter(events), "msg_1", "m")))
    names = [n for n, _ in decoded]
    assert names == ["message_start", "content_block_start", "content_block_delta",
                     "content_block_stop", "message_delta", "message_stop"]
    assert decoded[1][1]["index"] == 0
    assert decoded[1][1]["content_block"] == {"type": "text", "text": ""}
    assert decoded[4][1]["delta"]["stop_reason"] == "max_tokens"


def test_stream_events_interleaved_reopens_blocks():
    # llm 保证 reasoning 在前；若交错出现，状态机如实开/关块，事件语法仍合法
    events = [("content", "a"), ("reasoning", "r"), ("content", "b"),
              ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 1, "completion_tokens": 1}})]
    decoded = _decode_frames(list(anthropic_dialect.stream_events(iter(events), "msg_1", "m")))
    starts = [(d["index"], d["content_block"]["type"]) for n, d in decoded if n == "content_block_start"]
    assert starts == [(0, "text"), (1, "thinking"), (2, "text")]


def test_stream_events_empty_content_still_emits_text_block():
    # 空正文：与非流式的空 text 块一致，开/关一个空 text 块，不伪造增量
    events = [("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 1, "completion_tokens": 0}})]
    decoded = _decode_frames(list(anthropic_dialect.stream_events(iter(events), "msg_1", "m")))
    names = [n for n, _ in decoded]
    assert names == ["message_start", "content_block_start", "content_block_stop",
                     "message_delta", "message_stop"]
    assert decoded[1][1]["content_block"] == {"type": "text", "text": ""}


def test_stream_events_midway_error_no_message_stop():
    def events():
        yield ("content", "部分")
        raise RuntimeError("mlx-lm died")
    decoded = _decode_frames(list(anthropic_dialect.stream_events(events(), "msg_1", "m")))
    names = [n for n, _ in decoded]
    assert "message_stop" not in names
    assert names[-1] == "error"
    assert decoded[-1][1] == {"type": "error",
                              "error": {"type": "api_error", "message": "mlx-lm died"}}


def test_stream_events_missing_finish_is_error():
    decoded = _decode_frames(list(anthropic_dialect.stream_events(iter([("content", "x")]), "msg_1", "m")))
    assert [n for n, _ in decoded][-1] == "error"
    assert "message_stop" not in [n for n, _ in decoded]
```

**绿**：在 `desk/gateway/anthropic_dialect.py` 追加：

```python
# desk/gateway/anthropic_dialect.py 追加

def _frame(name: str, data: dict) -> bytes:
    """每个事件严格两行：event: + data:（R-gateway-05）。"""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


_DELTA_BY_TYPE = {"thinking": ("thinking_delta", "thinking"), "text": ("text_delta", "text")}


def stream_events(events: Iterable[tuple], message_id: str, model: str) -> Iterator[bytes]:
    """ChatEvent 元组流 → Anthropic SSE 事件流（R-gateway-05/06）。

    两态小状态机（当前块类型 × 是否已开块）：类型切换先 stop 再 start。
    message_start 的 usage 以 0 占位、真值在 message_delta——Anthropic 原生行为，非伪造。
    下游中途抛错：发原生 event: error 后终止，不发 message_stop（R-gateway-09）。
    不发 ping（可选事件，YAGNI）。
    """
    yield _frame("message_start", {
        "type": "message_start",
        "message": {"id": message_id, "type": "message", "role": "assistant", "model": model,
                    "content": [], "stop_reason": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}},
    })
    index = -1
    open_type = None            # None | "thinking" | "text"
    text_emitted = False

    def _start(btype: str) -> bytes:
        block = {"type": "thinking", "thinking": ""} if btype == "thinking" else {"type": "text", "text": ""}
        return _frame("content_block_start",
                      {"type": "content_block_start", "index": index, "content_block": block})

    def _stop() -> bytes:
        return _frame("content_block_stop", {"type": "content_block_stop", "index": index})

    try:
        for kind, payload in events:
            if kind == "finish":
                if open_type is not None:
                    yield _stop()
                    open_type = None
                if not text_emitted:
                    # 正文为空也如实给一个空 text 块（与非流式响应的空 text 块一致）
                    index += 1
                    yield _start("text")
                    yield _stop()
                usage = payload["usage"]
                yield _frame("message_delta", {
                    "type": "message_delta",
                    "delta": {"stop_reason": _STOP_REASON[payload["finish_reason"]],
                              "stop_sequence": None},
                    "usage": {"input_tokens": usage["prompt_tokens"],
                              "output_tokens": usage["completion_tokens"]},
                })
                yield _frame("message_stop", {"type": "message_stop"})
                return
            btype = "thinking" if kind == "reasoning" else "text"
            if open_type != btype:
                if open_type is not None:
                    yield _stop()
                index += 1
                yield _start(btype)
                open_type = btype
                text_emitted = text_emitted or btype == "text"
            delta_type, key = _DELTA_BY_TYPE[btype]
            yield _frame("content_block_delta",
                         {"type": "content_block_delta", "index": index,
                          "delta": {"type": delta_type, key: payload}})
    except Exception as exc:  # noqa: BLE001 —— 错误就是错误
        yield _frame("error", {"type": "error", "error": {"type": "api_error", "message": str(exc)}})
        return
    yield _frame("error", {"type": "error",
                           "error": {"type": "api_error",
                                     "message": "upstream stream ended without a finish event"}})
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_anthropic.py -q`
**commit** `gateway: Anthropic 流式事件状态机（严格 event/data 两行、错误不发 message_stop）`

---

## T-gateway-05 GatewayBackend 协议、FakeBackend 与准入判定（`backend.py` / `guard.py`）

**红**：写 `tests/gateway_fakes.py`（测试基础设施，非测试文件）与 `tests/test_gateway_guard.py`。

```python
# tests/gateway_fakes.py
"""gateway 测试共用假后端：记录每一次调用，可编程状态/结果/事件/故障。"""
from __future__ import annotations

import copy

LOADED_STATUS = {
    "state": "loaded",
    "loaded": {"key": "qwen3-30b", "served_id": "mlx-community/Qwen3-30B-A3B-8bit",
               "loaded_at": 1756600000.0, "meta": {}},
}
IDLE_STATUS = {"state": "idle", "loaded": None}
IDLE_DESK = {
    "holder": None, "media_busy": False,
    "can_start": {"llm": {"ok": True, "reason": None}, "media": {"ok": True, "reason": None}},
}
MEDIA_DESK = {
    "holder": {"kind": "video", "label": "H3 视频", "phase": "running"}, "media_busy": True,
    "can_start": {"llm": {"ok": False, "reason": {"code": "media_busy", "message": "视频作业进行中"}},
                  "media": {"ok": False, "reason": {"code": "media_busy", "message": "视频作业进行中"}}},
}
MEDIA_REFUSAL = {"ok": False, "reason": {"code": "media_busy", "message": "视频作业进行中"}}
RESULT = {"content": "你好！", "reasoning": "用户在打招呼。",
          "finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}}
EVENTS = [("reasoning", "用户在"), ("reasoning", "打招呼。"), ("content", "你"), ("content", "好！"),
          ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}})]

QUERY_METHODS = {"llm_status", "desk_state", "can_start_heavy"}   # 只读查询；chat_* 之外的全部


class FakeBackend:
    """GatewayBackend 的可编程假实现。calls 逐条记录 (方法名, 参数…)。

    协议上**没有** load/unload/acquire 方法——「绝不自动加载」的结构性保证；
    调用记录再做二次证明。
    """

    def __init__(self, *, llm=None, desk=None, can_start=None, result=None,
                 events=None, stream_error=None, completion_error=None):
        self.calls = []
        self._llm = llm if llm is not None else LOADED_STATUS
        self._desk = desk if desk is not None else IDLE_DESK
        self._can_start = can_start if can_start is not None else {"ok": True, "reason": None}
        self._result = result if result is not None else RESULT
        self._events = list(events) if events is not None else list(EVENTS)
        self._stream_error = stream_error
        self._completion_error = completion_error

    # --- 状态查询（api:llmStatus / data:deskState / api:canStartHeavy） ---
    def llm_status(self):
        self.calls.append(("llm_status",))
        return copy.deepcopy(self._llm)

    def desk_state(self):
        self.calls.append(("desk_state",))
        return copy.deepcopy(self._desk)

    def can_start_heavy(self, kind):
        self.calls.append(("can_start_heavy", kind))
        return copy.deepcopy(self._can_start)

    # --- 推理（api:chatCompletion / api:chatStream） ---
    def chat_completion(self, req):
        self.calls.append(("chat_completion", copy.deepcopy(req)))
        if self._completion_error is not None:
            raise self._completion_error
        return copy.deepcopy(self._result)

    def chat_stream(self, req):
        self.calls.append(("chat_stream", copy.deepcopy(req)))

        def gen():
            for event in self._events:
                yield event
            if self._stream_error is not None:
                raise self._stream_error

        return gen()

    # --- 断言助手 ---
    def called_methods(self):
        return [c[0] for c in self.calls]

    def assert_no_inference_calls(self):
        assert set(self.called_methods()) <= QUERY_METHODS, \
            f"503 路径不得触发任何推理/加载调用: {self.calls!r}"
```

```python
# tests/test_gateway_guard.py
"""guard.admit：503 决策顺序、模型标识匹配、绝不触发加载（R-gateway-08/10）。"""
import pytest

from desk.gateway.errors import (
    REASON_MEDIA_JOB_RUNNING,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    GatewayReject,
)
from desk.gateway.guard import admit
from gateway_fakes import (
    IDLE_STATUS,
    LOADED_STATUS,
    MEDIA_DESK,
    MEDIA_REFUSAL,
    FakeBackend,
)


def _rejected(backend, model=None) -> GatewayReject:
    with pytest.raises(GatewayReject) as e:
        admit(backend, model)
    backend.assert_no_inference_calls()
    return e.value


def test_admit_ok_returns_loaded():
    backend = FakeBackend()
    loaded = admit(backend, None)
    assert loaded["key"] == "qwen3-30b"
    assert loaded["served_id"] == "mlx-community/Qwen3-30B-A3B-8bit"
    backend.assert_no_inference_calls()   # admit 本身只做只读查询


def test_admit_accepts_key_and_served_id_and_empty():
    for model in ("qwen3-30b", "mlx-community/Qwen3-30B-A3B-8bit", None, ""):
        assert admit(FakeBackend(), model)["key"] == "qwen3-30b"


def test_media_busy_uses_arbiter_reason_code():
    backend = FakeBackend(desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    r = _rejected(backend)
    assert (r.http, r.code) == (503, "media_busy")       # arbiter 词汇优先，全台面同一套
    assert "视频作业进行中" in r.message
    assert ("can_start_heavy", "llm") in backend.calls


def test_media_busy_falls_back_to_local_code():
    backend = FakeBackend(desk=MEDIA_DESK, can_start={"ok": True, "reason": None})
    r = _rejected(backend)
    assert (r.http, r.code) == (503, REASON_MEDIA_JOB_RUNNING)


def test_media_busy_checked_before_model_state():
    backend = FakeBackend(llm=IDLE_STATUS, desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    assert _rejected(backend).code == "media_busy"       # 判定顺序：媒体在前


def test_no_model_loaded():
    for status in (IDLE_STATUS, {"state": "loading", "loaded": None}, {"state": "error", "loaded": None}):
        r = _rejected(FakeBackend(llm=status))
        assert (r.http, r.code) == (503, REASON_NO_MODEL_LOADED)


def test_model_mismatch_names_resident_model():
    r = _rejected(FakeBackend(), "gpt-4o")
    assert (r.http, r.code) == (503, REASON_MODEL_NOT_LOADED)
    assert "gpt-4o" in r.message
    assert "qwen3-30b" in r.message                      # 指明当前驻留的是谁，不静默换模型


def test_backend_protocol_has_no_load_paths():
    # 结构性保证：协议对象上根本没有加载/卸载/acquire 方法可调
    backend = FakeBackend()
    for forbidden in ("load_llm", "unload_llm", "acquire_heavy", "release_heavy"):
        assert not hasattr(backend, forbidden)
```

**绿**：

```python
# desk/gateway/backend.py
"""GatewayBackend 协议：gateway 对兄弟模块暴露/消费形状的唯一假设点（进程内注入）。

组合根（desk 服务启动代码）用 llm / arbiter / foundation 的真实实现装配它；
测试注入 FakeBackend。协议上**没有**任何加载/卸载/acquire 方法——
「绝不自动加载」（R-gateway-08）的结构性保证。
"""
from __future__ import annotations

from typing import Iterator, Protocol

# ChatRequest = {"messages": [{"role": str, "content": str}],
#                "max_tokens": int, "temperature": float | None, "top_p": float | None}
# ChatResult  = {"content": str, "reasoning": str,
#                "finish_reason": "stop" | "length",
#                "usage": {"prompt_tokens": int, "completion_tokens": int}}
# ChatEvent   = ("reasoning", str) | ("content", str)
#             | ("finish", {"finish_reason": ..., "usage": {...}})   # 成功流的最后一个事件，必带两值


class GatewayBackend(Protocol):
    def llm_status(self) -> dict:
        """api:llmStatus → {"state": data:llmState.status,
        "loaded": None | {"key", "served_id", "loaded_at", "meta"}（data:loadedModel）}"""
        ...

    def desk_state(self) -> dict:
        """data:deskState → {"holder": None | {"kind", "label", "phase"},
        "media_busy": bool, "can_start": {...}}"""
        ...

    def can_start_heavy(self, kind: str) -> dict:
        """api:canStartHeavy → {"ok": bool, "reason": None | {"code", "message"}}（arbiter 原因码）"""
        ...

    def chat_completion(self, req: dict) -> dict:
        """api:chatCompletion（非流式）→ ChatResult；失败抛异常"""
        ...

    def chat_stream(self, req: dict) -> Iterator[tuple]:
        """api:chatStream（流式）→ ChatEvent 元组流；中途失败抛异常"""
        ...
```

```python
# desk/gateway/guard.py
"""准入判定（R-gateway-08/10）：503 决策与模型标识匹配。

此文件里**不存在**任何触发加载/卸载/acquire 的调用路径——GatewayBackend 协议上
根本没有这些方法；测试用调用记录二次证明。
"""
from __future__ import annotations

from .errors import (
    REASON_MEDIA_JOB_RUNNING,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    GatewayReject,
)


def admit(backend, requested_model):
    """通过返回 loaded（data:loadedModel，含 key/served_id）；失败抛 GatewayReject(503)。

    判定顺序：1) 媒体作业在跑 2) 无模型驻留 3) 请求 model 与驻留不符。
    绝不自动加载、绝不排队等待。
    """
    desk = backend.desk_state()
    if desk.get("media_busy"):
        code = REASON_MEDIA_JOB_RUNNING
        message = "a media job is running; the gateway never queues or evicts"
        probe = backend.can_start_heavy("llm") or {}
        reason = probe.get("reason") or {}
        if reason.get("code"):                 # arbiter 原因码优先，全台面同一套词汇
            code = reason["code"]
            message = reason.get("message") or message
        raise GatewayReject(code, 503, message)

    status = backend.llm_status()
    loaded = status.get("loaded")
    if status.get("state") != "loaded" or not loaded:
        raise GatewayReject(REASON_NO_MODEL_LOADED, 503,
                            "no chat model is loaded; the gateway never auto-loads")

    if requested_model and requested_model not in (loaded["key"], loaded["served_id"]):
        raise GatewayReject(
            REASON_MODEL_NOT_LOADED, 503,
            f"requested model '{requested_model}' is not the resident model; "
            f"currently loaded: '{loaded['key']}' (served id '{loaded['served_id']}')")
    return loaded
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_guard.py -q`
**commit** `gateway: GatewayBackend 协议、FakeBackend 与 guard 准入判定`

---

## T-gateway-06 HTTP 服务器核心 + `GET /v1/models`（`http_server.py`）→ **api:openaiListModels**

**红**：写 `tests/gateway_client.py`（基础设施）并在 `tests/test_gateway_openai.py` 追加 HTTP 段。

```python
# tests/gateway_client.py
"""gateway 测试 HTTP 客户端：起临时服务器、发请求、读 SSE 帧。全部 127.0.0.1 + 端口 0。"""
from __future__ import annotations

import contextlib
import http.client
import json
import threading

from desk.gateway.http_server import GatewayHTTPServer

FIXED_NOW = 1756605000
FIXED_ID = "fixedfixedfixedfixedfixedfixed00"


@contextlib.contextmanager
def serve(backend, *, now=lambda: FIXED_NOW, new_id=lambda: FIXED_ID):
    server = GatewayHTTPServer(("127.0.0.1", 0), backend, now=now, new_id=new_id)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def request(port, method, path, body=None, host="127.0.0.1"):
    """返回 (status, {小写头: 值}, 原始字节)。body 为 dict 时按 JSON 编码。"""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    payload = None
    if body is not None:
        payload = body if isinstance(body, (bytes, str)) else json.dumps(body, ensure_ascii=False)
    try:
        conn.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        raw = resp.read()
        headers = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, headers, raw
    finally:
        conn.close()


def json_request(port, method, path, body=None, host="127.0.0.1"):
    status, headers, raw = request(port, method, path, body, host=host)
    return status, headers, json.loads(raw)


def sse_request(port, path, body):
    """POST 并读完整个 SSE 响应（服务端流结束即关连接），按空行切帧。"""
    status, headers, raw = request(port, "POST", path, body)
    frames = [f + "\n\n" for f in raw.decode("utf-8").split("\n\n") if f]
    return status, headers, frames
```

```python
# tests/test_gateway_openai.py 追加（文件顶部补 import）
from desk.gateway.errors import REASON_HEADER
from gateway_client import FIXED_NOW, json_request, request, serve, sse_request
from gateway_fakes import IDLE_STATUS, FakeBackend


# ---- HTTP：GET /v1/models（R-gateway-01） ----

def test_http_models_empty_when_idle():
    with serve(FakeBackend(llm=IDLE_STATUS)) as port:
        status, _, payload = json_request(port, "GET", "/v1/models")
    assert status == 200
    assert payload == {"object": "list", "data": []}


def test_http_models_lists_loaded_identifiers():
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "GET", "/v1/models")
    assert status == 200
    assert [m["id"] for m in payload["data"]] == ["qwen3-30b", "mlx-community/Qwen3-30B-A3B-8bit"]
    for m in payload["data"]:
        assert m["object"] == "model"
        assert m["created"] == 1756600000
        assert m["owned_by"] == "localmodeldesk"


# ---- HTTP：路由错误（R-gateway-09） ----

def test_http_unknown_path_404_openai_envelope():
    with serve(FakeBackend()) as port:
        status, headers, payload = json_request(port, "GET", "/no/such/path")
    assert status == 404
    assert payload["error"]["type"] == "invalid_request_error"
    assert headers[REASON_HEADER.lower()] == "not_found"


def test_http_unknown_path_under_messages_gets_anthropic_envelope():
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "GET", "/v1/messages/count_tokens")
    assert status == 404
    assert payload == {"type": "error",
                       "error": {"type": "not_found_error",
                                 "message": "unknown path: /v1/messages/count_tokens"}}


def test_http_method_not_allowed():
    with serve(FakeBackend()) as port:
        s1, _, p1 = json_request(port, "POST", "/v1/models", body={})
        s2, _, _ = json_request(port, "GET", "/v1/chat/completions")
    assert (s1, s2) == (405, 405)
    assert p1["error"]["code"] == "method_not_allowed"


def test_http_oversized_body_400():
    with serve(FakeBackend()) as port:
        big = b'{"messages": "' + b"x" * (10 * 1024 * 1024) + b'"}'
        status, _, payload = json_request(port, "POST", "/v1/chat/completions", body=big)
    assert status == 400
    assert payload["error"]["code"] == "invalid_request"
```

**绿**：

```python
# desk/gateway/http_server.py
"""gateway 的 HTTP 面：路由、读体、JSON/SSE 写出、断连处理。

协议内容全部来自方言纯函数与 guard；本文件只做 socket 搬运。
同进程第二监听器：台面 UI 在 127.0.0.1:8766（兄弟模块所有），gateway 按配置绑独立端口。
"""
from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import anthropic_dialect, guard, openai_dialect
from .errors import (
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_METHOD_NOT_ALLOWED,
    REASON_NOT_FOUND,
    REASON_UPSTREAM_ERROR,
    RETRY_AFTER_SECONDS,
    GatewayReject,
    dialect_for_path,
    error_envelope,
)

MAX_BODY_BYTES = 10 * 1024 * 1024


def _new_id() -> str:
    return uuid.uuid4().hex


class GatewayHTTPServer(ThreadingHTTPServer):
    """每请求一线程；now/new_id 可注入保证测试确定性。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, backend, *, now=time.time, new_id=_new_id):
        super().__init__(address, _Handler)
        self.backend = backend
        self.now = now
        self.new_id = new_id


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: GatewayHTTPServer

    def log_message(self, fmt, *args):  # 不往 stderr 刷访问日志
        pass

    # ---- 写出 ----

    def _send_json(self, code: int, payload: dict, extra_headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_reject(self, reject: GatewayReject):
        headers = [(REASON_HEADER, reject.code)]
        if reject.http == 503:
            headers.append(("Retry-After", str(RETRY_AFTER_SECONDS)))
        self._send_json(reject.http, error_envelope(dialect_for_path(self.path), reject), headers)

    def _stream(self, frames):
        """SSE 写出：503/400 都在此之前以 JSON 返回，永不出现半截 SSE。"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for frame in frames:
                self.wfile.write(frame)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # 客户端断开：记号即关闭下游迭代器，无其他动作
        finally:
            close = getattr(frames, "close", None)
            if close is not None:
                close()          # 传导给下游生成器（llm 借此终止生成）
            self.close_connection = True

    # ---- 读体 ----

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            raise GatewayReject(REASON_INVALID_REQUEST, 400,
                                f"request body exceeds {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(raw)
        except ValueError:
            raise GatewayReject(REASON_INVALID_REQUEST, 400, "request body is not valid JSON") from None

    # ---- 路由 ----

    def do_GET(self):
        try:
            if self.path == "/v1/models":
                self._send_json(200, openai_dialect.models_list(self.server.backend.llm_status()))
            elif self.path in ("/v1/chat/completions", "/v1/messages"):
                raise GatewayReject(REASON_METHOD_NOT_ALLOWED, 405, f"{self.path} requires POST")
            else:
                raise GatewayReject(REASON_NOT_FOUND, 404, f"unknown path: {self.path}")
        except GatewayReject as reject:
            self._send_reject(reject)

    def do_POST(self):
        try:
            if self.path == "/v1/chat/completions":
                self._chat(openai_dialect)
            elif self.path == "/v1/messages":
                self._chat(anthropic_dialect)
            elif self.path == "/v1/models":
                raise GatewayReject(REASON_METHOD_NOT_ALLOWED, 405, "/v1/models requires GET")
            else:
                raise GatewayReject(REASON_NOT_FOUND, 404, f"unknown path: {self.path}")
        except GatewayReject as reject:
            self._send_reject(reject)

    # ---- 聊天主流程：读体 → 方言解析 → 准入 → 调 llm → 方言封装 ----

    def _chat(self, dialect_mod):
        parsed = dialect_mod.parse_request(self._read_json_body())
        loaded = guard.admit(self.server.backend, parsed["model"])
        # model 缺失/空串时回填 served_id——「请求里的标识」不存在时的唯一诚实值
        model_out = parsed["model"] or loaded["served_id"]

        if parsed["stream"]:
            events = self.server.backend.chat_stream(parsed["chat_request"])
            if dialect_mod is openai_dialect:
                frames = openai_dialect.stream_chunks(
                    events, "chatcmpl-" + self.server.new_id(), int(self.server.now()), model_out)
            else:
                frames = anthropic_dialect.stream_events(
                    events, "msg_" + self.server.new_id(), model_out)
            self._stream(frames)
            return

        try:
            result = self.server.backend.chat_completion(parsed["chat_request"])
        except Exception as exc:  # noqa: BLE001 —— 下游失败原样上报，不伪造成功
            raise GatewayReject(REASON_UPSTREAM_ERROR, 500, f"chat backend failed: {exc}") from exc
        if dialect_mod is openai_dialect:
            payload = openai_dialect.completion_response(
                result, model_out, "chatcmpl-" + self.server.new_id(), int(self.server.now()))
        else:
            payload = anthropic_dialect.message_response(result, model_out, "msg_" + self.server.new_id())
        self._send_json(200, payload)
```

（`_chat` 的聊天用例在 T-07/T-08 用测试钉死；本任务的验收覆盖 models、404/405、超限体。）

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_openai.py -q`
**commit** `gateway: HTTP 服务器核心与 GET /v1/models`

---

## T-gateway-07 `POST /v1/chat/completions` 全路径 → **api:openaiChatCompletions**

**红**：在 `tests/test_gateway_openai.py` 追加：

```python
# tests/test_gateway_openai.py 追加（顶部补 import）
from gateway_fakes import MEDIA_DESK, MEDIA_REFUSAL

CHAT_BODY = {"model": "qwen3-30b", "messages": [{"role": "user", "content": "打个招呼"}]}


# ---- 非流式（R-gateway-02） ----

def test_http_chat_completion_full_shape():
    backend = FakeBackend()
    with serve(backend) as port:
        status, _, payload = json_request(port, "POST", "/v1/chat/completions", body=CHAT_BODY)
    assert status == 200
    assert payload == {
        "id": "chatcmpl-fixedfixedfixedfixedfixedfixed00",
        "object": "chat.completion",
        "created": FIXED_NOW,
        "model": "qwen3-30b",
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": "你好！",
                                 "reasoning_content": "用户在打招呼。"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
    }
    # 下游收到的 ChatRequest 形状
    assert ("chat_completion",
            {"messages": [{"role": "user", "content": "打个招呼"}],
             "max_tokens": 2048, "temperature": None, "top_p": None}) in backend.calls


def test_http_chat_completion_missing_model_echoes_served_id():
    with serve(FakeBackend()) as port:
        _, _, payload = json_request(port, "POST", "/v1/chat/completions",
                                     body={"messages": [{"role": "user", "content": "hi"}]})
    assert payload["model"] == "mlx-community/Qwen3-30B-A3B-8bit"


# ---- 流式（R-gateway-03） ----

def test_http_chat_stream_chunks_and_done():
    with serve(FakeBackend()) as port:
        status, headers, frames = sse_request(port, "/v1/chat/completions",
                                              {**CHAT_BODY, "stream": True})
    assert status == 200
    assert headers["content-type"].startswith("text/event-stream")
    decoded = _decode([f.encode("utf-8") for f in frames])
    assert decoded[-1] == "[DONE]"
    deltas = [c["choices"][0]["delta"] for c in decoded[:-1]]
    assert deltas[0] == {"role": "assistant"}
    assert {"reasoning_content": "用户在"} in deltas and {"content": "你"} in deltas
    assert decoded[-2]["choices"][0]["finish_reason"] == "stop"
    ids = {c["id"] for c in decoded[:-1]}
    assert ids == {"chatcmpl-fixedfixedfixedfixedfixedfixed00"}


def test_http_chat_stream_midway_error_no_done():
    backend = FakeBackend(events=[("content", "部分")], stream_error=RuntimeError("mlx-lm died"))
    with serve(backend) as port:
        status, _, frames = sse_request(port, "/v1/chat/completions", {**CHAT_BODY, "stream": True})
    assert status == 200                      # 头已发出，失败只能写进流里
    decoded = _decode([f.encode("utf-8") for f in frames])
    assert "[DONE]" not in decoded
    assert decoded[-1]["error"]["type"] == "api_error"
    assert "mlx-lm died" in decoded[-1]["error"]["message"]


# ---- 503（R-gateway-08）：绝不触发加载 ----

def test_http_503_media_busy():
    backend = FakeBackend(desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    with serve(backend) as port:
        status, headers, payload = json_request(port, "POST", "/v1/chat/completions", body=CHAT_BODY)
    assert status == 503
    assert headers["retry-after"] == "30"
    assert headers[REASON_HEADER.lower()] == "media_busy"
    assert payload["error"]["type"] == "service_unavailable_error"
    backend.assert_no_inference_calls()


def test_http_503_no_model():
    backend = FakeBackend(llm=IDLE_STATUS)
    with serve(backend) as port:
        status, headers, _ = json_request(port, "POST", "/v1/chat/completions", body=CHAT_BODY)
    assert status == 503
    assert headers[REASON_HEADER.lower()] == "no_model_loaded"
    backend.assert_no_inference_calls()


def test_http_503_model_mismatch_then_200_with_both_ids():
    backend = FakeBackend()
    with serve(backend) as port:
        status, headers, payload = json_request(
            port, "POST", "/v1/chat/completions", body={**CHAT_BODY, "model": "gpt-4o"})
        assert status == 503
        assert headers[REASON_HEADER.lower()] == "model_not_loaded"
        assert "qwen3-30b" in payload["error"]["message"]
        backend.assert_no_inference_calls()
        # 两个可接受标识各发一次都放行（R-gateway-10）
        s1, _, _ = json_request(port, "POST", "/v1/chat/completions",
                                body={**CHAT_BODY, "model": "qwen3-30b"})
        s2, _, _ = json_request(port, "POST", "/v1/chat/completions",
                                body={**CHAT_BODY, "model": "mlx-community/Qwen3-30B-A3B-8bit"})
    assert (s1, s2) == (200, 200)


# ---- 错误信封与选路（R-gateway-09） ----

def test_http_bad_json_400_openai_envelope():
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "POST", "/v1/chat/completions", body=b"{not json")
    assert status == 400
    assert payload["error"] == {"message": "request body is not valid JSON",
                                "type": "invalid_request_error", "code": "invalid_request"}


def test_http_stream_flag_routing():
    with serve(FakeBackend()) as port:
        # stream 缺省 → JSON
        _, h1, _ = json_request(port, "POST", "/v1/chat/completions", body=CHAT_BODY)
        # stream:"yes" → 400（不是半截 SSE）
        s2, h2, p2 = json_request(port, "POST", "/v1/chat/completions",
                                  body={**CHAT_BODY, "stream": "yes"})
    assert h1["content-type"].startswith("application/json")
    assert (s2, p2["error"]["code"]) == (400, "invalid_request")
    assert h2["content-type"].startswith("application/json")


def test_http_downstream_completion_error_500():
    backend = FakeBackend(completion_error=RuntimeError("connection refused"))
    with serve(backend) as port:
        status, headers, payload = json_request(port, "POST", "/v1/chat/completions", body=CHAT_BODY)
    assert status == 500
    assert headers[REASON_HEADER.lower()] == "upstream_error"
    assert payload["error"]["type"] == "api_error"
    assert "connection refused" in payload["error"]["message"]
```

**绿**：实现已在 T-06 的 `_chat` 就位；本任务跑测试、修偏差（典型：头大小写、`Retry-After` 只挂 503、`model` 回填）。若全绿则本任务是纯验证 + 修正提交。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_openai.py -q`
**commit** `gateway: POST /v1/chat/completions 非流式/流式/503/错误信封全路径`

---

## T-gateway-08 `POST /v1/messages` 全路径 → **api:anthropicMessages**

**红**：在 `tests/test_gateway_anthropic.py` 追加：

```python
# tests/test_gateway_anthropic.py 追加（顶部补 import）
from desk.gateway.errors import REASON_HEADER
from gateway_client import json_request, serve, sse_request
from gateway_fakes import IDLE_STATUS, MEDIA_DESK, MEDIA_REFUSAL, FakeBackend

MSG_BODY = {"model": "qwen3-30b", "max_tokens": 100,
            "messages": [{"role": "user", "content": "打个招呼"}]}


def test_http_messages_full_shape():
    backend = FakeBackend()
    with serve(backend) as port:
        status, _, payload = json_request(port, "POST", "/v1/messages", body=MSG_BODY)
    assert status == 200
    assert payload == {
        "id": "msg_fixedfixedfixedfixedfixedfixed00",
        "type": "message",
        "role": "assistant",
        "model": "qwen3-30b",
        "content": [{"type": "thinking", "thinking": "用户在打招呼。"},
                    {"type": "text", "text": "你好！"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 12, "output_tokens": 7},
    }
    assert ("chat_completion",
            {"messages": [{"role": "user", "content": "打个招呼"}],
             "max_tokens": 100, "temperature": None, "top_p": None}) in backend.calls


def test_http_messages_missing_model_echoes_served_id():
    body = {"max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]}
    with serve(FakeBackend()) as port:
        _, _, payload = json_request(port, "POST", "/v1/messages", body=body)
    assert payload["model"] == "mlx-community/Qwen3-30B-A3B-8bit"


def test_http_messages_system_reaches_backend():
    backend = FakeBackend()
    with serve(backend) as port:
        json_request(port, "POST", "/v1/messages",
                     body={**MSG_BODY, "system": [{"type": "text", "text": "你是台面助手"}]})
    sent = [c for c in backend.calls if c[0] == "chat_completion"][0][1]
    assert sent["messages"][0] == {"role": "system", "content": "你是台面助手"}


def test_http_messages_stream_event_sequence_over_wire():
    with serve(FakeBackend()) as port:
        status, headers, frames = sse_request(port, "/v1/messages", {**MSG_BODY, "stream": True})
    assert status == 200
    assert headers["content-type"].startswith("text/event-stream")
    decoded = _decode_frames([f.encode("utf-8") for f in frames])
    assert [n for n, _ in decoded] == [
        "message_start",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "message_delta", "message_stop",
    ]
    assert decoded[0][1]["message"]["id"] == "msg_fixedfixedfixedfixedfixedfixed00"
    assert decoded[9][1]["usage"] == {"input_tokens": 12, "output_tokens": 7}


def test_http_messages_stream_midway_error_no_message_stop():
    backend = FakeBackend(events=[("content", "部分")], stream_error=RuntimeError("mlx-lm died"))
    with serve(backend) as port:
        _, _, frames = sse_request(port, "/v1/messages", {**MSG_BODY, "stream": True})
    decoded = _decode_frames([f.encode("utf-8") for f in frames])
    names = [n for n, _ in decoded]
    assert "message_stop" not in names
    assert names[-1] == "error"


def test_http_messages_503_media_busy_anthropic_envelope():
    backend = FakeBackend(desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    with serve(backend) as port:
        status, headers, payload = json_request(port, "POST", "/v1/messages", body=MSG_BODY)
    assert status == 503
    assert headers["retry-after"] == "30"
    assert headers[REASON_HEADER.lower()] == "media_busy"
    assert payload["type"] == "error"
    assert payload["error"]["type"] == "overloaded_error"
    backend.assert_no_inference_calls()


def test_http_messages_503_no_model():
    backend = FakeBackend(llm=IDLE_STATUS)
    with serve(backend) as port:
        status, headers, payload = json_request(port, "POST", "/v1/messages", body=MSG_BODY)
    assert (status, headers[REASON_HEADER.lower()]) == (503, "no_model_loaded")
    assert payload["error"]["type"] == "overloaded_error"
    backend.assert_no_inference_calls()


def test_http_messages_missing_max_tokens_400_anthropic_envelope():
    body = {"messages": [{"role": "user", "content": "hi"}]}
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "POST", "/v1/messages", body=body)
    assert status == 400
    assert payload["type"] == "error"
    assert payload["error"]["type"] == "invalid_request_error"
    assert "max_tokens" in payload["error"]["message"]


def test_http_messages_stream_flag_routing():
    with serve(FakeBackend()) as port:
        s, h, p = json_request(port, "POST", "/v1/messages", body={**MSG_BODY, "stream": "yes"})
    assert (s, p["error"]["type"]) == (400, "invalid_request_error")
    assert h["content-type"].startswith("application/json")   # 400 永远是 JSON，不是半截 SSE
```

**绿**：路由与 `_chat` 已在 T-06 就位；本任务跑测试、修偏差（典型：Anthropic 信封选路、`msg_` 前缀、事件序列）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_anthropic.py -q`
**commit** `gateway: POST /v1/messages 非流式/流式/503/错误信封全路径`

---

## T-gateway-09 GatewayService 生命周期 + LAN 自证（`service.py`）→ **data:gatewayStatus**

**红**：写 `tests/test_gateway_service.py`：

```python
# tests/test_gateway_service.py
"""GatewayService：生命周期、data:gatewayStatus、0.0.0.0 局域网可达（R-gateway-07）。"""
import socket
import subprocess

import pytest

from desk.gateway.service import GatewayService
from gateway_client import json_request
from gateway_fakes import FakeBackend


def _config(enabled=True, host="127.0.0.1", port=0):
    holder = {"gateway": {"enabled": enabled, "host": host, "port": port}}
    return holder, (lambda: holder)


def _connect_refused(host, port):
    with socket.socket() as s:
        s.settimeout(2)
        return s.connect_ex((host, port)) != 0


@pytest.fixture
def service_factory():
    services = []

    def make(read_config, backend=None):
        svc = GatewayService(backend or FakeBackend(), read_config)
        services.append(svc)
        return svc

    yield make
    for svc in services:
        svc.stop()


def test_disabled_does_not_listen(service_factory):
    _, read = _config(enabled=False, port=18999)
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["enabled"] is False
    assert st["listening"] is False
    assert st["last_error"] is None
    assert _connect_refused("127.0.0.1", 18999)


def test_start_serves_models_and_reports_real_port(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["listening"] is True
    assert st["port"] > 0                      # 端口 0 → 报实际绑定端口
    status, _, payload = json_request(st["port"], "GET", "/v1/models")
    assert status == 200
    assert payload["object"] == "list"


def test_status_shape(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    port = st["port"]
    assert st == {
        "enabled": True,
        "listening": True,
        "host": "127.0.0.1",
        "port": port,
        "openai_base_url": f"http://127.0.0.1:{port}/v1",
        "anthropic_base_url": f"http://127.0.0.1:{port}",
        "auth": "none",                        # 给 settings 面板「当前无鉴权」标注
        "last_error": None,
    }


def test_bind_failure_recorded_not_fatal(service_factory):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    try:
        _, read = _config(port=occupied)
        svc = service_factory(read)
        svc.start_from_config()               # 不抛：绑定失败记入 status，进程继续活
        st = svc.status()
        assert st["enabled"] is True
        assert st["listening"] is False
        assert st["last_error"] is not None
        assert str(occupied) in st["last_error"]
    finally:
        blocker.close()


def test_stop_closes_listener(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    svc.stop()
    assert svc.status()["listening"] is False
    assert _connect_refused("127.0.0.1", port)


def _lan_ip():
    try:
        proc = subprocess.run(["ipconfig", "getifaddr", "en0"],
                              capture_output=True, text=True, timeout=5)
    except OSError:
        return None
    ip = proc.stdout.strip()
    return ip if proc.returncode == 0 and ip else None


def _spec_port_or_ephemeral():
    """优先按 spec 用 8770；被占则退回临时端口（非回环路径的证明力不变）。"""
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", 8770))
        except OSError:
            return 0
    return 8770


def test_lan_reachability_via_en0_ip(service_factory):
    """决策 D-0002：绑 0.0.0.0 后用本机 LAN IP 自连——不走回环，足证非本地监听生效。"""
    ip = _lan_ip()
    if not ip:
        pytest.skip("'ipconfig getifaddr en0' 未返回局域网 IP：本机无法自证非回环可达，"
                    "跳过（不得静默通过）")
    _, read = _config(host="0.0.0.0", port=_spec_port_or_ephemeral())
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["listening"] is True
    status, _, payload = json_request(st["port"], "GET", "/v1/models", host=ip)
    assert status == 200
    assert payload["object"] == "list"
```

**绿**：

```python
# desk/gateway/service.py
"""GatewayService：生命周期、配置应用、data:gatewayStatus 的唯一产地。

gateway 不写配置（消费清单里没有 api:writeConfig）：UI 改动流程是
foundation api:writeConfig → gateway api:gatewayConfig 应用（重读并换绑）。
"""
from __future__ import annotations

import threading

from .http_server import GatewayHTTPServer

_DEFAULTS = {"enabled": True, "host": "0.0.0.0", "port": 8770}


class GatewayService:
    def __init__(self, backend, read_config, *, server_factory=GatewayHTTPServer):
        self._backend = backend
        self._read_config = read_config      # foundation api:readConfig（注入，不 import）
        self._server_factory = server_factory
        self._server = None
        self._thread = None
        self._applied = None                 # 正在生效的 (enabled, host, port)
        self._bound_port = None
        self._last_error = None

    # ---- 配置读取（data:deskConfig 的 gateway 段；缺键补默认） ----

    def _gateway_config(self) -> dict:
        cfg = dict(_DEFAULTS)
        cfg.update((self._read_config() or {}).get("gateway") or {})
        return cfg

    # ---- 生命周期 ----

    def start_from_config(self) -> None:
        """enabled 才监听；绑定失败不抛，记入 status（desk 服务整体不退）。不自动重试。"""
        cfg = self._gateway_config()
        self._applied = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        self._last_error = None
        if not cfg["enabled"]:
            return
        try:
            self._server = self._server_factory((cfg["host"], cfg["port"]), self._backend)
        except OSError as exc:
            self._server = None
            detail = exc.strerror or str(exc)
            self._last_error = f"bind {cfg['host']}:{cfg['port']} failed: [errno {exc.errno}] {detail}"
            return
        self._bound_port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="gateway-http", daemon=True)
        self._thread.start()

    def apply_config(self) -> dict:
        """重读配置；(enabled,host,port) 或监听实况有变则 stop 旧 → start 新。返回 status。"""
        cfg = self._gateway_config()
        wanted = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        listening = self._server is not None
        if wanted == self._applied and listening == wanted[0]:
            return self.status()
        self.stop()
        self.start_from_config()
        return self.status()

    def stop(self) -> None:
        """关闭监听 socket；在跑的流被断开——错误即错误，不温柔收尾。"""
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        self._bound_port = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=10)

    # ---- data:gatewayStatus ----

    def status(self) -> dict:
        """listening 是实测值（socket 已 bind 成功），不是 enabled 的回声。"""
        if self._server is not None:
            enabled, host, _ = self._applied
            listening, port = True, self._bound_port
        else:
            cfg = self._gateway_config()
            enabled, host, port = bool(cfg["enabled"]), cfg["host"], cfg["port"]
            listening = False
        return {
            "enabled": enabled,
            "listening": listening,
            "host": host,
            "port": port,
            "openai_base_url": f"http://{host}:{port}/v1",
            "anthropic_base_url": f"http://{host}:{port}",
            "auth": "none",              # 常量：给 settings 面板「当前无鉴权」标注
            "last_error": self._last_error,
        }
```

并把 `desk/gateway/__init__.py` 更新为完整公开入口：

```python
# desk/gateway/__init__.py（T-09 终态）
"""gateway：OpenAI + Anthropic 兼容对外推理接口（纯翻译层，不加载、不排队）。"""
from .backend import GatewayBackend  # noqa: F401
from .errors import (  # noqa: F401
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_MEDIA_JOB_RUNNING,
    REASON_METHOD_NOT_ALLOWED,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    REASON_NOT_FOUND,
    REASON_UPSTREAM_ERROR,
    RETRY_AFTER_SECONDS,
    GatewayReject,
)
from .service import GatewayService  # noqa: F401
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_service.py -q`
**commit** `gateway: GatewayService 生命周期、gatewayStatus 与 LAN 自证`

---

## T-gateway-10 `api:gatewayConfig`：`handle_config_request` 与换绑

**红**：在 `tests/test_gateway_service.py` 追加：

```python
# tests/test_gateway_service.py 追加

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_config_request_get_returns_config_and_status(service_factory):
    holder, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    code, payload = svc.handle_config_request("GET")
    assert code == 200
    assert payload["config"] == holder["gateway"]
    assert payload["status"]["listening"] is True


def test_config_request_post_rebinds_to_new_port(service_factory):
    p1, p2 = _free_port(), _free_port()
    holder, read = _config(port=p1)
    svc = service_factory(read)
    svc.start_from_config()
    assert svc.status()["port"] == p1
    holder["gateway"] = {"enabled": True, "host": "127.0.0.1", "port": p2}   # UI 已走 api:writeConfig
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"] == svc.status()
    assert svc.status()["port"] == p2
    status, _, _ = json_request(p2, "GET", "/v1/models")                     # 新端口通
    assert status == 200
    assert _connect_refused("127.0.0.1", p1)                                 # 旧端口拒


def test_config_request_post_disable_stops_listening(service_factory):
    holder, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    holder["gateway"] = {"enabled": False, "host": "127.0.0.1", "port": port}
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is False
    assert _connect_refused("127.0.0.1", port)


def test_config_request_post_same_config_is_noop(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is True         # 配置未变：监听不动
    status, _, _ = json_request(port, "GET", "/v1/models")
    assert status == 200


def test_config_request_post_retries_failed_bind(service_factory):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    holder, read = _config(port=occupied)
    svc = service_factory(read)
    svc.start_from_config()
    assert svc.status()["listening"] is False
    blocker.close()                                       # 用户腾出端口后重新应用
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is True
    assert payload["status"]["last_error"] is None


def test_config_request_rejects_other_methods(service_factory):
    _, read = _config()
    svc = service_factory(read)
    code, payload = svc.handle_config_request("DELETE")
    assert code == 405
    assert payload["error"]["code"] == "method_not_allowed"
```

**绿**：在 `desk/gateway/service.py` 的 `GatewayService` 追加：

```python
    # ---- api:gatewayConfig 的 HTTP 面 ----
    # WSGI 风格小处理函数；由 8766 台面服务的路由所有者挂到 /api/gateway/config。
    # GET 返回 {config, status}；POST 触发 apply_config 并返回新 status。
    # gateway 不写配置：改动流程是 foundation api:writeConfig → 这里重读并换绑。

    def handle_config_request(self, method: str, body=None):
        if method == "GET":
            return 200, {"config": self._gateway_config(), "status": self.status()}
        if method == "POST":
            return 200, {"config": self._gateway_config(), "status": self.apply_config()}
        return 405, {"error": {"message": "GET or POST only",
                               "type": "invalid_request_error",
                               "code": "method_not_allowed"}}
```

注意 `apply_config` 的判断：`wanted == self._applied and listening == wanted[0]` —— 配置没变
且监听实况与期望一致时不动；绑定曾失败（enabled 但 listening False）时同配置重发 POST 会**重试绑定**
（`test_config_request_post_retries_failed_bind` 钉死此行为）。

**验收（模块全绿收口）**
`cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_gateway_errors.py tests/test_gateway_openai.py tests/test_gateway_anthropic.py tests/test_gateway_guard.py tests/test_gateway_service.py -q`
**commit** `gateway: api:gatewayConfig 处理函数与配置换绑`

---

## 附录 A：人工验证 runbook（非任务、非 reality gate——spec 明示本模块无 reality gate）

自动验收已覆盖协议形状与非回环可达（LAN IP 自连，D-0002）。以下为交付后可选的人工复核，
依赖真实模型驻留（llm 模块领域），故不进入本模块任务 DAG：

1. 在台面 UI 加载任一聊天模型，确认状态条显示 loaded。
2. 另一台同网设备执行 `curl http://<本机IP>:8770/v1/models`——预期 200，data 列出两个标识。
3. OpenAI SDK：`OpenAI(base_url="http://<本机IP>:8770/v1", api_key="none").chat.completions.create(model="<key>", messages=[{"role":"user","content":"你好"}])`——预期返回 content 非空、usage 有数。
4. Anthropic SDK：`Anthropic(base_url="http://<本机IP>:8770", api_key="none").messages.create(model="<key>", max_tokens=100, messages=[{"role":"user","content":"你好"}])`——预期 `type:"message"`、content 有 text 块。
5. 在台面发起一个视频作业，期间重复第 3 步——预期 503 + `Retry-After: 30` + `X-LocalModelDesk-Reason`，且视频作业不受影响。

## 附录 B：本计划内部决定（不越 design 的 Assumptions 边界）

1. **system 块数组中的非 text 块 → 400**（design 只写了「取全部 text 块拼接」）：与 messages 内容块
   的处理同一条诚实规则——不静默丢弃；合法客户端的 system 数组本就只有 text 块，行为无差。
2. **LAN 用例端口**：优先按 spec 绑 `0.0.0.0:8770`；8770 恰被占（例如真 App 正在跑）时退回临时端口。
   证明目标是「经 LAN IP 的非回环路径可达」，与端口数值无关；测试不因环境巧合误报红。
3. **所有错误响应都带 `X-LocalModelDesk-Reason` 头**（design 只要求 503 带）：503 额外带
   `Retry-After`；统一带原因码头无副作用，且让 Anthropic 信封（体内无 code 位）的 4xx 也机器可读。
4. **流缺 finish 事件的防御尾**：按 llm 合同这不该发生；发生即按上游故障写方言错误（无 `[DONE]` /
   无 `message_stop`），与「不数 token、不伪造用量」一致。
5. **`handle_config_request` 的 POST 也回 `config`**：design 说「返回新 status」，附带当前 config
   便于 UI 单次刷新，不改变语义。

## 附录 C：需求覆盖矩阵

| 需求 | 任务 |
|---|---|
| R-gateway-01 | T-02（models_list）、T-06（HTTP） |
| R-gateway-02 | T-02（completion_response）、T-07 |
| R-gateway-03 | T-02（stream_chunks）、T-07 |
| R-gateway-04 | T-03、T-08 |
| R-gateway-05 | T-04、T-08 |
| R-gateway-06 | T-03（system 两形态/多轮/映射）、T-04（usage/stop_reason 流式） |
| R-gateway-07 | T-09（0.0.0.0 + LAN 自证、开关不监听） |
| R-gateway-08 | T-05（guard）、T-07/T-08（503 + 头 + 无加载调用记录） |
| R-gateway-09 | T-01（信封）、T-07/T-08（HTTP 错误路径、流中失败） |
| R-gateway-10 | T-02（两标识列出）、T-05（匹配）、T-07（key/served_id 各放行一次） |
