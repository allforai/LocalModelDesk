"""Shared Playwright fixtures and invariant guards for browser E2E tests."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError as exc:
    raise RuntimeError(
        "e2e requires playwright==1.62.0; install tests/e2e/requirements.txt"
    ) from exc

expect.set_options(timeout=10_000)
REPO = Path(__file__).resolve().parents[2]
FORBIDDEN_ROOTS = tuple(REPO / name for name in (
    "llms", "minimax-h3", "minimax-music3", "image-models", "outputs"))
_open_violations: list[str] = []


def _audit(event: str, args) -> None:
    if event != "open" or not args:
        return
    target = args[0]
    if not isinstance(target, (str, bytes, os.PathLike)):
        return
    try:
        path = os.fsdecode(os.fspath(target))
    except TypeError:
        return
    if any(path == str(root) or path.startswith(str(root) + os.sep)
           for root in FORBIDDEN_ROOTS):
        _open_violations.append(path)


sys.addaudithook(_audit)


@pytest.fixture(autouse=True)
def audit_violations():
    _open_violations.clear()
    yield _open_violations
    assert not _open_violations, f"touched forbidden data dirs: {_open_violations}"


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        cdp_url = os.environ.get("MEGASTORM_CDP_URL")
        instance = (playwright.chromium.connect_over_cdp(cdp_url)
                    # Headless Chromium hides scrollbars; the app's WKWebView shows them whenever a
                    # mouse is attached, so render them here or their look is never tested (2026-09-16).
                    if cdp_url else playwright.chromium.launch(ignore_default_args=["--hide-scrollbars"]))
        yield instance
        if not cdp_url:
            instance.close()


@pytest.fixture
def context(browser):
    instance = browser.new_context()
    requests: list[str] = []
    instance.on("request", lambda request: requests.append(request.url))
    yield instance
    instance.close()
    direct = [url for url in requests if ":8767" in url]
    assert not direct, f"browser talked to :8767 directly: {direct}"


@pytest.fixture
def page(context, request, tmp_path):
    instance = context.new_page()
    errors: list[str] = []
    instance.on("pageerror", lambda error: errors.append(str(error)))
    yield instance
    if getattr(request.node, "rep_failed", False):
        artifacts = tmp_path / "e2e-artifacts"
        artifacts.mkdir(exist_ok=True)
        try:
            (artifacts / "page.html").write_text(instance.content(), encoding="utf-8")
        except Exception:
            pass
        (artifacts / "pageerrors.txt").write_text("\n".join(errors), encoding="utf-8")
    assert not errors, f"uncaught page errors: {errors}"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.rep_failed = report.failed


@pytest.fixture
def wait_until():
    def wait(predicate, timeout: float = 10.0, interval: float = 0.1):
        deadline, last = time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            last = predicate()
            if last:
                return last
            time.sleep(interval)
        raise AssertionError(f"condition not met within {timeout}s (last={last!r})")
    return wait
