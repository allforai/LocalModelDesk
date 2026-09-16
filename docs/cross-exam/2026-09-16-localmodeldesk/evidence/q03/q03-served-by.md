# q03 served-by

- probe port (GET /readback, /window, /eval, /snapshot): 127.0.0.1:18780 -> shell process
  `/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk` (own instance, pid 30903)
- desk shell/backend port (LMD_SHELL_PORT): 127.0.0.1:18771
  - before kill: python3.13 -s -m desk, pid 30910 (child of 30903)
  - confirmed via `lsof -i :18771` before killing: listener was pid 30910
  - after `kill 30910`: port closed (`lsof -i :18771` empty)
  - after clicking 重试 in the UI: NEW listener on 127.0.0.1:18771, pid 36017
    (confirmed via `lsof -i :18771` and `ps aux`), i.e. the shell app (pid 30903)
    respawned a fresh `python -m desk` child process.
- mock_layers: none checked/applicable (native macOS app hitting its own local backend, no browser/service-worker layer)
- checked_absent: n/a (no web/browser context; no MOCK/USE_MOCK/STUB env vars set by this probe)
- other LocalModelDesk instance on the machine (127.0.0.1:8766 python, 127.0.0.1:8771 shell app,
  pid 24401/24393) was left untouched throughout — verified unchanged pid before and after.
