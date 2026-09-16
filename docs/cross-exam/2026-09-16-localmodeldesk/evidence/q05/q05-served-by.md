# 请求去向 — q05 (J3: 菜单栏"打开成品目录")

- 目标进程：`/Users/aa/LocalModelDesk/dist/LocalModelDesk.app` 的 pid **45162**（外壳/UI 进程），
  与其 python 后端 pid **45168**（`python3.13 -s -m desk`）。
- 启动方式：`open --env LOCALMODELDESK_DATA_ROOT=/tmp/lmd-q05-iaObw6 --env LMD_SHELL_PORT=8781 --env LMD_PROBE_PORT=8782 -n dist/LocalModelDesk.app`
- host:port：`127.0.0.1:8781`（LMD_SHELL_PORT，本地后端）、`127.0.0.1:8782`（LMD_PROBE_PORT，取证探针）。
  由 `lsof -nP -iTCP:8781/8782 -sTCP:LISTEN` 确认监听方是 pid 45168 / 45162，与其它两个已在跑的实例
  （8766/8771，以及 unix id 12410/12418；另一独立实例 unix id 44345/44351 监听 60485/60486）分离，
  未触碰任何一个。
- 点击菜单栏"打开成品目录"后，`logs/desk.log` 记录 `22:43:56,764 POST /api/outputs/reveal HTTP/1.1 200`——
  请求打到了自己这个实例的后端（127.0.0.1:8781），得到 200。
- mock_layers：无——这是原生 app 自带的本地 HTTP 后端，不经过浏览器、无 service worker/MSW 可言。
- checked_absent：不适用（native 型不存在 mock 层这一类拦截）。
