"""Verification of image sessions against the confirmed acceptance (image-sessions rev 1).

Falsification pass owned by image-session-verify. Each test states the acceptance it tries to break
and asserts on what the backend settled (GET /api/image-sessions/{id}, /api/history, /api/outputs),
not on what the form happened to hold. Runs against launch_test_harness — real DeskApp,
LibraryService, ImageSessionStore, MediaService and desk/static in real Chromium — with the scripted
media executor writing a small PNG instead of running Qwen-Image; the real-model journey is proved
separately against a built app bundle.

Visual states reuse the DOM checks of test_image_flow.py (no 「种子」 in the main flow, no blank
image, no horizontal scroll, no clipped button, no overlap) at 1280×800 and 900×700; when
LMD_IMAGE_SESSIONS_SHOTS names a directory each checked state is saved there.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import Exit, Line, MediaScript, cancellable_media_steps, default_media_steps, fast_media_steps
from test_image_flow import VIEWPORTS, _check_state

SESSION_ITEMS = "[data-image-session-list] [data-session-id]"
CURRENT_ITEM = "[data-image-session-list] li[aria-current='true']"


def _harness(tmp_path, jobs=(), *, image_runtime=True):
    return launch_test_harness(tmp_path, model_states={"qwen-image": "present"},
                               image_runtime=image_runtime, media_script=MediaScript(list(jobs)))


def _open(page, harness):
    page.goto(harness.base_url + "#tab=image")
    pane = page.locator("#pane-image")
    expect(pane).to_be_visible()
    expect(pane.locator(CURRENT_ITEM)).to_have_count(1)
    return pane


def _cards(pane):
    return pane.locator("[data-image-timeline] .attempt")


def _generate(pane, prompt=None):
    if prompt is not None:
        pane.locator("[data-image-prompt]").fill(prompt)
    start = pane.locator("[data-image-start]")
    expect(start).to_be_enabled()
    start.click()


def _settled(pane, count, status="done"):
    expect(_cards(pane)).to_have_count(count)
    expect(_cards(pane).nth(count - 1)).to_have_attribute("data-attempt-status", status, timeout=15_000)
    # The composer must stop claiming a generation once the file says it settled.
    expect(pane.locator("[data-image-start]")).to_be_enabled(timeout=5_000)


def _current_id(pane):
    return pane.locator(CURRENT_ITEM).get_attribute("data-session-id")


def _get(page, harness, path):
    response = page.request.get(harness.base_url + path)
    assert response.status == 200, (path, response.status, response.text())
    return response.json()


def _session(page, harness, session_id):
    return _get(page, harness, f"/api/image-sessions/{session_id}")


def _timeline_snapshot(pane):
    """What the user can see of a session's timeline, card by card."""
    return pane.evaluate("""(root) => [...root.querySelectorAll('[data-image-timeline] .attempt')].map((card) => ({
        id: card.dataset.attemptId, status: card.dataset.attemptStatus,
        expanded: card.getAttribute('aria-expanded'),
        label: card.querySelector('.attempt-label')?.textContent,
        prompt: card.querySelector('.attempt-prompt')?.textContent,
        spec: card.querySelector('.attempt-spec')?.textContent,
        // the card's own image: its thumbnail when collapsed, the large image in its place when expanded
        image: card.querySelector('.attempt-thumb img, img.attempt-image')?.getAttribute('src') ?? null,
    }))""")


def _advanced_values(card):
    """The four values listed in an expanded card's 高级参数 block (opened to read them)."""
    details = card.locator("details.attempt-advanced")
    details.locator("summary").click()
    expect(details).to_have_attribute("open", "")
    text = details.inner_text()
    details.locator("summary").click()
    numbers = {}
    for label, key in (("宽度", "width"), ("高度", "height"), ("步数", "steps"), ("种子", "seed")):
        found = re.search(label + r"\D*?(\d+)", text)
        assert found, (label, text)
        numbers[key] = int(found.group(1))
    return numbers


def _set_advanced(pane, **values):
    details = pane.locator("details[data-image-advanced]")
    if details.get_attribute("open") is None:
        details.locator("summary").click()
    for key, value in values.items():
        pane.locator(f"[data-image-{key}]").fill(str(value))
    details.locator("summary").click()
    expect(details).not_to_have_attribute("open", "")


def test_ac1_ac2_three_refine_rounds_stay_ordered_with_their_params_and_seeds(page, tmp_path):
    """AC-1 and AC-2, read back from the session file the backend wrote."""
    with _harness(tmp_path, [fast_media_steps() for _ in range(4)]) as harness:
        pane = _open(page, harness)
        session_id = _current_id(pane)
        # Non-default size and steps so a refine that forgot to carry them would be caught.
        _set_advanced(pane, width=768, height=512, steps=20)
        first_prompt = "  清晨的港口，\n\n渔船    归来，薄雾笼罩着远处的灯塔与山峦  "
        prompts = [first_prompt, "清晨的港口，渔船归来，加一只海鸥", "清晨的港口，渔船归来，加一只海鸥，暖色调"]
        _generate(pane, prompts[0])
        _settled(pane, 1)

        for round_index in (1, 2):
            source = _cards(pane).nth(round_index - 1)
            source.click()
            expect(source).to_have_attribute("aria-expanded", "true")
            source.get_by_role("button", name="在这张基础上改").click()
            expect(pane.locator("[data-image-prompt]")).to_have_value(prompts[round_index - 1])
            expect(pane.locator("[data-image-refine-text]")).to_have_text(f"沿用第 {round_index} 次的构图")
            expect(_cards(pane)).to_have_count(round_index)
            _generate(pane, prompts[round_index])
            _settled(pane, round_index + 1)

        attempts = _session(page, harness, session_id)["attempts"]
        assert [a["status"] for a in attempts] == ["done", "done", "done"]
        assert [a["params"]["prompt"] for a in attempts] == prompts  # stored as typed, not trimmed
        assert [a["ts"] for a in attempts] == sorted(a["ts"] for a in attempts)
        for attempt in attempts:
            assert {k: attempt["params"][k] for k in ("width", "height", "steps")} == \
                {"width": 768, "height": 512, "steps": 20}
        seeds = [a["params"]["seed"] for a in attempts]
        assert seeds[0] == seeds[1] == seeds[2], seeds
        assert len({a["output"] for a in attempts}) == 3
        for attempt in attempts:
            assert page.request.get(f"{harness.base_url}/api/outputs/{attempt['output']}").status == 200

        # The timeline shows the three in order, each with its own parameters and image.
        cards = _cards(pane)
        for index, attempt in enumerate(attempts):
            card = cards.nth(index)
            expect(card).to_have_attribute("data-attempt-id", attempt["id"])
            expect(card.locator(".attempt-label")).to_contain_text(f"第 {index + 1} 次")
            expect(card.locator(".attempt-spec")).to_have_text("768×512 · 20 步")
            # Collapsed: the thumbnail; expanded (the last one on open): the large image in its place.
            shown = card.locator(".attempt-thumb img, img.attempt-image")
            expect(shown).to_have_count(1)
            expect(shown).to_have_attribute("src", re.compile(re.escape(attempt["output"])))
            card.click()
            expect(card).to_have_attribute("aria-expanded", "true")
            expect(card.locator(".attempt-full-prompt")).to_have_text(" ".join(attempt["params"]["prompt"].split()))
            assert _advanced_values(card) == {"width": 768, "height": 512, "steps": 20, "seed": seeds[0]}

        # D-11: the title is the first prompt with whitespace folded, cut at 24 characters.
        folded = " ".join(first_prompt.split())
        title = pane.locator(CURRENT_ITEM).locator(".session-title")
        expect(title).to_have_text(folded[:24] + "…")
        assert _session(page, harness, session_id)["title"] == folded[:24] + "…"

        # 换个构图 on the second attempt: same prompt and size, a new seed, form untouched.
        pane.locator("[data-image-prompt]").fill("输入框里的草稿")
        second = cards.nth(1)
        second.click()
        second.get_by_role("button", name="换个构图").click()
        _settled(pane, 4)
        expect(pane.locator("[data-image-prompt]")).to_have_value("输入框里的草稿")
        recomposed = _session(page, harness, session_id)["attempts"][3]
        assert recomposed["params"]["prompt"] == prompts[1]
        assert recomposed["params"]["seed"] != seeds[1]
        assert {k: recomposed["params"][k] for k in ("width", "height", "steps")} == \
            {"width": 768, "height": 512, "steps": 20}
        # Earlier attempts were not rewritten by the later ones (append only, BR-8).
        assert _session(page, harness, session_id)["attempts"][:3] == attempts
        _check_state(page, "verify-four-attempts", harness=harness)


def test_new_sessions_first_image_uses_a_fresh_random_seed(page, tmp_path):
    """D-19 / D-66: no fixed default seed — the request omits it and the backend draws one."""
    with _harness(tmp_path, [fast_media_steps() for _ in range(3)]) as harness:
        bodies = []
        page.on("request", lambda r: bodies.append(r.post_data_json)
                if r.url.endswith("/api/media/image") and r.method == "POST" else None)
        pane = _open(page, harness)
        seeds = []
        for index in range(3):
            if index:
                pane.locator("[data-image-session-new]").click()
                expect(pane.locator(SESSION_ITEMS)).to_have_count(index + 1)
                expect(pane.locator("[data-image-empty]")).to_be_visible()
            expect(pane.locator("[data-image-seed]")).to_have_value("")
            _generate(pane, "同一句提示词")
            _settled(pane, 1)
            seeds.append(_session(page, harness, _current_id(pane))["attempts"][0]["params"]["seed"])
        assert all("seed" not in body for body in bodies), bodies
        assert len(set(seeds)) == 3, seeds
        assert 42 not in seeds
        assert all(0 <= seed <= 4294967295 for seed in seeds)


def test_ac4_switching_away_and_back_changes_nothing_and_new_session_takes_only_new_images(page, tmp_path):
    """AC-4: switch → switch back leaves the timeline and the file as they were."""
    with _harness(tmp_path, [fast_media_steps() for _ in range(4)]) as harness:
        pane = _open(page, harness)
        session_a = _current_id(pane)
        _generate(pane, "甲会话：雪山")
        _settled(pane, 1)
        _generate(pane, "甲会话：雪山，夜晚")
        _settled(pane, 2)
        _cards(pane).first.click()  # the user's selection is part of what must survive
        expect(_cards(pane).first).to_have_attribute("aria-expanded", "true")
        before_view = _timeline_snapshot(pane)
        before_file = _session(page, harness, session_a)

        pane.locator("[data-image-session-new]").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(2)
        session_b = _current_id(pane)
        assert session_b != session_a
        expect(_cards(pane)).to_have_count(0)
        _generate(pane, "乙会话：沙漠")
        _settled(pane, 1)

        pane.locator(f"{SESSION_ITEMS}[data-session-id='{session_a}']").click()
        expect(pane.locator(CURRENT_ITEM)).to_have_attribute("data-session-id", session_a)
        expect(_cards(pane)).to_have_count(2)
        after_view = _timeline_snapshot(pane)
        # Reopening selects the last attempt by design (D-72); everything else must be identical.
        strip = lambda view: [{k: v for k, v in card.items() if k != "expanded"} for card in view]
        assert strip(after_view) == strip(before_view)
        assert _session(page, harness, session_a) == before_file  # viewing does not rewrite (D-05)

        b = _session(page, harness, session_b)
        assert [a["params"]["prompt"] for a in b["attempts"]] == ["乙会话：沙漠"]
        assert all(a["params"]["prompt"].startswith("甲") for a in before_file["attempts"])

        pane.locator(f"{SESSION_ITEMS}[data-session-id='{session_b}']").click()
        expect(_cards(pane)).to_have_count(1)
        expect(_cards(pane).first.locator(".attempt-full-prompt")).to_have_text("乙会话：沙漠")
        # Without a new session, the next image joins the current one (BR-4).
        _generate(pane, "乙会话：沙漠，日落")
        _settled(pane, 2)
        assert len(_session(page, harness, session_b)["attempts"]) == 2
        assert len(_session(page, harness, session_a)["attempts"]) == 2
        _check_state(page, "verify-switch-back", harness=harness)


def test_rename_stops_automatic_titles(page, tmp_path):
    """D-11 / D-12: only an untouched empty session takes its title from the first prompt."""
    with _harness(tmp_path, [fast_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        session_id = _current_id(pane)
        item = pane.locator(CURRENT_ITEM)
        item.hover()
        item.get_by_role("button", name="改名").click()
        rename = item.locator("input.session-rename")
        rename.fill("我的海报")
        rename.press("Enter")
        expect(item.locator(".session-title")).to_have_text("我的海报")
        _generate(pane, "第一句提示词不应成为标题")
        _settled(pane, 1)
        expect(item.locator(".session-title")).to_have_text("我的海报")
        stored = _session(page, harness, session_id)
        assert (stored["title"], stored["title_auto"]) == ("我的海报", False)
        _generate(pane, "第二句")
        _settled(pane, 2)
        assert _session(page, harness, session_id)["title"] == "我的海报"


def test_ac5_deleting_a_session_keeps_its_images_in_the_library(page, tmp_path):
    """AC-5: the session leaves the list, the current one moves on, the image still opens."""
    with _harness(tmp_path, [fast_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        doomed = _current_id(pane)
        _generate(pane, "将被删除分组的灯塔")
        _settled(pane, 1)
        output = _session(page, harness, doomed)["attempts"][0]["output"]
        pane.locator("[data-image-session-new]").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(2)
        keeper = _current_id(pane)
        _generate(pane, "留下来的会话")
        _settled(pane, 1)
        outputs_before = _get(page, harness, "/api/outputs")
        history_before = _get(page, harness, "/api/history")

        pane.locator(f"{SESSION_ITEMS}[data-session-id='{doomed}']").click()
        expect(pane.locator(CURRENT_ITEM)).to_have_attribute("data-session-id", doomed)
        item = pane.locator(CURRENT_ITEM)
        item.hover()
        item.get_by_role("button", name="删除会话：将被删除分组的灯塔").click()
        # D-90: focus starts on 「取消」, and that focus is visible, not only present in the DOM (N-01).
        focus = page.evaluate("""() => { const b = document.activeElement; const s = getComputedStyle(b);
            return {text: b.innerText, in_dialog: !!b.closest('.overlay .dialog'),
                    outline: s.outlineStyle, width: parseFloat(s.outlineWidth) || 0}; }""")
        assert focus["text"] == "取消" and focus["in_dialog"], focus
        assert focus["outline"] != "none" and focus["width"] >= 2, ("取消 has no visible focus ring", focus)
        page.locator(".overlay .dialog").get_by_role("button", name="删除").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(1)
        expect(pane.locator(f"{SESSION_ITEMS}[data-session-id='{doomed}']")).to_have_count(0)
        expect(pane.locator(CURRENT_ITEM)).to_have_attribute("data-session-id", keeper)
        expect(_cards(pane)).to_have_count(1)
        assert page.request.get(f"{harness.base_url}/api/image-sessions/{doomed}").status == 404
        assert [s["id"] for s in _get(page, harness, "/api/image-sessions")] == [keeper]
        assert _get(page, harness, "/api/outputs") == outputs_before
        assert _get(page, harness, "/api/history") == history_before
        _check_state(page, "verify-after-delete", harness=harness)

        page.locator("#tabs [data-tab='library']").click()
        library = page.locator("#pane-library")
        entry = library.locator("li").filter(has_text="将被删除分组的灯塔")
        expect(entry).to_be_visible()
        entry.get_by_role("button", name="预览").click()
        preview = library.locator("[data-lib-player] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('[data-lib-player] img')?.naturalWidth > 0")
        _check_library(page, "library-after-delete", harness)


def _check_library(page, state, harness):
    """library-after-delete lives on the library pane: the preview must be a real picture."""
    shots = os.environ.get("LMD_IMAGE_SESSIONS_SHOTS")
    for name in ("wide", "narrow"):
        width, height = VIEWPORTS[name]
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_function("() => document.querySelector('[data-lib-player] img')?.naturalWidth > 0")
        page.locator("[data-lib-player]").scroll_into_view_if_needed()
        checks = page.evaluate("""() => {
          const pane = document.querySelector('#pane-library');
          const visible = (el) => el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          const scroller = document.scrollingElement;
          return {
            seed_word_in_main_flow: pane.innerText.includes('种子'),
            blank_images: [...pane.querySelectorAll('img')].filter(visible).filter((i) => !i.complete || i.naturalWidth === 0).length,
            horizontal_scroll: scroller.scrollWidth > scroller.clientWidth,
            clipped_buttons: [...pane.querySelectorAll('button')].filter(visible)
              .filter((b) => b.scrollWidth > b.clientWidth + 1).map((b) => b.innerText),
            preview_natural_width: pane.querySelector('[data-lib-player] img')?.naturalWidth ?? 0,
            preview_gap: pane.querySelector('[data-lib-player]').getBoundingClientRect().top
              - pane.querySelector('[data-lib-refresh]').getBoundingClientRect().bottom,
          };
        }""")
        if shots:
            folder = Path(shots)
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / f"{state}-{name}.png"))
            (folder / f"{state}-{name}.json").write_text(json.dumps({
                "state_id": state, "viewport": {"name": name, "width": width, "height": height},
                "url": page.url, "dom_checks": checks,
                "served_by": {"host": harness.base_url, "process": "desk.testing.launch_test_harness",
                              "mock_layers": ["FakeMediaExecutor (desk/testing/scripts.py MediaScript)",
                                              "FakeLlmBackend", "FakeMemoryReader", "FixedClock"]},
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        assert checks["preview_natural_width"] > 0, (state, name)
        assert checks["blank_images"] == 0, (state, name)
        assert not checks["horizontal_scroll"], (state, name)
        assert checks["clipped_buttons"] == [], (state, name, checks["clipped_buttons"])
        assert checks["preview_gap"] >= 8, ("preview sits directly under 刷新", state, name, checks["preview_gap"])


def test_deleting_a_session_while_it_generates_sends_the_image_to_the_library_only(page, tmp_path):
    """D-31: no error, the job finishes, the image is in the library and in no session."""
    with _harness(tmp_path, [default_media_steps()]) as harness:
        pane = _open(page, harness)
        doomed = _current_id(pane)
        _generate(pane, "生成中被删的会话")
        expect(_cards(pane).first).to_have_attribute("data-attempt-status", "running")
        item = pane.locator(CURRENT_ITEM)
        item.hover()
        item.get_by_role("button", name="删除会话：生成中被删的会话").click()
        page.locator(".overlay .dialog").get_by_role("button", name="删除").click()
        expect(pane.locator(f"{SESSION_ITEMS}[data-session-id='{doomed}']")).to_have_count(0)
        expect(pane.locator(SESSION_ITEMS)).to_have_count(1)  # D-90: an emptied list gets a fresh session
        harness.media_script.step()
        harness.media_script.step()
        expect(pane.locator("[data-image-start]")).to_be_enabled(timeout=15_000)
        expect(pane.locator("[data-image-error]")).to_be_hidden()
        history = _get(page, harness, "/api/history")
        entry = next(e for e in history if (e.get("params") or {}).get("prompt") == "生成中被删的会话")
        assert entry["session_id"] == doomed
        output = entry["output"]
        assert output and output in [o["name"] for o in _get(page, harness, "/api/outputs")], entry
        assert page.request.get(f"{harness.base_url}/api/outputs/{output}").status == 200
        for summary in _get(page, harness, "/api/image-sessions"):
            attempts = _session(page, harness, summary["id"])["attempts"]
            assert all(a["params"]["prompt"] != "生成中被删的会话" for a in attempts)


def test_library_refill_reopens_the_session_and_selects_that_attempt(page, tmp_path):
    """D-94: refill from the library goes back to the attempt's own session and number."""
    with _harness(tmp_path, [fast_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        origin = _current_id(pane)
        _generate(pane, "回填：第一张")
        _settled(pane, 1)
        _generate(pane, "回填：第二张")
        _settled(pane, 2)
        first = _session(page, harness, origin)["attempts"][0]
        pane.locator("[data-image-session-new]").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(2)
        pane.locator("[data-image-prompt]").fill("")

        page.locator("#tabs [data-tab='library']").click()
        page.locator("#pane-library li").filter(has_text="回填：第一张").get_by_role("button", name="回填参数").click()
        expect(pane).to_be_visible()
        expect(pane.locator(CURRENT_ITEM)).to_have_attribute("data-session-id", origin)
        card = pane.locator(f"[data-image-timeline] .attempt[data-attempt-id='{first['id']}']")
        expect(card).to_have_attribute("aria-expanded", "true")
        expect(pane.locator(".attempt[aria-expanded='true']")).to_have_count(1)
        expect(pane.locator("[data-image-prompt]")).to_have_value("回填：第一张")
        expect(pane.locator("[data-image-refine-text]")).to_have_text("沿用第 1 次的构图")
        expect(pane.locator("[data-image-seed]")).to_have_value(str(first["params"]["seed"]))


def test_ac6_failed_and_cancelled_attempts_keep_their_reason_and_no_blank_image(page, tmp_path):
    """AC-6, checked against the stored status and error code as well as the card."""
    failing = [Line("step 1/10"), Line("RuntimeError: Metal out of memory"), Exit(1)]
    with _harness(tmp_path, [failing, cancellable_media_steps()]) as harness:
        pane = _open(page, harness)
        session_id = _current_id(pane)
        _generate(pane, "失败的尝试")
        _settled(pane, 1, "failed")
        _generate(pane, "取消的尝试")
        expect(_cards(pane).nth(1)).to_have_attribute("data-attempt-status", "running")
        harness.media_script.step()
        _cards(pane).nth(1).get_by_role("button", name="取消").click()
        _settled(pane, 2, "cancelled")

        stored = _session(page, harness, session_id)["attempts"]
        assert [a["status"] for a in stored] == ["failed", "cancelled"]
        assert stored[0]["error"]["code"] == "exit_nonzero" and stored[0]["output"] is None
        assert stored[1]["error"]["code"] == "cancelled" and stored[1]["output"] is None
        # D-85: a failure names its cause; a user cancel carries its 「已取消」 mark and, as its
        # explanation, the stored D-09 message without the repeated 「已取消：」 prefix (AC-6 「显示原因」).
        expect(_cards(pane).nth(0).locator(".attempt-reason")).to_have_text("内存不足，生成被中止")
        expect(_cards(pane).nth(1).locator(".attempt-reason-sub")).to_have_text("这次生成被手动停止")
        for index, badge in ((0, "失败"), (1, "已取消")):
            card = _cards(pane).nth(index)
            expect(card.locator(".attempt-badge")).to_have_text(badge)
            expect(card.locator("img")).to_have_count(0)
            expect(card.locator(".attempt-icon")).to_be_visible()
            box = card.locator(".attempt-icon").bounding_box()
            assert box and box["width"] > 0 and box["height"] > 0
        page.reload()  # still visible, still explained, after a reload
        expect(_cards(pane)).to_have_count(2)
        expect(_cards(pane).nth(0).locator(".attempt-reason")).to_have_text("内存不足，生成被中止")
        expect(_cards(pane).nth(1).locator(".attempt-badge")).to_have_text("已取消")
        expect(_cards(pane).nth(1).locator(".attempt-reason-sub")).to_have_text("这次生成被手动停止")
        expect(_cards(pane).locator("img")).to_have_count(0)
        _check_state(page, "verify-failed-and-cancelled", harness=harness)


def test_ac3_restart_on_the_same_data_root_keeps_sessions_attempts_and_images(page, tmp_path):
    """AC-3 on the harness: close every service, relaunch on the same data root."""
    with _harness(tmp_path, [fast_media_steps(), fast_media_steps(), fast_media_steps()]) as harness:
        pane = _open(page, harness)
        _generate(pane, "重启：甲一")
        _settled(pane, 1)
        _generate(pane, "重启：甲二")
        _settled(pane, 2)
        pane.locator("[data-image-session-new]").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(2)
        _generate(pane, "重启：乙一")
        _settled(pane, 1)
        listing = _get(page, harness, "/api/image-sessions")
        full = {s["id"]: _session(page, harness, s["id"]) for s in listing}

    with _harness(tmp_path) as harness:
        pane = _open(page, harness)
        assert _get(page, harness, "/api/image-sessions") == listing
        for session_id, before in full.items():
            assert _session(page, harness, session_id) == before
            pane.locator(f"{SESSION_ITEMS}[data-session-id='{session_id}']").click()
            expect(_cards(pane)).to_have_count(len(before["attempts"]))
            for index in range(len(before["attempts"])):
                expect(_cards(pane).nth(index)).to_have_attribute("data-attempt-status", "done")
            page.wait_for_function(
                "() => [...document.querySelectorAll('#pane-image .attempt-thumb img')].every((i) => i.complete && i.naturalWidth > 0)")


def test_first_entry_without_sessions_creates_exactly_one(page, tmp_path):
    """D-62: no 「请先新建」 — one empty 新会话 is made and selected, and only once."""
    with _harness(tmp_path) as harness:
        assert not harness.roots.image_sessions_dir.exists() or not any(harness.roots.image_sessions_dir.iterdir())
        pane = _open(page, harness)
        expect(pane.locator(SESSION_ITEMS)).to_have_count(1)
        expect(pane.locator(CURRENT_ITEM).locator(".session-title")).to_have_text("新会话")
        expect(pane.locator("[data-image-empty]")).to_contain_text("还没有图片")
        expect(pane).not_to_contain_text("请先")
        # The quoted action names in the hint never break across lines (N-07), at either width.
        for width, height in VIEWPORTS.values():
            page.set_viewport_size({"width": width, "height": height})
            names = page.evaluate("""() => [...document.querySelectorAll('#pane-image [data-image-empty] .keep-together')]
                .map((n) => ({text: n.textContent, lines: new Set([...n.getClientRects()].map((r) => Math.round(r.top))).size}))""")
            assert [n["text"] for n in names] == ["「生成图片」", "「在这张基础上改」", "「换个构图」"], names
            assert all(n["lines"] == 1 for n in names), (width, names)
        page.reload()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(1)
        assert len(_get(page, harness, "/api/image-sessions")) == 1


def test_runtime_unavailable_blocks_generation_with_its_reason(page, tmp_path):
    """§7.6: model present but no MLX runtime — the button is disabled and says why."""
    with _harness(tmp_path, image_runtime=False) as harness:
        pane = _open(page, harness)
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        hint = pane.locator("[data-image-hint-text]")
        expect(hint).not_to_have_text("")
        expect(hint).not_to_contain_text("正在检查")
        capability = _get(page, harness, "/api/capabilities").get("image_runtime", {})
        assert capability.get("present") is False, capability
        expected = capability.get("detail") or "图片 MLX 运行环境不可用，请检查服务或应用安装"
        expect(hint).to_have_text(expected)
        _check_state(page, "runtime-unavailable", harness=harness)


def test_running_in_one_session_while_viewing_another_that_has_images(page, tmp_path):
    """running-other-session with its stated precondition: B already has a finished attempt."""
    with _harness(tmp_path, [fast_media_steps(), default_media_steps()]) as harness:
        pane = _open(page, harness)
        session_b = _current_id(pane)
        _generate(pane, "乙会话：已完成的一张")
        _settled(pane, 1)
        pane.locator("[data-image-session-new]").click()
        expect(pane.locator(SESSION_ITEMS)).to_have_count(2)
        session_a = _current_id(pane)
        _generate(pane, "甲会话：正在生成")
        expect(_cards(pane).first).to_have_attribute("data-attempt-status", "running")
        pane.locator(f"{SESSION_ITEMS}[data-session-id='{session_b}']").click()
        expect(pane.locator(CURRENT_ITEM)).to_have_attribute("data-session-id", session_b)
        expect(_cards(pane)).to_have_count(1)
        card = _cards(pane).first
        expect(card).to_have_attribute("data-attempt-status", "done")
        expect(card).to_have_attribute("aria-expanded", "true")
        expect(pane.locator("[data-image-timeline] .attempt[data-attempt-status='running']")).to_have_count(0)
        expect(pane.locator(f"{SESSION_ITEMS}[data-session-id='{session_a}'] [data-session-running]")).to_have_text("生成中")
        expect(pane.locator("[data-image-hint-text]")).to_have_text("「甲会话：正在生成」正在生成图片")
        expect(pane.locator("[data-image-return]")).to_be_visible()
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(card.get_by_role("button", name="换个构图")).to_be_disabled()
        expect(card.get_by_role("button", name="在这张基础上改")).to_be_enabled()
        _check_state(page, "running-other-session", harness=harness)
        harness.media_script.step()
        harness.media_script.step()
        expect(pane.locator("[data-image-start]")).to_be_enabled(timeout=15_000)
        assert [a["params"]["prompt"] for a in _session(page, harness, session_b)["attempts"]] == ["乙会话：已完成的一张"]


def test_model_and_runtime_both_missing_names_the_runtime_first(page, tmp_path):
    """§7.6 priority when neither the MLX runtime nor the model is there: the runtime reason wins.
    (test_image_flow's first-entry test now keeps the runtime so its model-missing capture meets
    its precondition; this keeps the both-missing case covered.)"""
    with launch_test_harness(tmp_path) as harness:
        pane = _open(page, harness)
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-model]")).to_contain_text("尚未安装")
        capability = _get(page, harness, "/api/capabilities").get("image_runtime", {})
        assert capability.get("present") is False, capability
        expected = capability.get("detail") or "图片 MLX 运行环境不可用，请检查服务或应用安装"
        expect(pane.locator("[data-image-hint-text]")).to_have_text(expected)


def test_model_missing_with_runtime_present_names_the_model(page, tmp_path):
    """model-missing with its stated precondition: the MLX runtime is there, the model is not."""
    with launch_test_harness(tmp_path, image_runtime=True) as harness:
        pane = _open(page, harness)
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-model]")).to_contain_text("尚未安装")
        expect(pane.locator("[data-image-hint-text]")).to_have_text("尚未安装图片模型，请到「资源」页下载")
        _check_state(page, "model-missing", harness=harness)


def test_action_buttons_of_the_settled_attempt_are_in_view_at_900x700(page, tmp_path):
    """AC-7 / D-71 / D-78: in a 900×700 window, once an attempt settles the timeline sits at its
    bottom, so the expanded card's two action buttons are inside the timeline viewport."""
    page.set_viewport_size({"width": 900, "height": 700})
    with _harness(tmp_path, [fast_media_steps() for _ in range(3)]) as harness:
        pane = _open(page, harness)
        for index in range(3):
            _generate(pane, f"窄窗第 {index + 1} 张")
            _settled(pane, index + 1)
            page.wait_for_function(
                "() => [...document.querySelectorAll('#pane-image img')].every((i) => i.complete)")
            page.wait_for_timeout(500)
            geometry = page.evaluate("""() => {
              const timeline = document.querySelector('#pane-image .image-timeline').getBoundingClientRect();
              return [...document.querySelectorAll('#pane-image .attempt[aria-expanded=true] .attempt-actions button')]
                .map((b) => { const r = b.getBoundingClientRect();
                  return {text: b.innerText, top: r.top, bottom: r.bottom, timeline_bottom: timeline.bottom}; });
            }""")
            assert len(geometry) == 2, geometry
            hidden = [g for g in geometry if g["bottom"] > g["timeline_bottom"] + 1]
            assert not hidden, (f"attempt {index + 1}: action buttons below the timeline viewport", geometry)
        # A window that shrinks keeps the expanded card's actions in view (re-pinned on resize).
        page.set_viewport_size({"width": 900, "height": 620})
        _assert_expanded_card_in_view(page, "after shrinking the window to 900×620")


THUMB = 96  # D-73: the collapsed card's thumbnail box
IMAGE_FLOOR = 2 * THUMB  # B-01: the expanded 大图 must be really bigger than a thumbnail


def _expanded_geometry(page):
    """Rects of the expanded card, its header, large image, header thumbnail and two actions, and of
    the timeline (with its inner height, padding excluded)."""
    return page.evaluate("""() => {
      const box = (node) => { if (!node) return null; const r = node.getBoundingClientRect();
        return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, height: r.height}; };
      const timeline = document.querySelector('#pane-image .image-timeline');
      const style = getComputedStyle(timeline);
      const card = timeline.querySelector('.attempt[aria-expanded=true]');
      const image = card?.querySelector('.attempt-image');
      return {
        timeline: box(timeline),
        timeline_inner: timeline.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom),
        card: box(card), label: box(card?.querySelector('.attempt-label')),
        thumb: box(card?.querySelector('.attempt-thumb')),
        image: box(image), image_complete: image ? image.complete && image.naturalWidth > 0 : null,
        image_natural: image ? image.naturalHeight : null, vh60: innerHeight * 0.6,
        buttons: [...(card?.querySelectorAll('.attempt-actions button') ?? [])].map(box),
      };
    }""")


def _assert_expanded_card_in_view(page, when, settle_ms=2_000):
    """The expanded card's large image and both actions are inside the timeline viewport, and so is
    its header whenever the whole card fits. The large image is never shrunk below IMAGE_FLOOR (or
    60vh / its own size when those are smaller) to make the header fit (B-01): when card and floor
    do not both fit, the header is the part that scrolls away. The pane re-fits and re-pins on image
    load and on its ResizeObserver, so poll until settled."""
    page.wait_for_function(
        "() => [...document.querySelectorAll('#pane-image .attempt-image')].every((i) => i.complete)")
    deadline = time.monotonic() + settle_ms / 1000
    while True:
        g = _expanded_geometry(page)
        top, bottom = g["timeline"]["top"] - 1, g["timeline"]["bottom"] + 1
        fits = g["card"] is not None and g["card"]["height"] <= g["timeline_inner"] + 1
        parts = {"image": g["image"], **{f"button{i}": b for i, b in enumerate(g["buttons"])}}
        if fits:
            parts["label"] = g["label"]
        outside = {name: r for name, r in parts.items() if r is not None and (r["top"] < top or r["bottom"] > bottom)}
        floor = min(IMAGE_FLOOR, g["vh60"], g["image_natural"] or IMAGE_FLOOR)
        small = g["image"] is not None and g["image"]["height"] < floor - 1
        if (not outside and not small and len(g["buttons"]) == 2) or time.monotonic() > deadline:
            break
        page.wait_for_timeout(100)
    assert len(g["buttons"]) == 2, (when, g)
    assert not outside, (when, "expanded card's image/actions (and header when it fits) not inside the timeline viewport",
                         outside, g["timeline"])
    assert not small, (when, f"expanded 大图 shrunk below {floor}px", g["image"], g)
    if g["image"] is not None:
        assert g["thumb"] is None, (when, "expanded card repeats the header thumbnail above its large image", g)
    return g


def test_selected_attempt_with_a_full_size_image_shows_header_image_and_actions_together(page, tmp_path):
    """AC-7 / D-72 / D-74: the harness writes the image at its declared 1024×1024, as the real model
    does, and selecting an earlier attempt shows its header, whole large image and both actions at
    once — at 1280×800 and at 900×700. After 「在这张基础上改」 the clicked button is still in view."""
    for name, (width, height) in VIEWPORTS.items():
        page.set_viewport_size({"width": width, "height": height})
        with _harness(tmp_path / name, [fast_media_steps() for _ in range(3)]) as harness:
            pane = _open(page, harness)
            for index in range(3):
                _generate(pane, f"大图第 {index + 1} 张：海边灯塔，黄昏，水彩画风")
                _settled(pane, index + 1)
            g = _assert_expanded_card_in_view(page, f"{name}: last attempt after it settled")
            assert g["image_complete"] and g["image"]["height"] >= IMAGE_FLOOR, (name, g)
            assert g["card"]["height"] <= g["timeline_inner"] + 1, (name, "whole card should fit here", g)

            first = _cards(pane).nth(0)
            first.click()
            expect(first).to_have_attribute("aria-expanded", "true")
            g = _assert_expanded_card_in_view(page, f"{name}: earlier attempt selected")
            assert g["image_complete"] and g["image"]["height"] >= IMAGE_FLOOR, (name, g)
            assert g["card"]["height"] <= g["timeline_inner"] + 1, (name, "whole card should fit here", g)

            first.get_by_role("button", name="在这张基础上改").click()
            expect(pane.locator("[data-image-refine-text]")).to_have_text("沿用第 1 次的构图")
            _assert_expanded_card_in_view(page, f"{name}: after 在这张基础上改 (composer grew)")
            _check_state(page, "verify-selected-full-size", harness=harness, viewports=(name,))


def test_session_list_gives_the_running_title_its_room_and_spaces_the_new_button(page, tmp_path):
    """D-77 / AC-7 (review N-02, N-03): the 生成中 mark takes room from the title, but the hidden
    改名/删除 buttons do not — a short title next to 生成中 is shown whole, at 1280×800 and 900×700.
    The 新会话 button does not touch the first session item. Hovering an item still reveals both
    buttons, and they do not cover the title."""
    for name, (width, height) in VIEWPORTS.items():
        page.set_viewport_size({"width": width, "height": height})
        with _harness(tmp_path / name, [default_media_steps()]) as harness:
            pane = _open(page, harness)
            _generate(pane, "会失败的港口")  # 6 characters: fits beside 生成中 in a 248px column
            expect(_cards(pane).first).to_have_attribute("data-attempt-status", "running")
            item = pane.locator(CURRENT_ITEM)
            expect(item.locator("[data-session-running]")).to_have_text("生成中")
            page.mouse.move(width - 5, height - 5)  # not over the list
            item.evaluate("(li) => document.activeElement?.blur()")
            geo = item.evaluate("""(li) => {
              const t = li.querySelector('.session-title'), a = li.querySelector('.session-actions');
              const nb = document.querySelector('#pane-image [data-image-session-new]').getBoundingClientRect();
              const first = document.querySelector('#pane-image [data-image-session-list] li').getBoundingClientRect();
              return {text: t.textContent, scroll: t.scrollWidth, client: t.clientWidth,
                      actions_width: a.getBoundingClientRect().width, gap: first.top - nb.bottom};
            }""")
            assert geo["scroll"] <= geo["client"], (name, "title cut beside 生成中 while buttons are hidden", geo)
            assert geo["gap"] >= 8, (name, "新会话 button touches the first session item", geo)
            item.hover()
            expect(item.get_by_role("button", name="改名")).to_be_visible()
            expect(item.get_by_role("button", name=re.compile("^删除会话："))).to_be_visible()
            hovered = item.evaluate("""(li) => {
              const r = (n) => n.getBoundingClientRect();
              const row = r(li.querySelector('.session-title-row')), acts = r(li.querySelector('.session-actions'));
              return {row_right: row.right, actions_left: acts.left};
            }""")
            assert hovered["row_right"] <= hovered["actions_left"] + 0.5, (name, "buttons overlap the title", hovered)
            harness.media_script.step()
            harness.media_script.step()
            expect(pane.locator("[data-image-start]")).to_be_enabled(timeout=15_000)
