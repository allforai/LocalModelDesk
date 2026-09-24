"""Image sessions in a real browser (design docs/superpowers/specs/2026-09-24-image-sessions-design.md).

Runs against launch_test_harness: real DeskApp / LibraryService / ImageSessionStore / MediaService,
with the scripted media executor writing a small PNG instead of running Qwen-Image. Every visual
state is checked at 1280×800 and 900×700 for: no 「种子」 in the main flow, no blank or broken
images, no horizontal scroll, no clipped buttons and no overlapping regions. When
LMD_IMAGE_SESSIONS_SHOTS names a directory, each checked state is also saved there as
<state>-<viewport>.png plus a .json with the DOM check results (self-check evidence).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from playwright.sync_api import expect

from desk.resources.catalog import list_catalog
from desk.testing import launch_test_harness
from desk.testing.seed import default_states
from desk.testing.scripts import (
    Exit, Line, MediaScript, cancellable_media_steps, default_media_steps, fast_media_steps,
)

SEED = "种子"
VIEWPORTS = {"wide": (1280, 800), "narrow": (900, 700)}
LONG_PROMPT = "一只橘猫坐在窗边，午后阳光，细腻的水彩插画，暖色调，柔和的光影"

DOM_CHECKS = r"""
() => {
  const pane = document.querySelector('#pane-image');
  const visible = (el) => !!el && el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
  const folded = (el) => !!el.closest('details.image-advanced, details.attempt-advanced');
  const texts = [];
  const walker = document.createTreeWalker(pane, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const host = node.parentElement;
    if (!host || folded(host) || !visible(host)) continue;
    if (host.closest('details:not([open])') && !host.closest('summary')) continue;
    texts.push(node.textContent);
  }
  for (const el of pane.querySelectorAll('[title],[aria-label],[placeholder]')) {
    if (folded(el) || !visible(el)) continue;
    texts.push(el.getAttribute('title') || '', el.getAttribute('aria-label') || '', el.getAttribute('placeholder') || '');
  }
  for (const el of document.querySelectorAll('.overlay .dialog')) texts.push(el.innerText);
  const images = [...pane.querySelectorAll('img')].filter(visible);
  const blank = images.filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.getAttribute('src'));
  const clipped = [...document.querySelectorAll('#pane-image button, .overlay button')].filter(visible)
    .filter((b) => b.scrollWidth > b.clientWidth + 1).map((b) => b.innerText || b.getAttribute('aria-label'));
  const titles = [...pane.querySelectorAll('.session-title')].filter(visible)
    .filter((t) => t.scrollWidth > t.clientWidth + 1 && getComputedStyle(t).textOverflow !== 'ellipsis').map((t) => t.innerText);
  const rect = (sel) => { const el = pane.querySelector(sel); return el && visible(el) ? el.getBoundingClientRect() : null; };
  const overlap = (a, b) => a && b && a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
  const aside = rect('aside.sessions'), timeline = rect('.image-timeline'), composer = rect('.image-composer'), head = rect('.image-head');
  const overlaps = [];
  if (overlap(aside, timeline)) overlaps.push('sessions/timeline');
  if (overlap(aside, composer)) overlaps.push('sessions/composer');
  if (overlap(timeline, composer)) overlaps.push('timeline/composer');
  if (overlap(head, timeline)) overlaps.push('head/timeline');
  const outside = [...pane.querySelectorAll('button, textarea, .attempt, .session')].filter(visible)
    .filter((el) => { const r = el.getBoundingClientRect(); return r.right > window.innerWidth + 1; }).length;
  const scroller = document.scrollingElement;
  return {
    seed_word_in_main_flow: texts.some((t) => t.includes('种子')),
    seed_texts: texts.filter((t) => t.includes('种子')),
    blank_images: blank.length, blank_srcs: blank,
    horizontal_scroll: scroller.scrollWidth > scroller.clientWidth,
    clipped_buttons: clipped, clipped_titles: titles, overlaps, outside_viewport: outside,
    foreign_panes: !!document.querySelector('#pane-video:not([hidden]), #pane-music:not([hidden])'),
  };
}
"""


def _check_state(page, state: str, *, harness=None, viewports=("wide", "narrow")) -> None:
    """Run the visual-QA DOM assertions for one state at each viewport (and save evidence if asked)."""
    shots = os.environ.get("LMD_IMAGE_SESSIONS_SHOTS")
    original = page.viewport_size
    for name in viewports:
        width, height = VIEWPORTS[name]
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_function(
            "() => [...document.querySelectorAll('#pane-image img')].every((i) => i.complete)")
        checks = page.evaluate(DOM_CHECKS)
        if shots:
            folder = Path(shots)
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / f"{state}-{name}.png"))
            sessions = page.evaluate(
                "() => [...document.querySelectorAll('[data-image-session-list] [data-session-id]')]"
                ".map((li) => li.dataset.sessionId)")
            (folder / f"{state}-{name}.json").write_text(json.dumps({
                "state_id": state, "viewport": {"name": name, "width": width, "height": height},
                "url": page.url, "session_ids": sessions, "dom_checks": checks,
                "served_by": {"host": harness.base_url if harness else None,
                              "process": "desk.testing.launch_test_harness",
                              "mock_layers": ["FakeMediaExecutor (desk/testing/scripts.py MediaScript)",
                                              "FakeLlmBackend", "FakeMemoryReader", "FixedClock"]},
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        assert not checks["seed_word_in_main_flow"], (state, name, checks["seed_texts"])
        assert checks["blank_images"] == 0, (state, name, checks["blank_srcs"])
        assert not checks["horizontal_scroll"], (state, name)
        assert checks["clipped_buttons"] == [], (state, name, checks["clipped_buttons"])
        assert checks["clipped_titles"] == [], (state, name, checks["clipped_titles"])
        assert checks["overlaps"] == [], (state, name, checks["overlaps"])
        assert checks["outside_viewport"] == 0, (state, name)
        assert not checks["foreign_panes"], (state, name)
    if original:
        page.set_viewport_size(original)


def _harness(tmp_path, jobs, *, with_other_media=False):
    states = {**default_states(list_catalog()), "qwen-image": "present"} if with_other_media else {"qwen-image": "present"}
    return launch_test_harness(tmp_path, model_states=states, image_runtime=True, media_script=MediaScript(jobs))


def _open(page, harness):
    page.goto(harness.base_url + "#tab=image")
    pane = page.locator("#pane-image")
    expect(pane).to_be_visible()
    expect(pane.locator("[data-image-session-list] li[aria-current='true']")).to_have_count(1)
    return pane


def _cards(pane):
    return pane.locator("[data-image-timeline] .attempt")


def _generate(pane, prompt=None):
    if prompt is not None:
        pane.locator("[data-image-prompt]").fill(prompt)
    start = pane.locator("[data-image-start]")
    expect(start).to_be_enabled()
    start.click()


def _wait_status(pane, count, status):
    expect(_cards(pane)).to_have_count(count)
    expect(_cards(pane).nth(count - 1)).to_have_attribute("data-attempt-status", status, timeout=15_000)


def _current_id(pane):
    return pane.locator("[data-image-session-list] li[aria-current='true']").get_attribute("data-session-id")


def _session(page, harness, session_id):
    response = page.request.get(f"{harness.base_url}/api/image-sessions/{session_id}")
    assert response.status == 200, response.status
    return response.json()


def _outside_timeline(page, selector, settle_ms=2_000):
    """Texts of timeline elements matching selector that are not wholly inside the timeline viewport,
    once the pane has settled after a resize (it re-fits and re-pins on its ResizeObserver)."""
    deadline = time.monotonic() + settle_ms / 1000
    while True:
        outside = _outside_timeline_now(page, selector)
        if not outside or time.monotonic() > deadline:
            return outside
        page.wait_for_timeout(100)


def _outside_timeline_now(page, selector):
    return page.evaluate("""(selector) => {
      const timeline = document.querySelector('#pane-image .image-timeline');
      const box = timeline.getBoundingClientRect();
      const nodes = [...timeline.querySelectorAll(selector)];
      if (!nodes.length) return ['<nothing matched ' + selector + '>'];
      return nodes.filter((n) => { const r = n.getBoundingClientRect(); return r.top < box.top - 1 || r.bottom > box.bottom + 1; })
        .map((n) => (n.innerText || n.alt || n.className).slice(0, 40));
    }""", selector)


def test_first_entry_creates_one_session_and_keeps_advanced_folded(page, tmp_path):
    # model-missing's stated precondition: the MLX runtime is present and only the model is absent,
    # so the reason shown is the model's, not the runtime's (§7.6 puts the runtime first).
    with launch_test_harness(tmp_path, image_runtime=True) as harness:
        pane = _open(page, harness)
        items = pane.locator("[data-image-session-list] [data-session-id]")
        expect(items).to_have_count(1)
        expect(items.first).to_contain_text("新会话")
        expect(pane.locator("[data-image-empty]")).to_contain_text("还没有图片")
        expect(pane.locator("[data-image-empty]")).to_contain_text("在下面写下想要的画面，点「生成图片」")
        expect(pane.locator("progress")).to_have_count(0)
        advanced = pane.locator("details[data-image-advanced]")
        expect(advanced).not_to_have_attribute("open", "")
        for name, value in {"width": "1024", "height": "1024", "steps": "40", "seed": ""}.items():
            expect(pane.locator(f"[data-image-{name}]")).to_have_value(value)
        expect(pane.locator("[data-image-seed]")).to_have_attribute("placeholder", "留空则每次随机")
        # No image model: generation is disabled and the reason names the model.
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-model]")).to_contain_text("尚未安装")
        expect(pane.locator("[data-image-hint-text]")).to_have_text("尚未安装图片模型，请到「资源」页下载")
        pane.get_by_label("图片提示词", exact=True).fill("一只橘猫")
        expect(pane.locator("[data-image-prompt]")).to_have_value("一只橘猫")
        _check_state(page, "model-missing", harness=harness)
        page.reload()
        expect(pane.locator("[data-image-session-list] [data-session-id]")).to_have_count(1)


def test_first_entry_with_model_ready(page, tmp_path):
    with _harness(tmp_path, []) as harness:
        pane = _open(page, harness)
        expect(pane.locator("[data-image-start]")).to_be_enabled()
        expect(pane.locator("[data-image-model]")).to_have_text("模型文件完整 · 可离线生成")
        expect(pane.locator("[data-image-hint]")).to_be_hidden()
        _check_state(page, "first-entry-auto-session", harness=harness)


def test_three_rounds_refine_keep_order_seed_and_recompose(page, tmp_path):
    """AC-1 / AC-2: three rounds of generate → 在这张基础上改 → generate, then 换个构图."""
    with _harness(tmp_path, [fast_media_steps() for _ in range(4)]) as harness:
        pane = _open(page, harness)
        session_id = _current_id(pane)
        prompts = [LONG_PROMPT, LONG_PROMPT + "，黄昏", LONG_PROMPT + "，黄昏，雨后"]

        _generate(pane, prompts[0])
        _wait_status(pane, 1, "done")
        expect(pane.locator("[data-image-hint-text]")).not_to_contain_text("正在生成", timeout=1500)
        # D-65: prompt stays for the next tweak, the seed box is cleared.
        expect(pane.locator("[data-image-prompt]")).to_have_value(prompts[0])
        expect(pane.locator("[data-image-seed]")).to_have_value("")
        title = pane.locator("[data-image-session-list] li[aria-current='true'] .session-title")
        expect(title).to_have_text(LONG_PROMPT[:24] + "…")

        for round_index in (1, 2):
            source = _cards(pane).nth(round_index - 1)
            source.click()
            expect(source).to_have_attribute("aria-expanded", "true")
            source.get_by_role("button", name="在这张基础上改").click()
            expect(pane.locator("[data-image-refine]")).to_be_visible()
            expect(pane.locator("[data-image-refine-text]")).to_have_text(f"沿用第 {round_index} 次的构图")
            expect(pane.locator("[data-image-prompt]")).to_be_focused()
            expect(pane.locator("details[data-image-advanced]")).not_to_have_attribute("open", "")
            expect(_cards(pane)).to_have_count(round_index)  # nothing submitted yet (D-40)
            if round_index == 2:
                _check_state(page, "refine-prefill", harness=harness)
            _generate(pane, prompts[round_index])
            _wait_status(pane, round_index + 1, "done")
            expect(pane.locator("[data-image-refine]")).to_be_hidden()

        session = _session(page, harness, session_id)
        attempts = session["attempts"]
        assert [a["params"]["prompt"] for a in attempts] == prompts
        assert [a["status"] for a in attempts] == ["done"] * 3
        assert attempts[1]["params"]["seed"] == attempts[0]["params"]["seed"]
        assert attempts[2]["params"]["seed"] == attempts[1]["params"]["seed"]
        assert len({a["output"] for a in attempts}) == 3

        labels = _cards(pane).locator(".attempt-label")
        for index in range(3):
            expect(labels.nth(index)).to_contain_text(f"第 {index + 1} 次")
            expect(_cards(pane).nth(index).locator(".attempt-spec")).to_have_text("1024×1024 · 40 步")
            if index < 2:  # collapsed cards show the thumbnail; the expanded one shows the large image instead
                expect(_cards(pane).nth(index).locator(".attempt-thumb img")).to_be_visible()
        last = _cards(pane).nth(2)
        expect(last.locator(".attempt-thumb")).to_have_count(0)
        expect(last).to_have_attribute("aria-expanded", "true")
        expect(last.locator("img.attempt-image")).to_be_visible()
        expect(last.locator(".attempt-full-prompt")).to_have_text(prompts[2])
        expect(last.locator("details.attempt-advanced")).not_to_have_attribute("open", "")
        expect(last.get_by_role("button", name="在这张基础上改")).to_be_visible()
        expect(last.get_by_role("button", name="换个构图")).to_be_visible()
        assert last.locator(".attempt-actions button").count() == 2  # no per-attempt delete (D-00c)
        # timeline-three-rounds is judged as a declared pair per viewport: pinned to the end, the
        # expanded 第 3 次 is whole (header, image, prompt, 高级参数, both actions); scrolled to the top
        # by the user, 第 1 次 → 第 3 次 headers are all in view.
        for name in ("wide", "narrow"):
            width, height = VIEWPORTS[name]
            page.set_viewport_size({"width": width, "height": height})
            outside = _outside_timeline(page, ".attempt[aria-expanded=true] :is(.attempt-label, .attempt-image, "
                                              ".attempt-full-prompt, .attempt-advanced summary, .attempt-actions button)")
            assert not outside, (name, "end of timeline: expanded card cut", outside)
            _check_state(page, "timeline-three-rounds", harness=harness, viewports=(name,))
            pane.locator("[data-image-timeline]").hover()
            page.mouse.wheel(0, -10_000)
            page.wait_for_function("() => document.querySelector('#pane-image .image-timeline').scrollTop === 0")
            outside = _outside_timeline(page, ".attempt .attempt-label")
            assert not outside, (name, "top of timeline: a 第 N 次 header is cut", outside)
            _check_state(page, "timeline-three-rounds-top", harness=harness, viewports=(name,))
            page.mouse.wheel(0, 10_000)  # back to the end, where the next viewport's check starts
            page.wait_for_function("""() => { const t = document.querySelector('#pane-image .image-timeline');
                return t.scrollHeight - t.scrollTop - t.clientHeight <= 2; }""")

        first = _cards(pane).nth(0)
        first.click()
        expect(first).to_have_attribute("aria-expanded", "true")
        expect(_cards(pane).nth(2)).to_have_attribute("aria-expanded", "false")
        expect(pane.locator(".attempt[aria-expanded='true']")).to_have_count(1)
        _check_state(page, "attempt-selected-actions", harness=harness)

        # 换个构图 on the first attempt: same prompt and size, a different seed, inputs untouched.
        pane.locator("[data-image-prompt]").fill("草稿不应被改")
        first.get_by_role("button", name="换个构图").click()
        _wait_status(pane, 4, "done")
        expect(pane.locator("[data-image-prompt]")).to_have_value("草稿不应被改")
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[3]["params"]["prompt"] == prompts[0]
        assert attempts[3]["params"]["seed"] != attempts[0]["params"]["seed"]
        assert {k: attempts[3]["params"][k] for k in ("width", "height", "steps")} == \
            {k: attempts[0]["params"][k] for k in ("width", "height", "steps")}

        # A new session starts empty and only it receives the next image (AC-4).
        pane.locator("[data-image-session-new]").click()
        items = pane.locator("[data-image-session-list] [data-session-id]")
        expect(items).to_have_count(2)
        expect(items.first).to_have_attribute("aria-current", "true")
        expect(pane.locator("[data-image-empty]")).to_be_visible()
        expect(pane.locator("[data-image-prompt]")).to_be_focused()
        _check_state(page, "empty-session", harness=harness)
        assert _session(page, harness, session_id)["attempts"] == attempts


def test_failed_and_cancelled_attempts_show_reasons_without_blank_images(page, tmp_path):
    """AC-6: failures and cancellations stay in the session with their reason and both actions."""
    failing = [Line("step 1/10"), Line("Traceback (most recent call last): boom"), Exit(1)]
    with _harness(tmp_path, [failing, cancellable_media_steps()]) as harness:
        pane = _open(page, harness)
        _generate(pane, "会失败的一张")
        _wait_status(pane, 1, "failed")
        # Once the file says the attempt settled, the pane must not keep claiming it is generating.
        expect(pane.locator("[data-image-hint-text]")).not_to_contain_text("正在生成", timeout=1500)
        card = _cards(pane).first
        expect(card.locator(".attempt-badge")).to_have_text("失败")
        expect(card.locator(".attempt-reason")).to_have_text("生成程序异常退出")
        expect(card.locator("img")).to_have_count(0)
        expect(card.locator(".attempt-icon.tone-danger")).to_be_visible()
        details = card.locator("details.attempt-error-details")
        details.locator("summary").click()
        expect(details).to_contain_text("exit_nonzero")
        expect(details).to_contain_text("boom")
        expect(card.get_by_role("button", name="在这张基础上改")).to_be_visible()
        expect(card.get_by_role("button", name="换个构图")).to_be_visible()
        _check_state(page, "attempt-failed", harness=harness)

        _generate(pane, "会被取消的一张")
        running = _cards(pane).nth(1)
        expect(running).to_have_attribute("data-attempt-status", "running")
        expect(running.locator("progress")).to_be_visible()
        expect(running.locator("img")).to_have_count(0)
        expect(running.get_by_role("button", name="换个构图")).to_have_count(0)
        expect(pane.locator("[data-image-hint-text]")).to_have_text("正在生成这个会话里的第 2 次")
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("li[aria-current='true'] [data-session-running]")).to_have_text("生成中")
        expect(running.locator("details.attempt-log")).not_to_have_attribute("open", "")
        _check_state(page, "running", harness=harness)
        harness.media_script.step()
        running.get_by_role("button", name="取消").click()
        _wait_status(pane, 2, "cancelled")
        cancelled = _cards(pane).nth(1)
        expect(cancelled.locator(".attempt-badge")).to_have_text("已取消")
        expect(cancelled.locator("img")).to_have_count(0)
        expect(cancelled.locator(".attempt-icon.tone-muted")).to_be_visible()
        expect(cancelled.get_by_role("button", name="换个构图")).to_be_visible()
        expect(pane.locator("li[aria-current='true'] [data-session-running]")).to_have_count(0)
        _check_state(page, "attempt-cancelled", harness=harness)


def test_running_job_stays_in_its_session_while_viewing_another(page, tmp_path):
    """Quality question 1 / AC-4: progress and result land in the session that started the job."""
    with _harness(tmp_path, [default_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        session_a = _current_id(pane)
        _generate(pane, "甲会话的灯塔")
        running = _cards(pane).first
        expect(running).to_have_attribute("data-attempt-status", "running")
        expect(running.locator(".attempt-log pre")).to_contain_text("step 1/10")

        pane.locator("[data-image-session-new]").click()
        expect(pane.locator("[data-image-session-list] [data-session-id]")).to_have_count(2)
        session_b = _current_id(pane)
        assert session_b != session_a
        expect(pane.locator("[data-image-empty]")).to_be_visible()
        expect(pane.locator("[data-image-hint-text]")).to_have_text("「甲会话的灯塔」正在生成图片")
        expect(pane.locator("[data-image-return]")).to_be_visible()
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        item_a = pane.locator(f"[data-image-session-list] [data-session-id='{session_a}']")
        expect(item_a.locator("[data-session-running]")).to_have_text("生成中")
        # Session B is brand new and empty here, so this is not the criteria's running-other-session
        # (whose B already holds a finished attempt); that state is captured by
        # tests/e2e/test_image_sessions.py::test_running_in_one_session_while_viewing_another_that_has_images.
        _check_state(page, "running-other-session-new-empty", harness=harness)

        harness.media_script.step()  # progress while B is on screen
        pane.locator("[data-image-return]").click()
        expect(pane.locator("[data-image-session-list] li[aria-current='true']")).to_have_attribute("data-session-id", session_a)
        running = _cards(pane).first
        expect(running.locator(".attempt-log pre")).to_contain_text("step 5/10", timeout=15_000)
        expect(running.locator("progress")).to_have_attribute("value", "50")

        item_b = pane.locator(f"[data-image-session-list] [data-session-id='{session_b}']")
        item_b.click()
        expect(pane.locator("[data-image-empty]")).to_be_visible()
        harness.media_script.step()  # finishes while B is on screen
        expect(item_a.locator("[data-session-running]")).to_have_count(0, timeout=15_000)
        expect(_cards(pane)).to_have_count(0)
        assert _session(page, harness, session_b)["attempts"] == []
        assert [a["status"] for a in _session(page, harness, session_a)["attempts"]] == ["done"]

        _generate(pane, "乙会话自己的图")
        _wait_status(pane, 1, "done")
        assert [a["params"]["prompt"] for a in _session(page, harness, session_b)["attempts"]] == ["乙会话自己的图"]
        assert len(_session(page, harness, session_a)["attempts"]) == 1

        item_a.click()
        expect(_cards(pane)).to_have_count(1)
        expect(_cards(pane).first).to_have_attribute("data-attempt-status", "done")
        expect(_cards(pane).first.locator(".attempt-full-prompt")).to_have_text("甲会话的灯塔")


def test_rename_delete_keeps_images_in_library(page, tmp_path):
    """AC-5 / D-89 / D-90."""
    with _harness(tmp_path, [fast_media_steps(), default_media_steps()]) as harness:
        pane = _open(page, harness)
        _generate(pane, "要被删掉分组的图")
        _wait_status(pane, 1, "done")
        output = _session(page, harness, _current_id(pane))["attempts"][0]["output"]

        item = pane.locator("[data-image-session-list] li[aria-current='true']")
        item.hover()
        item.get_by_role("button", name="改名").click()
        rename = item.locator("input.session-rename")
        expect(rename).to_be_focused()
        expect(rename).to_have_value("要被删掉分组的图")
        _check_state(page, "rename", harness=harness)
        rename.fill("窗边小猫")
        rename.press("Enter")
        expect(item.locator(".session-title")).to_have_text("窗边小猫")

        item.hover()
        item.get_by_role("button", name="删除会话：窗边小猫").click()
        dialog = page.locator(".overlay .dialog")
        expect(dialog.locator("h3")).to_have_text("删除会话")
        expect(dialog.locator("p")).to_have_text("确定删除「窗边小猫」？只删除这个会话分组，其中的图片仍保留在素材库。")
        expect(dialog.get_by_role("button", name="取消")).to_be_focused()
        _check_state(page, "delete-confirm", harness=harness)
        dialog.get_by_role("button", name="删除").click()
        items = pane.locator("[data-image-session-list] [data-session-id]")
        expect(items).to_have_count(1)
        expect(items.first).to_contain_text("新会话")
        expect(pane.locator("[data-image-empty]")).to_be_visible()

        # A session whose job is still running warns that the image will go to the library only.
        _generate(pane, "删除时还在生成")
        expect(_cards(pane).first).to_have_attribute("data-attempt-status", "running")
        item = pane.locator("[data-image-session-list] li[aria-current='true']")
        item.hover()
        item.get_by_role("button", name="删除会话：删除时还在生成").click()
        expect(dialog.locator("p")).to_contain_text(
            "这个会话正在生成图片，生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。")
        _check_state(page, "delete-confirm-running", harness=harness)
        dialog.get_by_role("button", name="删除").click()
        expect(pane.locator("[data-image-session-list] [data-session-id]")).to_have_count(1)
        harness.media_script.step()
        harness.media_script.step()

        page.locator("#tabs [data-tab='library']").click()
        library = page.locator("#pane-library")
        entry = library.locator("li").filter(has_text="要被删掉分组的图")
        expect(entry).to_be_visible()
        entry.get_by_role("button", name="预览").click()
        preview = library.locator("[data-lib-player] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('[data-lib-player] img').naturalWidth > 0")
        expect(library.locator("li").filter(has_text="删除时还在生成")).to_be_visible(timeout=15_000)


def test_restart_keeps_sessions_and_marks_interrupted_and_missing_files(page, tmp_path):
    """AC-3 plus the interrupted and file-missing states (D-25, D-85)."""
    with _harness(tmp_path, [fast_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        session_id = _current_id(pane)
        _generate(pane, "重启前的第一张")
        _wait_status(pane, 1, "done")
        _generate(pane, "重启前的第二张")
        _wait_status(pane, 2, "done")
        before = _session(page, harness, session_id)
        sessions_dir = harness.roots.image_sessions_dir
        outputs_root = harness.outputs_root

    # Simulate a crash mid-generation: the file still says running when the app starts again.
    path = sessions_dir / f"{session_id}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["attempts"].append({
        "id": "f" * 32, "job_id": 9, "ts": "2026-09-24T15:00:00", "finished": None, "status": "running",
        "params": {"prompt": "重启时还在生成", "width": 1024, "height": 1024, "steps": 40, "seed": 7},
        "output": None, "error": None})
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")

    with _harness(tmp_path, []) as harness:
        pane = _open(page, harness)
        assert _current_id(pane) == session_id
        expect(_cards(pane)).to_have_count(3)
        for index in (0, 1):
            expect(_cards(pane).nth(index)).to_have_attribute("data-attempt-status", "done")
            expect(_cards(pane).nth(index).locator(".attempt-thumb img")).to_be_visible()
        interrupted = _cards(pane).nth(2)
        expect(interrupted).to_have_attribute("data-attempt-status", "failed")
        expect(interrupted.locator(".attempt-reason")).to_have_text("应用在生成途中关闭，这次没有完成")
        expect(interrupted.locator("progress")).to_have_count(0)
        _check_state(page, "attempt-interrupted", harness=harness)
        after = _session(page, harness, session_id)
        assert [a["id"] for a in after["attempts"][:2]] == [a["id"] for a in before["attempts"]]

        (outputs_root / before["attempts"][0]["output"]).unlink()
        page.reload()
        missing = _cards(pane).first
        expect(missing).to_have_attribute("data-attempt-status", "missing")
        expect(missing).to_contain_text("图片文件已不在")
        expect(missing).to_contain_text("可能已在访达中移动或删除")
        expect(missing.locator("img")).to_have_count(0)
        missing.click()
        expect(missing.get_by_role("button", name="在这张基础上改")).to_be_enabled()
        expect(missing.get_by_role("button", name="换个构图")).to_be_enabled()
        _check_state(page, "attempt-file-missing", harness=harness)


def test_corrupt_session_and_list_load_failure(page, tmp_path):
    """§7.2: a corrupt file only offers delete; a failing list explains itself and offers retry."""
    with _harness(tmp_path, []) as harness:
        sessions_dir = harness.roots.image_sessions_dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / ("c" * 32 + ".json")).write_text("{ not json", encoding="utf-8")
        healthy = harness.library.image_sessions.create()["id"]
        page.route("**/api/image-sessions", lambda route: route.fulfill(
            status=500, content_type="application/json", body=json.dumps({"error": "磁盘读不出来"}))
            if route.request.method == "GET" else route.continue_())
        page.goto(harness.base_url + "#tab=image")
        pane = page.locator("#pane-image")
        expect(pane.locator("[data-image-session-list]")).to_contain_text("会话列表读不出来：磁盘读不出来")
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-hint-text]")).to_have_text("会话还没加载好")
        _check_state(page, "session-list-load-failed", harness=harness)
        page.unroute("**/api/image-sessions")
        pane.get_by_role("button", name="重试").click()

        items = pane.locator("[data-image-session-list] [data-session-id]")
        expect(items).to_have_count(2)  # the healthy session first, the corrupt one last
        expect(items.nth(0)).to_have_attribute("data-session-id", healthy)
        expect(items.nth(0)).to_have_attribute("aria-current", "true")
        corrupt = items.nth(1)
        expect(corrupt.locator(".session-title")).to_have_text("无法读取的会话")
        expect(corrupt.locator(".session-meta")).to_have_text("文件已损坏")
        expect(corrupt.get_by_role("button", name="改名")).to_have_count(0)
        corrupt.click()
        expect(pane.locator("[data-image-empty]")).to_have_text(
            "这个会话文件已损坏，无法显示。可以删除它，素材库里的图片不受影响。")
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-hint-text]")).to_have_text("请选择其他会话或新建一个")
        _check_state(page, "corrupt-session", harness=harness)
        corrupt.hover()
        corrupt.get_by_role("button", name="删除会话：无法读取的会话").click()
        page.locator(".overlay .dialog").get_by_role("button", name="删除").click()
        expect(items).to_have_count(1)
        expect(pane.locator("[data-image-start]")).to_be_enabled()


def test_other_media_job_blocks_generation_without_return_button(page, tmp_path):
    with _harness(tmp_path, [fast_media_steps(), default_media_steps()], with_other_media=True) as harness:
        pane = _open(page, harness)
        _generate(pane, "先有一张")
        _wait_status(pane, 1, "done")
        page.locator("#tabs [data-tab='video']").click()
        video = page.locator("#pane-video")
        video.locator("[data-video-prompt]").fill("视频占用")
        video.locator("[data-video-start]").click()
        expect(video.locator("[data-job-log]")).to_contain_text("step 1/10")
        page.locator("#tabs [data-tab='image']").click()
        card = _cards(pane).first
        expect(card.get_by_role("button", name="换个构图")).to_be_disabled(timeout=15_000)
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-return]")).to_be_hidden()
        expect(card.get_by_role("button", name="在这张基础上改")).to_be_enabled()
        reason = pane.locator("[data-image-hint-text]").inner_text()
        assert reason and "正在生成图片" not in reason, reason
        _check_state(page, "busy-other-media", harness=harness)
        harness.media_script.step()
        harness.media_script.step()
