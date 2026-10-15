"""视频、图片、音乐页在矮窗口下的上下排布（视觉基线 layout #5；cross-exam 2026-10-14 缺口 G4–G9、J5-squeezed）。

规则原文：任何窗口高度（最矮 600）下，一张结果卡片的标题、媒体与操作行都能在结果区内完整看到，不被输入区遮挡、
不被结果区硬边截断；输入内容超长时只在输入框内滚动，页面不出现第二条滚动条。

每个用例先真生成一次（脚本化执行器写小文件），再往提示词框（音乐是歌词框）里填 600 字，然后量：
结果区之外只有提示词框一个滚动区（输入区不整块滚动，整页不滚动）；方式行（视频）与主按钮完整可见；输入区不出窗口；结果卡片滚到顶后
标题行、媒体、操作行都在结果区可视范围内。截图写到 $LMD_SHORT_WINDOW_SHOTS（未设置时写 tmp_path）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.fakes import gradient_png
from desk.testing.scripts import MediaScript, fast_media_steps

LONG = ("夜色里的海港城市，雨后街道反射霓虹灯，镜头缓慢推进，远处有渔船汽笛声与细雨声，" * 20)[:600]
PAGES = {
    "video": {"model": "h3", "input": "[data-video-prompt]"},
    "image": {"model": "qwen-image", "input": "[data-image-prompt]"},
    "music": {"model": "music3", "input": "[data-music-lyrics]"},
}
SIZES = [(900, 600), (1400, 851), (2560, 1440)]
# 结果卡片里画面（视频、图片）的最小可用高度：放不下时输入区按既定顺序让位，而不是把画面压没（用户 2026-10-16 拍板）。
MIN_MEDIA = 140

# 可见元素里内容超出、能滚动的那些（含整页）。结果区（时间线）本来就是可滚动的结果列表——卡片的完整提示词与
# 参数在操作行下面，滚下去才看得到——不算「第二条滚动条」；会话列表只有一个会话时不滚动，所以不必排除。
SCROLLERS = """(pane) => {
  const root = document.querySelector('#pane-' + pane);
  const found = [...root.querySelectorAll('*')].filter((n) => {
    if (n.classList.contains('image-timeline')) return false;
    if (!n.getClientRects().length) return false;
    const cs = getComputedStyle(n);
    return /(auto|scroll)/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 1;
  }).map((n) => n.getAttribute('aria-label') || n.className || n.tagName);
  if (document.scrollingElement.scrollHeight > innerHeight + 1) found.push('document');
  return found;
}"""

# 量展开那张卡片的标题行、媒体、操作行是否都落在结果区的可视范围里；scroll 为真时先把卡片滚到结果区顶端。
CARD_FIT = """([pane, scroll]) => {
  const root = document.querySelector('#pane-' + pane);
  const tl = root.querySelector('.image-timeline');
  const card = tl.querySelector('.attempt[aria-expanded=true]');
  const pad = parseFloat(getComputedStyle(tl).paddingTop) || 0;
  if (scroll) tl.scrollTop += card.getBoundingClientRect().top - tl.getBoundingClientRect().top - pad;
  const box = tl.getBoundingClientRect();
  const view = {top: box.top + tl.clientTop, bottom: box.top + tl.clientTop + tl.clientHeight};
  const part = (sel) => {
    const n = card.querySelector(sel);
    if (!n) return null;
    const r = n.getBoundingClientRect();
    return {top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height)};
  };
  return {view: {top: Math.round(view.top), bottom: Math.round(view.bottom)},
          title: part('.attempt-row'), media: part('video, img.attempt-image, audio'), actions: part('.attempt-actions')};
}"""

# 元素完整在窗口里、且中心点与上沿都没被别的元素盖住（elementFromPoint 落在它自己或它的子孙上）。
VISIBLE = """(sel) => {
  const n = document.querySelector(sel);
  const r = n.getBoundingClientRect();
  const mine = (x, y) => { const hit = document.elementFromPoint(x, y); return !!hit && (hit === n || n.contains(hit)); };
  return {top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height),
          inside: r.top >= 0 && r.bottom <= innerHeight && r.height > 0,
          uncovered: mine(r.left + r.width / 2, r.top + r.height / 2) && mine(r.left + r.width / 2, r.top + 3)};
}"""


def _shot(page, tmp_path, name):
    folder = Path(os.environ.get("LMD_SHORT_WINDOW_SHOTS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f"{name}.png"))


def _harness(tmp_path, kind):
    return launch_test_harness(tmp_path, model_states={PAGES[kind]["model"]: "present"}, image_runtime=kind == "image",
                               media_script=MediaScript([fast_media_steps()]))


def _generate_one(page, harness, kind):
    page.goto(harness.base_url + f"#tab={kind}")
    pane = page.locator(f"#pane-{kind}")
    if kind == "music":
        pane.locator("[data-music-caption]").fill("温柔的民谣")
    if kind == "image":  # 竖幅图最占高度
        pane.locator("[data-image-advanced] summary").click()
        pane.locator("[data-image-width]").fill("512")
        pane.locator("[data-image-height]").fill("1536")
        pane.locator("[data-image-advanced] summary").click()
    pane.locator(PAGES[kind]["input"]).fill("短提示")
    pane.locator(f"[data-{kind}-start]").click()
    expect(pane.locator(".attempt").first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
    return pane


def _assert_layout(page, kind, label):
    page.wait_for_timeout(300)  # 让 ResizeObserver 的下一帧调整落定
    scrollers = page.evaluate(SCROLLERS, kind)
    expected = [page.locator(PAGES[kind]["input"]).get_attribute("aria-label")]
    assert scrollers == expected, f"{label}：结果区之外的滚动区应只有提示词框，实际 {scrollers}"

    composer = page.evaluate(VISIBLE, f"#pane-{kind} .image-composer")
    assert composer["bottom"] <= page.viewport_size["height"], f"{label}：输入区出了窗口 {composer}"
    start = page.evaluate(VISIBLE, f"[data-{kind}-start]")
    assert start["inside"] and start["uncovered"], f"{label}：主按钮不完整可见 {start}"
    if kind == "video":
        mode = page.evaluate(VISIBLE, "#pane-video .video-mode")
        assert mode["inside"] and mode["uncovered"], f"{label}：「生成方式」一行不完整可见 {mode}"

    # 先看页面自己停在哪（贴底、落定之后不需要用户去滚），再看用户把卡片滚到顶时。
    for scroll in (False, True):
        fit = page.evaluate(CARD_FIT, [kind, scroll])
        view = fit["view"]
        for part in ("title", "media", "actions"):
            box = fit[part]
            assert box, f"{label}：卡片里找不到 {part}"
            assert view["top"] <= box["top"] and box["bottom"] <= view["bottom"], (
                f"{label}{'（滚到卡片顶）' if scroll else ''}：卡片的 {part} {box} 不在结果区可视范围 {view} 内")
        least = 48 if kind == "music" else MIN_MEDIA - 1
        assert fit["media"]["height"] >= least, f"{label}：媒体被压得太小 {fit['media']}"


@pytest.mark.parametrize("kind", list(PAGES))
@pytest.mark.parametrize("width,height", SIZES)
def test_long_input_scrolls_only_in_the_prompt_and_a_card_stays_whole(page, tmp_path, kind, width, height):
    with _harness(tmp_path, kind) as harness:
        page.set_viewport_size({"width": width, "height": height})
        pane = _generate_one(page, harness, kind)
        pane.locator(PAGES[kind]["input"]).fill(LONG)
        _assert_layout(page, kind, f"{kind} {width}×{height} 长输入")
        _shot(page, tmp_path, f"{kind}-{width}x{height}-long")


@pytest.mark.parametrize("kind", list(PAGES))
def test_open_advanced_params_keep_the_layout_at_the_minimum_window(page, tmp_path, kind):
    """矮窗口里展开「高级参数」是输入区上方的浮层：结果区高度不变，输入区不出窗口，按 Esc 收起。"""
    with _harness(tmp_path, kind) as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, kind)
        pane.locator(PAGES[kind]["input"]).fill(LONG)
        page.wait_for_timeout(300)
        before = page.evaluate("(k) => document.querySelector('#pane-' + k + ' .image-timeline').clientHeight", kind)
        pane.locator(f"[data-{kind}-advanced] summary").click()
        page.wait_for_timeout(300)
        after = page.evaluate("(k) => document.querySelector('#pane-' + k + ' .image-timeline').clientHeight", kind)
        assert after == before, f"{kind}：展开高级参数后结果区从 {before}px 变成 {after}px"
        body = page.evaluate(VISIBLE, f"[data-{kind}-advanced] .advanced-body")
        assert body["inside"] and body["uncovered"], f"{kind}：高级参数浮层不完整可见 {body}"
        _shot(page, tmp_path, f"{kind}-900x600-advanced")
        page.keyboard.press("Escape")
        expect(pane.locator(f"[data-{kind}-advanced]")).not_to_have_attribute("open", "")
        _assert_layout(page, kind, f"{kind} 900×600 收起高级参数后")


def test_first_and_last_frames_fold_into_slots_at_the_minimum_window(page, tmp_path):
    """图生视频选了首帧、尾帧：矮窗口里素材收成方式行里的两个槽位，点槽位弹出浮层更换；结果卡片仍整张可见。"""
    frame = tmp_path / "frame.png"
    frame.write_bytes(gradient_png(512, 288))
    with _harness(tmp_path, "video") as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, "video")
        pane.locator("[data-video-mode]").select_option("image")
        pane.locator("[data-video-first-upload]").set_input_files(str(frame))
        pane.locator("[data-video-last]").set_input_files(str(frame))
        pane.locator("[data-video-prompt]").fill(LONG)
        slots = pane.locator("[data-video-slot]")
        expect(slots).to_have_count(2)
        expect(slots.nth(0)).to_have_attribute("aria-label", re.compile(r"^首帧："))
        expect(slots.nth(1)).to_have_attribute("aria-label", re.compile(r"^尾帧："))
        expect(slots.nth(0)).to_contain_text("首")
        expect(slots.nth(0).locator("img")).to_be_visible()
        expect(pane.locator("[data-video-first-area]")).not_to_be_visible()
        _assert_layout(page, "video", "图生视频首尾帧 900×600")
        _shot(page, tmp_path, "video-900x600-frames")

        slots.nth(1).click()
        area = pane.locator("[data-video-last-area]")
        expect(area).to_be_visible()
        assert page.evaluate(VISIBLE, "[data-video-last-area]")["inside"]
        expect(area.locator("[data-video-clear-last]")).to_be_visible()
        _shot(page, tmp_path, "video-900x600-last-frame-open")
        page.keyboard.press("Escape")
        expect(area).not_to_be_visible()

        page.set_viewport_size({"width": 1400, "height": 1000})  # 高窗口：素材照旧展开，没有槽位
        expect(pane.locator("[data-video-first-area]")).to_be_visible()
        expect(slots.first).not_to_be_visible()


@pytest.mark.parametrize("width,height", [(900, 600), (1400, 851)])
def test_frames_long_names_and_open_advanced_still_leave_a_whole_card(page, tmp_path, width, height):
    """recheck 2026-10-15（WKWebView）：图生视频选了长文件名的首帧、尾帧，又展开高级参数、填 600 字时，1400×851 下
    输入区曾冲出窗口、结果区只剩 20px，900×600 下高级参数浮层的上沿钻到标签栏下面。"""
    first = tmp_path / ("synthetic-first-frame-morning-lake-with-mist-and-heron-standing-in-reeds-" * 3 + "1280x720.png")
    last = tmp_path / ("synthetic-last-frame-morning-lake-heron-flying-away-over-golden-reeds-" * 3 + "1280x720.png")
    first.write_bytes(gradient_png(1280, 720))
    last.write_bytes(gradient_png(1280, 720))
    with _harness(tmp_path, "video") as harness:
        page.set_viewport_size({"width": width, "height": height})
        pane = _generate_one(page, harness, "video")
        pane.locator("[data-video-mode]").select_option("image")
        pane.locator("[data-video-first-upload]").set_input_files(str(first))
        pane.locator("[data-video-last]").set_input_files(str(last))
        pane.locator("[data-video-prompt]").fill(LONG)
        pane.locator("[data-video-advanced] summary").click()
        _assert_popover(page, "video", "[data-video-advanced] .advanced-body", f"{width}×{height} 首尾帧、展开高级参数")
        _shot(page, tmp_path, f"video-{width}x{height}-frames-advanced")
        page.keyboard.press("Escape")
        _assert_layout(page, "video", f"长文件名首尾帧 {width}×{height}")


def test_a_long_prompt_under_the_card_does_not_shrink_the_image(page, tmp_path):
    """recheck 2026-10-15：竖幅图的完整提示词有 600 字时，1400×851 下大图曾被压到 193px（结果区有 568px）——
    提示词与参数占得多时留在操作行下面滚着看，不再为了整张卡片放得下去缩大图。"""
    with _harness(tmp_path, "image") as harness:
        page.set_viewport_size({"width": 1400, "height": 851})
        page.goto(harness.base_url + "#tab=image")
        pane = page.locator("#pane-image")
        pane.locator("[data-image-advanced] summary").click()
        pane.locator("[data-image-width]").fill("512")
        pane.locator("[data-image-height]").fill("1536")
        pane.locator("[data-image-advanced] summary").click()
        pane.locator("[data-image-prompt]").fill(LONG)
        pane.locator("[data-image-start]").click()
        expect(pane.locator(".attempt").first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        pane.locator("[data-image-prompt]").fill("")
        page.wait_for_timeout(500)
        fit = page.evaluate(CARD_FIT, ["image", False])
        assert fit["media"]["height"] >= 300, f"大图只有 {fit['media']}，结果区 {fit['view']}"
        for part in ("title", "media", "actions"):
            assert fit["view"]["top"] <= fit[part]["top"] and fit[part]["bottom"] <= fit["view"]["bottom"], (part, fit)


def test_everything_set_at_once_still_collapses(page, tmp_path):
    """recheck 2026-10-15（WKWebView）：素材、长提示词、展开高级参数在同一刻设好（输入区一下子冲出主列）时，
    收起判定曾把「其余部分」算成负数而不收起，结果区只剩 20px、提示词与主按钮出了窗口。"""
    first = tmp_path / "first.png"
    first.write_bytes(gradient_png(1280, 720))
    with _harness(tmp_path, "video") as harness:
        page.set_viewport_size({"width": 1400, "height": 851})
        pane = _generate_one(page, harness, "video")
        page.set_viewport_size({"width": 900, "height": 600})
        pane.locator("[data-video-mode]").select_option("image")
        pane.locator("[data-video-first-upload]").set_input_files(str(first))
        pane.locator("[data-video-last]").set_input_files(str(first))
        page.evaluate("""(text) => {
          document.querySelector('[data-video-advanced]').open = true;
          const p = document.querySelector('[data-video-prompt]');
          p.value = text; p.dispatchEvent(new Event('input', {bubbles: true}));
        }""", LONG)
        page.wait_for_timeout(300)
        page.keyboard.press("Escape")
        _assert_layout(page, "video", "同一刻设好 900×600")


def test_slots_are_disabled_while_continuing(page, tmp_path):
    """recheck 2026-10-15：接着往下生时首帧、尾帧被锁，矮窗口里的槽位也要禁用变暗，而不是照常亮着。"""
    with _harness(tmp_path, "video") as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, "video")
        pane.locator(".attempt[aria-expanded=true] [data-attempt-continue]").click()
        slots = pane.locator("[data-video-slot]")
        expect(slots.first).to_be_visible()
        for index in range(slots.count()):
            expect(slots.nth(index)).to_be_disabled()
        assert page.evaluate("getComputedStyle(document.querySelector('[data-video-slot]')).opacity") == "0.5"


# 浮层（高级参数、素材块）打开时：浮层完整可见、自己不出滚动条，展开卡片的标题行不被它盖住。
def _assert_popover(page, kind, popover, label):
    page.wait_for_timeout(300)
    body = page.evaluate(VISIBLE, popover)
    assert body["inside"] and body["uncovered"], f"{label}：浮层不完整可见 {body}"
    overflow = page.evaluate("(s) => { const n = document.querySelector(s); return [n.scrollHeight, n.clientHeight]; }", popover)
    assert overflow[0] <= overflow[1] + 1, f"{label}：浮层里内容超出、出了滚动条 {overflow}"
    title = page.evaluate(VISIBLE, f"#pane-{kind} .attempt[aria-expanded=true] .attempt-row")
    assert title["inside"] and title["uncovered"], f"{label}：展开卡片的标题行被浮层盖住或不在可视范围 {title}"
    view = page.evaluate(CARD_FIT, [kind, False])["view"]
    assert view["top"] <= title["top"] and title["bottom"] <= view["bottom"], f"{label}：标题行 {title} 不在结果区 {view} 内"


def test_portrait_image_with_a_base_keeps_a_usable_size(page, tmp_path):
    """recheck 2026-10-15：900×600 下竖幅图带「以第 N 次为底稿」、填 600 字、又展开高级参数时，大图曾缩到约 33×100。"""
    with _harness(tmp_path, "image") as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, "image")
        pane.locator("[data-attempt-refine]").first.click()
        expect(pane.locator("[data-image-refine]")).to_be_visible()
        pane.locator("[data-image-prompt]").fill(LONG)
        _assert_layout(page, "image", "竖幅图带底稿 900×600")
        expect(pane.locator("[data-image-refine]")).to_be_visible()
        pane.locator("[data-image-advanced] summary").click()
        _assert_popover(page, "image", "[data-image-advanced] .advanced-body", "竖幅图带底稿、展开高级参数")
        assert page.evaluate(CARD_FIT, ["image", False])["media"]["height"] >= MIN_MEDIA - 1
        _shot(page, tmp_path, "image-900x600-base-advanced")
        page.keyboard.press("Escape")
        _assert_layout(page, "image", "竖幅图带底稿、收起高级参数后")


@pytest.mark.parametrize("kind", list(PAGES))
def test_open_advanced_params_do_not_cover_the_card_title(page, tmp_path, kind):
    """recheck 2026-10-15：最矮窗口下浮层最高到主列顶端，会盖住结果卡片的标题行。"""
    with _harness(tmp_path, kind) as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, kind)
        pane.locator(PAGES[kind]["input"]).fill(LONG)
        page.wait_for_timeout(300)
        page.evaluate("(k) => { const t = document.querySelector('#pane-' + k + ' .image-timeline'); t.dispatchEvent(new WheelEvent('wheel')); t.scrollTop = t.scrollHeight; }", kind)
        pane.locator(f"[data-{kind}-advanced] summary").click()
        _assert_popover(page, kind, f"[data-{kind}-advanced] .advanced-body", f"{kind} 900×600 展开高级参数")
        _shot(page, tmp_path, f"{kind}-900x600-advanced-title")


MATERIALS = {
    "image": [("firstArea", "[data-video-first-upload]"), ("lastArea", "[data-video-last]")],
    "reference": [("referenceArea", None)],
    "music_ref": [("musicArea", "[data-video-ref-image-upload]")],
}


@pytest.mark.parametrize("mode", list(MATERIALS))
def test_material_popovers_fit_at_the_minimum_window(page, tmp_path, mode):
    """recheck 2026-10-15：900×600 下素材块浮层多出约 33px、出了小滚动条，也会盖住卡片标题行；
    素材收成槽位后画面也要保住最小可用高度。"""
    frame = tmp_path / ("synthetic-frame-morning-lake-with-mist-" * 3 + "1280x720.png")
    frame.write_bytes(gradient_png(1280, 720))
    with _harness(tmp_path, "video") as harness:
        page.set_viewport_size({"width": 900, "height": 600})
        pane = _generate_one(page, harness, "video")
        pane.locator("[data-video-mode]").select_option(mode)
        for _, upload in MATERIALS[mode]:
            if upload:
                pane.locator(upload).set_input_files(str(frame))
        pane.locator("[data-video-prompt]").fill(LONG)
        _assert_layout(page, "video", f"{mode} 素材收起 900×600")
        for area, _ in MATERIALS[mode]:
            pane.locator(f"[data-video-slot={area}]").click()
            _assert_popover(page, "video", f"#pane-video .video-assets.is-popped", f"{mode} 弹出 {area}")
            _shot(page, tmp_path, f"video-900x600-{mode}-{area}")
            page.keyboard.press("Escape")
