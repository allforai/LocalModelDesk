# 代码摘录：对外网关默认值与首启行为

## desk/gateway/service.py
```
9: _DEFAULTS = {"enabled": True, "host": "0.0.0.0", "port": 8770}
```
`_gateway_config()`（52-55行）：`cfg = dict(_DEFAULTS); cfg.update((self._read_config() or {}).get("gateway") or {})`
——没有持久化配置时，直接用这份默认值。

`start_from_config()`（78-80行）调用 `_start(self._gateway_config())`；`_start()`（57-76行）里
`if not cfg["enabled"]: return`——只有 enabled 为 False 才不尝试绑定；默认 enabled=True，所以
进程一起来就会尝试用默认 host/port 绑定监听 socket，不需要用户在设置里勾选什么。

## desk/foundation/config.py
```
59:    return {
...
59:        "gateway": {"enabled": True, "host": "0.0.0.0", "port": 8770},
60:    }
```
`_defaults()`（53-60行）是全新安装（config.json 不存在）时的落地默认值，与 service.py 的
_DEFAULTS 一致：enabled=true, host="0.0.0.0"（通配，绑定所有网卡）, port=8770。

`_load_raw()`（63-79行）：`if not config_path.exists(): return None`——全新数据根下没有
config.json 文件，`read_config()`（140-144行）会用 `_from_raw(None, data_root)` 落到纯默认值，
且 `needs_setup=(raw is None) or not merged["first_run_done"]`（130行）在全新安装时为 True。

代码里没有找到任何"首次启动自动把默认配置写盘"的调用（grep write_config/first_run 只命中
config.py 自身定义处，desk/runtime.py 与 desk/app.py 没有相关调用）——也就是说全新安装、
服务刚起来时，config.json 在磁盘上还不存在，网关配置完全来自内存默认值。
