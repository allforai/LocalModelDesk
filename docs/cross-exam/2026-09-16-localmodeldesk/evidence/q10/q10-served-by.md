# q10 served-by

- probe: http://127.0.0.1:19772 (LMD_PROBE_PORT) — process: LocalMode (pid 81079), native shell/Electron-like wrapper `/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk`
- 台面服务 (desk service): 本应监听 http://127.0.0.1:19771 (LMD_SHELL_PORT) — process: python3.13 -s -m desk (pid 81095) — 已被本实测官按 pid kill 掉以制造错误页
- 错误页本身：`location.href` = `about:blank`，证实是外壳 `loadHTMLString` 直接塞进 WKWebView 的静态 HTML，不经过台面服务
- mock_layers: []（无 service worker：`typeof navigator.serviceWorker` 在 about:blank 上下文返回 undefined；无 MOCK/USE_MOCK/STUB 相关探测对象）
- checked_absent: ["navigator.serviceWorker 不存在（about:blank 上下文）"]
