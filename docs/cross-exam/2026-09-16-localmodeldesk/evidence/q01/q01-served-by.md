# served_by — q01

- host: 127.0.0.1:50988
- process: /opt/homebrew/Cellar/python@3.14/3.14.7/.../Python -m desk (pid 94068), launched by this prober via
  `LOCALMODELDESK_DATA_ROOT=/tmp/lmd-crossexam-q01.b6bj3B LMD_SHELL_PORT=50988 python3 -m desk`
  from /Users/aa/LocalModelDesk (repo root).
- lsof -i :50988 confirms this exact pid holds the listening socket (single hop, no proxy).
- Backend is a single-process http.server.ThreadingHTTPServer (desk/app.py); no dev-server proxy in front of it.

## mock_layers (currently in effect)
(none — empty array)

## checked_absent
- No MOCK / USE_MOCK / STUB env vars present in the launch environment (only LOCALMODELDESK_DATA_ROOT and LMD_SHELL_PORT were set).
- grep across desk/ for json-server / miragejs / nock / msw / "service worker" found no matches — this backend is a plain stdlib http.server, no such tooling is even a dependency.
- No browser/service-worker context applies (type: api, plain HTTP requests via curl).
