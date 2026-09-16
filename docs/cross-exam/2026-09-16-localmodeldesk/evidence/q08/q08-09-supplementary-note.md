# 补充实验：端口不被占用时网关会不会真的监听

主证据（q08-01/03/04/05）用的是全新数据根 + 默认配置（未预置 config.json），此时默认端口 8770
被机器上另一个已在跑的 LocalModelDesk 实例占用，绑定失败（q08-01 里 last_error 已记录原文），
所以从这次运行本身看不到"真的监听在哪个地址"的直接证据——只能看到 enabled=true、host=0.0.0.0、
port=8770 这三个配置值，以及 listening=false。

为了不去碰占着 8770 的进程，另起了一个全新临时数据根（/tmp/lmd-q08b-fnuJLW），预置了一份
config.json：gateway.port 改成一个当时空闲的端口 18812（其余字段与代码默认值一致：
enabled=true, host="0.0.0.0"），first_run_done 设为 true 以跳过设置向导。启动后
GET /api/gateway/config 返回 listening: true，last_error: null；`lsof` 看到该进程
(pid 63653) 有一条 `TCP *:18812 (LISTEN)`——`*` 即 0.0.0.0，监听所有网卡，不只是 127.0.0.1。
这证实了：默认配置一旦端口可用，网关确实会真的监听，且监听地址是通配地址（局域网内其他设备
理论上能连到 status 里报告的 lan_host:port）。

这是补充实验，不是「全新安装、未预置任何东西」的原始状态——原始状态的证据在 q08-01 到 q08-05。
