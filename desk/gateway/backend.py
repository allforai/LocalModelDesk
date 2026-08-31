"""GatewayBackend's injected, read-only dependency contract."""
from __future__ import annotations

from typing import Iterator, Protocol


class GatewayBackend(Protocol):
    """Gateway-facing view of LLM and arbiter state and inference operations.

    Deliberately excludes load, unload, acquire, and release operations so the
    gateway cannot implicitly change heavy-work ownership.
    """

    def llm_status(self) -> dict:
        """Return ``{state, loaded}`` from api:llmStatus."""
        ...

    def desk_state(self) -> dict:
        """Return the data:deskState projection."""
        ...

    def can_start_heavy(self, kind: str) -> dict:
        """Return the api:canStartHeavy result for ``kind``."""
        ...

    def chat_completion(self, req: dict) -> dict:
        """Run a non-streaming chat completion."""
        ...

    def chat_stream(self, req: dict) -> Iterator[tuple]:
        """Return a stream of chat events."""
        ...
