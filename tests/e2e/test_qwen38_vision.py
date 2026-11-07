"""UI to service transport only; fake weights and fake model answers."""
from playwright.sync_api import expect

from desk.resources.manifest import Manifest, ManifestFile, ManifestStore
from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done
from desk.testing.seed import TINY_PNG


def test_image_chat_and_runtime_setting(page, tmp_path, monkeypatch, wait_until):
    original = ManifestStore.get

    def tiny_manifest(self, model, refresh=False):
        if model.key == 'qwen38-flash-next':
            return Manifest(model.hf_repo, (ManifestFile('weights/a.safetensors', 600),
                                            ManifestFile('weights/b.safetensors', 400)), 'now', 'mock')
        return original(self, model, refresh)

    monkeypatch.setattr(ManifestStore, 'get', tiny_manifest)
    script = ChatScript([Delta(content='截图中有代码'), Done(usage={'prompt_tokens': 20, 'completion_tokens': 5, 'total_tokens': 25})])
    with launch_test_harness(tmp_path, model_states={'qwen38-flash-next': 'present'}, chat_script=script) as harness:
        page.goto(harness.base_url)
        pane = page.locator('#pane-chat')
        pane.locator('[data-model-select]').select_option('qwen38-flash-next')
        pane.get_by_role('button', name='加载', exact=True).click()
        expect(pane.locator('[data-model-state]')).to_contain_text('已加载')
        pane.locator('[data-chat-images]').set_input_files({'name': 'code.png', 'mimeType': 'image/png', 'buffer': TINY_PNG})
        expect(pane.locator('[data-chat-image-list] img')).to_have_count(1)
        pane.locator('[data-chat-input]').fill('查看这张代码图片')
        pane.get_by_role('button', name='发送', exact=True).click()
        expect(pane.locator('.msg-assistant .md').last).to_have_text('截图中有代码')
        assert script.requests[0]['messages'][-1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
        wait_until(lambda: harness.library.list_chat_sessions()[0]['messages'][0].get('images'))
        page.reload()
        expect(pane.locator('.msg-user img')).to_have_count(1)
        page.locator('[data-open-settings]').click()
        page.locator('[data-settings-omlx-python]').fill('/tmp/review-only-omlx/bin/python')
        page.locator('[data-settings-omlx-save]').click()
        expect(page.locator('[data-settings-error]')).to_contain_text('路径已保存')
        page.reload()
        page.locator('[data-open-settings]').click()
        expect(page.locator('[data-settings-omlx-python]')).to_have_value('/tmp/review-only-omlx/bin/python')
