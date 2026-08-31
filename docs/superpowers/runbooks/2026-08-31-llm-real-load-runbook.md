# LLM real-load acceptance

This is a human-only reality gate. Do not run it from an implementation agent.

1. Start LocalModelDesk and confirm one chat model is reported as complete.
2. Load it and observe `loading` then `loaded`, with resident-memory growth consistent with the model.
3. Send one prompt. Confirm tokens stream incrementally and reasoning, when present, is separated from final text.
4. Confirm `lsof -tiTCP:8767 -sTCP:LISTEN` reports the resident server.
5. Unload it. Confirm state returns to idle, port 8767 has no listener, and memory falls.
6. Record timestamps, model id, observations, and command output in
   `docs/superpowers/runs/2026-08-31-localmodeldesk-app/human-acceptance/llm-real-load.md`.
7. Only when every check passes, add a standalone line: `VERDICT: PASS`.
