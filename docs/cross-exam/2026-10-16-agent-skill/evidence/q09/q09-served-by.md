host 127.0.0.1:8766
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 31005   aa    4u  IPv4 0x77646812c27af57d      0t0  TCP 127.0.0.1:8766 (LISTEN)
  PID COMMAND
31005 /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk

## Test conditions
- LMDESK_FAKE_VERSION=9.9.9 was set only on the three fake-version commands (q09-01). It overrides the CLI-side version value (cli field / "lmdesk 9.9.9" text) and triggers the mismatch notice on stderr.
- It did not replace or intercept any desk response: requests still went to the real desk process (pid 31005) at 127.0.0.1:8766, and the desk's own version (1.0.0) and the models list came from the real backend.
- Control and dev-entry runs had no variable set.
- No proxy, MSW, stub server or sandbox config was used. mock_layers is therefore empty.
