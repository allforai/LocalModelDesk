# served_by — Q06 / J4 (窗口从最窄拉到最宽)

- 探针请求打到 `127.0.0.1:19102`（LMD_PROBE_PORT），进程为 `LocalModelDesk`（pid 45655，
  `/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/MacOS/LocalModelDesk`）。
- 同一实例的 shell 端口 `127.0.0.1:19101`（LMD_SHELL_PORT），进程为
  `python3.13 -s -m desk`（pid 45661，`.../Contents/Resources/python/bin/python3.13`），
  两者同属一个 launch coalition（{45655,45657,45658,45661}），经 `lsof -i :19101` /
  `lsof -i :19102` 核对 pid 归属确认。
- 未经过任何代理/网关，请求直达单跳（本机 loopback）。
- 检查过 mock/stub 相关开关：本次 `open --env` 只传了 LOCALMODELDESK_DATA_ROOT、
  LMD_SHELL_PORT、LMD_PROBE_PORT 三个环境变量，没有 MOCK/USE_MOCK/STUB 之类的键；
  探针走的是真实 WKWebView（readback 里 appearance/locale/scroll 等字段均来自真实渲染），
  不是任何 mock 层。
