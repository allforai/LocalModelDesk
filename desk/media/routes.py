"""HTTP adapter from MediaService to the media route table."""
from __future__ import annotations

from typing import Callable

from .service import MediaError, MediaService


Handler = Callable[[dict | None, dict], tuple[int, dict]]


def _envelope(exc: MediaError) -> dict:
    return {"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}}


def _run(fn: Callable[[], dict]) -> tuple[int, dict]:
    try:
        return 200, fn()
    except MediaError as exc:
        return exc.http_status, _envelope(exc)


def _int_param(query: dict, name: str, default: int | None) -> int | None:
    raw = query.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise MediaError("invalid_params", f"{name} must be an integer", 400)


def build_routes(service: MediaService) -> list[tuple[str, str, Handler]]:
    def start_video(body, _query):
        payload = body or {}
        return _run(lambda: service.start_video_job(
            prompt=payload.get("prompt"), width=payload.get("width"),
            height=payload.get("height"), frames=payload.get("frames"),
            steps=payload.get("steps"), mode=payload.get("mode", "text"),
            first_frame=payload.get("first_frame"), last_frame=payload.get("last_frame"),
            ref_video=payload.get("ref_video"), use_audio=payload.get("use_audio", True),
            force=bool(payload.get("force", False))))

    def start_music(body, _query):
        payload = body or {}
        return _run(lambda: service.start_music_job(
            caption=payload.get("caption"), lyrics=payload.get("lyrics"),
            duration=payload.get("duration"), force=bool(payload.get("force", False))))

    def cancel(_body, _query):
        return _run(service.cancel_job)

    def start_image(body, _query):
        payload = body or {}
        return _run(lambda: service.start_image_job(
            prompt=payload.get("prompt"), width=payload.get("width", 1024),
            height=payload.get("height", 1024), steps=payload.get("steps", 40),
            seed=payload.get("seed", 42), force=payload.get("force", False)))

    def status(_body, query):
        def call():
            return service.job_status(
                log_from=_int_param(query, "log_from", 0) or 0,
                job_id=_int_param(query, "job_id", None))
        return _run(call)

    return [
        ("POST", "/api/media/inputs", lambda body, _query: _run(lambda: service.upload_input(
            name=(body or {}).get("name"), data=(body or {}).get("data")))),
        ("POST", "/api/media/video", start_video),
        ("POST", "/api/media/music", start_music),
        ("POST", "/api/media/image", start_image),
        ("POST", "/api/media/cancel", cancel),
        ("GET", "/api/media/job", status),
    ]
