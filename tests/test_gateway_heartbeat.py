"""Long model silences must not trip API clients' body-idle timers."""
import http.client
import json
import threading

import pytest

from gateway_client import serve
from gateway_fakes import FakeBackend


@pytest.mark.parametrize('path', ['/v1/chat/completions', '/v1/messages'])
def test_heartbeat_arrives_while_model_is_blocked(path):
    release = threading.Event()
    closed = threading.Event()

    class SlowBackend(FakeBackend):
        def chat_stream(self, req):
            try:
                assert release.wait(5), 'test did not release model'
                yield 'content', 'hello'
                yield 'finish', {'finish_reason': 'stop', 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
            finally:
                closed.set()

    with serve(SlowBackend(), sse_heartbeat_seconds=0.02) as port:
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
        try:
            conn.request('POST', path, body=json.dumps({
                'model': 'qwen3-30b', 'stream': True, 'max_tokens': 32,
                'messages': [{'role': 'user', 'content': 'hi'}],
            }), headers={'Content-Type': 'application/json'})
            response = conn.getresponse()
            assert response.status == 200
            # Anthropic may emit message_start before asking the model for data.
            while True:
                line = response.readline()
                assert line, 'stream closed before heartbeat'
                if line == b': keep-alive\n':
                    break
            assert not release.is_set()
            release.set()
            remaining = response.read()
            assert b'hello' in remaining
            assert b'[DONE]' in remaining if path.endswith('completions') else b'message_stop' in remaining
            assert closed.wait(1)
        finally:
            release.set()
            conn.close()
