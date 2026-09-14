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
