## wrapper
#!/bin/bash
# lmdesk inside LocalModelDesk.app: the embedded Python runs desk.agent_cli (A-02).
SELF="$0"; while [[ -L "$SELF" ]]; do t="$(readlink "$SELF")"; [[ "$t" = /* ]] && SELF="$t" || SELF="$(dirname "$SELF")/$t"; done
RES="$(cd "$(dirname "$SELF")/.." && pwd)"
exec env -u PYTHONHOME PYTHONPATH="$RES" PYTHONDONTWRITEBYTECODE=1 "$RES/python/bin/python3.13" -s -m desk.agent_cli "$@"

## argv seen
22117 21909 Mon Oct 19 20:53:28 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
25844 25130 Mon Oct 19 20:54:12 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
27842 27841 Mon Oct 19 20:54:31 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
29172 29038 Mon Oct 19 20:54:47 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
29895 29712 Mon Oct 19 20:54:56 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
31201 31200 Mon Oct 19 20:55:12 2026     /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk.agent_cli status --json
