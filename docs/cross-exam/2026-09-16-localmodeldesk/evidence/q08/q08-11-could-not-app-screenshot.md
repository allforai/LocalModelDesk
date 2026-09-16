# could_not：完整 app 路线的「设置面板 / 对外 API」截图

尝试：`open --env LOCALMODELDESK_DATA_ROOT=/tmp/lmd-q08c-elKflR --env LMD_SHELL_PORT=18830
--env LMD_PROBE_PORT=18831 -n /Users/aa/LocalModelDesk/dist/LocalModelDesk.app`（pid 69627
主进程 / 69633 python -m desk 子进程）。

- 起服务这一侧成功：`curl http://127.0.0.1:18830/api/config` 立即返回 200，内容与 q08-02
  一致（needs_setup:true，gateway 默认 enabled/0.0.0.0/8770）。
- 探针这一侧卡死：`GET http://127.0.0.1:18831/readback` 反复超时（先是探针自己的
  "probe timed out" 出错体，之后连 TCP 连接都收不到响应，curl 直接 operation timed out），
  试了 `/readback` 与 `/window?width=1200&height=800`，间隔重试共约 30 秒，webview 一直没有
  应答，因而无法用 `/eval` 把界面翻到设置抽屉里的"对外 API"那一段，也就拍不到这张截图。
- 收尾：`kill -TERM 69627 69633`——69633 应声退出，69627（主进程）对 TERM 无反应，
  改用 `kill -KILL 69627` 才结束；两个 pid 都是本次自己起的，未触碰机器上其它已在跑的
  LocalModelDesk 实例（8770/8766/8771 等）。临时数据根 /tmp/lmd-q08c-elKflR 已删除。

对外接口默认是开是关、监听在什么地址，这个问题本身已经由 q08-01～q08-08（(a) 只起服务的路线，
含预置空闲端口验证真实 bind 到通配地址）完整回答；这里缺的只是"设置面板里那一段勾选框长什么样"
的视觉证据。
