# 请求去向 — q04 (J1 journey)

- native app 窗口取证探针：`127.0.0.1:60486`（自选空闲端口，`LMD_PROBE_PORT`）
  - 进程：`/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk`（pid 44345）
- shell/backend 侧车：`127.0.0.1:60485`（自选空闲端口，`LMD_SHELL_PORT`）
  - 进程：`/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/python/bin/python3.13 -s -m desk`（pid 44351, ppid 44345）
- 数据根：`/tmp/lmd-q04-n6SiAJ`（自建全新临时目录，非 ~/LocalModelDesk、非 ~/Library/Application Support/LocalModelDesk）
- 其他已在跑的 LocalModelDesk 实例（未触碰）：
  - `localhost:8766`（python3.1，pid 12418）
  - `localhost:8771`（LocalModelDesk app，pid 12410）
- mock_layers: 无（native 桌面 app，无 service worker / MSW / mock 开关）
- checked_absent: 未检查浏览器层 mock（native WKWebView 无外部网络请求需要拦截；本问未涉及对外 API 转发路径）
