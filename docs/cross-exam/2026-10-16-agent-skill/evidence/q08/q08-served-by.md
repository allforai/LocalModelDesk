# q08 served-by
- Requests target: 127.0.0.1:8766
- Serving process: PID 31005 python3.13 -m desk, inside dist/LocalModelDesk.app (app PID 30967); already running, not touched.
- Test condition (not a mock layer): sandbox-exec -f q08.sb with profile `(version 1)(allow default)(deny network*)`, applied only to the sandbox runs (steps 01, 02).
  - Affected: the lmdesk process under it could not open network connections; the kernel denied them. lmdesk printed its own error and exited 6.
  - Not affected: the desk process (outside the sandbox), the control runs (no sandbox), and any response content. No fake data or stub replaced any backend response.
- Mock layers: none. No MSW, json-server, stub switch, or env override.
