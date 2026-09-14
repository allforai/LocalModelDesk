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
