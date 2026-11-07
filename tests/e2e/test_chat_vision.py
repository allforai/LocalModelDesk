"""Actual upload, multimodal request and persisted image reload in the browser."""
import json
from playwright.sync_api import expect
from desk.testing import launch_test_harness
from desk.testing.seed import TINY_PNG
from desk.resources.catalog import entry


def test_chat_upload_reaches_transport_and_survives_reload(page, tmp_path, wait_until):
    with launch_test_harness(tmp_path, model_states={"superqwen": "present"}) as h:
        model_dir = h.models_root / entry('superqwen').relpath
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / 'config.json').write_text(json.dumps({'vision_config': {'model_type': 'qwen3_5'}}))
        page.goto(h.base_url)
        pane = page.locator('#pane-chat')
        pane.locator('[data-model-select]').select_option('superqwen')
        pane.get_by_role('button', name='加载', exact=True).click()
        expect(pane.locator('[data-model-state]')).to_contain_text('已加载')
        pane.locator('[data-chat-images]').set_input_files({'name': 'shapes.png', 'mimeType': 'image/png', 'buffer': TINY_PNG})
        expect(pane.locator('[data-chat-image-list] img')).to_have_count(1)
        pane.locator('[data-chat-input]').fill('描述图片')
        with page.expect_request('**/api/llm/chat/stream') as request:
            pane.get_by_role('button', name='发送', exact=True).click()
        blocks = request.value.post_data_json['messages'][-1]['content']
        assert blocks[1]['image_url']['url'].startswith('data:image/png;base64,')
        h.chat_script.run_to_end()
        wait_until(lambda: any(s['messages'] and s['messages'][0].get('images') for s in h.library.list_chat_sessions()))
        page.reload()
        expect(page.locator('.msg-user img')).to_have_count(1)
        assert page.locator('.msg-user img').evaluate('(img) => img.complete && img.naturalWidth > 0')
