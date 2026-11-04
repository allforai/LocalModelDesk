import sys, json
sys.path.insert(0, "tests/e2e")
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright, expect
from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps
tmp = Path(tempfile.mkdtemp())
out = {}
with launch_test_harness(tmp, model_states={"qwen-image": "present"}, image_runtime=True,
                         media_script=MediaScript([fast_media_steps() for _ in range(3)])) as h, sync_playwright() as p:
    b = p.chromium.launch(ignore_default_args=["--hide-scrollbars"])
    page = b.new_page(viewport={"width": 900, "height": 700})
    page.goto(h.base_url + "#tab=image")
    pane = page.locator("#pane-image")
    expect(pane.locator("[data-image-session-list] li[aria-current='true']")).to_have_count(1)
    for i in range(3):
        pane.locator("[data-image-prompt]").fill(f"窄窗第{i+1}张")
        expect(pane.locator("[data-image-start]")).to_be_enabled()
        pane.locator("[data-image-start]").click()
        expect(pane.locator(".attempt")).to_have_count(i + 1)
        expect(pane.locator(".attempt").nth(i)).to_have_attribute("data-attempt-status", "done", timeout=15000)
        page.wait_for_timeout(800)
        out[f"after_{i+1}"] = page.evaluate("""() => {
          const tl = document.querySelector('#pane-image .image-timeline').getBoundingClientRect();
          const scroller = document.querySelector('#pane-image .image-timeline');
          const btns = [...document.querySelectorAll('#pane-image .attempt[aria-expanded=true] .attempt-actions button')].map((b) => { const r = b.getBoundingClientRect(); return {text: b.innerText, top: r.top, bottom: r.bottom}; });
          return {timeline: {top: tl.top, bottom: tl.bottom}, scrollTop: scroller.scrollTop, scrollHeight: scroller.scrollHeight, clientHeight: scroller.clientHeight, buttons: btns};
        }""")
    page.screenshot(path=str(Path(sys.argv[1]) / "narrow-native.png"))
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
