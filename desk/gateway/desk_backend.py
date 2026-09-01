"""Gateway projection over the production Desk services."""
from __future__ import annotations


class DeskGatewayBackend:
    """Expose the OpenAI/Anthropic gateway's narrow backend contract."""

    def __init__(self, llm, arbiter):
        self._llm = llm
        self._arbiter = arbiter

    def llm_status(self) -> dict:
        status = self._llm.status()
        state = status["state"]
        loaded = status["loaded_model"]
        if loaded is not None:
            loaded = {**loaded, "loaded_at": state["loaded_at"]}
        return {"state": state["status"], "loaded": loaded}

    def desk_state(self) -> dict:
        return self._arbiter.desk_state()

    def can_start_heavy(self, kind: str) -> dict:
        return self._arbiter.can_start_heavy(kind)

    def chat_completion(self, request: dict) -> dict:
        return self._llm.chat_completion(request)

    def chat_stream(self, request: dict):
        for event in self._llm.chat_stream(request):
            if event["type"] == "delta":
                if event["reasoning"] is not None:
                    yield "reasoning", event["reasoning"]
                if event["text"] is not None:
                    yield "content", event["text"]
            elif event["type"] == "done":
                yield "finish", event
            else:
                raise RuntimeError(event["message"])
