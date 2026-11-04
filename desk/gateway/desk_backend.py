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
        return self._llm.chat_completion({**request, "origin": "agent"})

    def chat_stream(self, request: dict):
        # Gateway traffic is external, not recent activity in the desk's chat UI.
        # Keep active_chats accounting, but do not block agent model swaps by
        # falsely marking every gateway request as a recent UI conversation.
        for event in self._llm.chat_stream({**request, "origin": "agent"}):
            if event["type"] == "delta":
                if event["reasoning"] is not None:
                    yield "reasoning", event["reasoning"]
                if event["text"] is not None:
                    yield "content", event["text"]
                if event.get("tool_calls") is not None:
                    yield "tool_calls", event["tool_calls"]
            elif event["type"] == "done":
                yield "finish", event
            else:
                raise RuntimeError(event["message"])
