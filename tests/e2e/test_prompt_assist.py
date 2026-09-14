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


def test_video_and_music_assist_rows_stay_inside_the_viewport_at_800px(page, tmp_path, audit_violations):
    page.set_viewport_size({"width": 800, "height": 832})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        for tab in ("video", "music"):
            page.locator(f"#tabs [data-tab={tab}]").click()
            page.wait_for_selector(f"[data-{tab}-assist]")
            scroll_width, inner_width = page.evaluate(
                "() => [document.documentElement.scrollWidth, window.innerWidth]"
            )
            assert scroll_width <= inner_width, (tab, scroll_width, inner_width)
    assert audit_violations == []
