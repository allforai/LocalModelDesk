"""R-e2e-09: 成品要能拖动播放（Range），访达入口要真存在（reveal）。"""
from desk.testing import launch_test_harness
from desk.testing.seed import TINY_MP4


def test_partial_content_and_reveal(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        name = "h3-range-test.mp4"
        harness.outputs_root.mkdir(parents=True, exist_ok=True)
        (harness.outputs_root / name).write_bytes(TINY_MP4)

        page.goto(harness.base_url)
        page.get_by_role("button", name="素材库").click()
        page.wait_for_selector("[data-lib-list] li")

        found_name = page.evaluate(
            "() => document.querySelector('[data-lib-list] [data-output-name]')?.dataset.outputName"
        )
        assert found_name == name

        response = page.request.get(
            f"{harness.base_url}/api/outputs/{name}", headers={"Range": "bytes=0-0"}
        )
        assert response.status == 206
        assert response.headers["content-range"].startswith("bytes 0-0/")
        assert response.headers["accept-ranges"] == "bytes"

        reveal = page.request.post(f"{harness.base_url}/api/outputs/{name}/reveal")
        assert reveal.status == 200
        assert harness.reveal_calls and harness.reveal_calls[-1][:2] == ["open", "-R"]

    assert audit_violations == []
