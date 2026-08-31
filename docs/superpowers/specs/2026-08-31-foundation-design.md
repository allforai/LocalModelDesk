# 模块设计：foundation

**日期** 2026-08-31
**对应 spec** `docs/superpowers/specs/2026-08-31-foundation-spec.md`
**覆盖需求** R-foundation-01 ~ R-foundation-06
**暴露** `data:deskConfig`、`data:pathRoots`、`api:resolvePaths`、`api:readConfig`、`api:writeConfig`、`api:completeFirstRun`、`api:adoptLegacyModels`
**消费** 无（根模块）

---

## 1. 架构

### 1.1 定位

foundation 是整棵依赖树的根：**路径与配置的唯一真相源**。它是一个纯 Python 子包
`desk/foundation/`，不 import 任何兄弟模块。所有兄弟模块通过它拿路径、读写配置；
仓库里除 `desk/foundation/paths.py` 外不允许出现第二处 `Path.home()` /
`os.path.expanduser` 拼接模型、输出或数据目录（用静态测试强制，见 §5）。

### 1.2 文件布局

```
desk/
  __init__.py
  __main__.py                # python -m desk 入口：组装并启动台面服务（见 §1.4）
  app.py                     # 极薄 HTTP 骨架：路由表 + ThreadingHTTPServer（见 §1.4）
  foundation/
    __init__.py              # 公开 API 的唯一 re-export 点
    paths.py                 # 运行模式判定 + PathRoots（data:pathRoots / api:resolvePaths）
    config.py                # DeskConfig + 原子读写（data:deskConfig / api:readConfig / api:writeConfig）
    firstrun.py              # api:completeFirstRun / api:adoptLegacyModels
    capabilities.py          # R-foundation-05 的能力探测
    errors.py                # 类型化异常与错误码
    routes.py                # foundation 自己的 HTTP 端点（挂到 desk/app.py 的路由表）
tests/
  test_foundation_paths.py
  test_foundation_config.py
  test_foundation_firstrun.py
  test_foundation_adopt.py
  test_foundation_capabilities.py
  test_foundation_invariants.py   # 仓库级静态断言（无第二处 Path.home()、无 SystemExit 等）
```

### 1.3 两种运行模式的单点判定（R-foundation-01）

安装态代码在 `.app/Contents/Resources/`，开发态直接从仓库跑。判定只在
`paths.py` 一处发生，依据是 **bundle 标记文件**，不靠散落的 if-dev 分支：

- 取 `desk` 包所在目录的父目录为候选资源根：`RES = Path(desk.__file__).parent.parent`。
- 若 `RES / "bundle.json"` 存在 → `mode = "bundle"`，`resources_root = RES`。
- 否则 → `mode = "dev"`，`resources_root = 仓库根`（同样是 `desk` 的父目录）。

`bundle.json` 由 packaging 模块在构建时写入 `Contents/Resources/`
（内容按 packaging 设计 §1.4：`{"app": "LocalModelDesk", "bundle_version": "...",
"python": "python/bin/python3.13"}`；foundation 只判存在性，内容仅用于状态展示）。
这是 foundation 定义、packaging 履约的布局契约（§1.5；文件名与键名已与 packaging §1.4
及 shell 的运行时判据对齐——三方同用这一个标记文件）。

### 1.4 服务启动骨架（R-foundation-05 的落点）

R-foundation-05 要求「`mlx-h3`、内嵌 venv、模型目录任一缺失时服务仍能启动并提供
状态接口」。这是对**服务进程启动路径**的要求，故启动入口归 foundation 管：

- `desk/app.py`：一个极薄骨架——`DeskApp` 持有一张路由表
  `(method, path_prefix, handler)`，内部用标准库 `ThreadingHTTPServer` 绑
  `127.0.0.1:8766`。它只做分发、JSON 编解码与错误信封，不含任何业务。
  各兄弟模块的 HTTP 适配层通过 `app.add_routes([...])` 注册自己的端点。
- `desk/__main__.py`：`resolve_paths()` → `setup_logging(roots)` → `probe_capabilities()`
  → 建 `DeskApp` → 依次注册各模块路由（缺能力的模块照常注册，运行时按能力状态报错）
  → `serve()`。
  **整个 `desk/` 内不允许出现 `raise SystemExit` / `sys.exit`**（静态测试强制，
  对应 census A19）；启动阶段任何能力缺失只落进 `capabilities` 状态，绝不阻止绑定端口。
- **日志落点（census A16）**：`foundation/paths.py` 提供 `setup_logging(roots)`，在
  `__main__` 绑定端口前调用一次——给根 logger 挂 `logging.FileHandler(roots.logs_dir /
  "desk.log")`（追加模式）+ 一个 stderr `StreamHandler`（dev 态便于观察）。全仓库唯一
  的文件日志配置点：兄弟模块只 `logging.getLogger(__name__)`，**不得自建 FileHandler、
  不得用相对路径开日志文件**（静态测试强制，见 §5）。子进程日志（`mlx-lm.log` 等）
  的目标路径由拉起方从 `PathRoots.logs_dir` 派生，同样不得落在代码目录。
- **启动对损坏配置的韧性**：`config.json` 损坏时启动不许死——`__main__` 里
  `resolve_paths()` 抛 `ConfigCorruptError` 则改用「静态根 + 默认派生路径」的
  `PathRoots` 完成绑定与路由注册（绑定 `127.0.0.1:8766` 本就不依赖 config），并把
  损坏事实记为 `capabilities["config"] = Capability(present=False, detail=<解析错误>)`。
  这**不是回退**：所有依赖 config 的端点（GET/PUT `/api/config`、first-run、adopt，
  以及兄弟模块每次 `resolve_paths()`）照常抛 `ConfigCorruptError` → 500
  `config_corrupt`，直到用户修复或删除该文件；服务活着只是为了把这个错误报出去。
- gateway 的 `0.0.0.0:8770` 监听是 gateway 模块自己的第二个 server，不经过这张表。

### 1.5 目录与布局契约（本模块定义，全仓库唯一）

**bundle 资源根**（只读）：

```
<resources_root>/                  # dev = 仓库根；bundle = .app/Contents/Resources
  bundle.json                      # 仅 bundle 态存在（模式标记，packaging §1.4 产出）
  desk/                            # Python 包（含 desk/static/ 前端）
  python/bin/python3.13            # 仅 bundle 态：内嵌可迁移 CPython（packaging §1.3）
  pylibs/desk/                     # 仅 bundle 态：desk + mlx_lm 依赖（uv --target 平铺）
  pylibs/music/                    # 仅 bundle 态：mlx_minimax_music3 依赖
  pylibs/h3/                       # 仅 bundle 态：mlx_h3 依赖（bundle 内无独立 mlx-h3 二进制）
```

**用户数据根**（可写）：

```
~/Library/Application Support/LocalModelDesk/
  config.json                      # data:deskConfig
  outputs/                         # 成品（可被 config.outputs_root 改址）
  history.jsonl                    # 作业历史（library 消费）
  sessions/                        # 多会话聊天（library 消费）
  logs/desk.log  logs/mlx-lm.log   # 日志（census A16）
  models/                          # 默认模型根（可被 config.models_root 改址）
    llms/<org>/<repo>/
    minimax-h3/
    minimax-music3/
```

数据根可被环境变量 `LOCALMODELDESK_DATA_ROOT` 覆盖（测试与开发用；生产不设）。

---

## 2. 组件

### 2.1 `paths.py` — `api:resolvePaths` / `data:pathRoots`

```python
@dataclass(frozen=True)
class PathRoots:
    mode: str                 # "bundle" | "dev"
    resources_root: Path      # 只读资源根
    static_dir: Path          # resources_root/desk/static
    venv_python: Path         # bundle: resources_root/python/bin/python3.13；dev: Path(sys.executable)
    mlx_h3_cmd: tuple[str, ...]  # H3 调用的 argv 前缀（media 消费）：
                              #   dev: 单元素（$LOCALMODELDESK_MLX_H3 或 shutil.which("mlx-h3") 或 ~/.local/bin/mlx-h3）
                              #   bundle: (venv_python, "-s", "-c", "from mlx_h3.cli import main; main()")
                              #           —— packaging §1.3：bundle 内无独立二进制，入口是 mlx_h3.cli:main
    mlx_h3_env: dict[str, str]   # 子进程附加环境：bundle {"PYTHONPATH": resources_root/pylibs/h3}；dev {}
    music_python: Path        # = venv_python（bundle 与 dev 同一解释器，packaging §1.3）
    music_env: dict[str, str] # bundle {"PYTHONPATH": resources_root/pylibs/music}；dev {}
    media_cli_dir: Path       # resources_root/desk/media（music3_cli.py 所在目录，media 消费）
    hf_cmd: tuple[str, ...]   # HF 下载 CLI 的 argv 前缀（resources 消费；Phase 1.2 对齐）：
                              #   dev: 单元素（$LOCALMODELDESK_HF 或 shutil.which("hf")；解析不到 → 空元组，
                              #        resources 据此报 hf_cli_missing，不猜路径）
                              #   bundle: (venv_python, "-s", "-c",
                              #            "from huggingface_hub.cli.hf import main; main()")
                              #     —— huggingface_hub 在 pylibs/desk（packaging §1.3），入口以锁定版本
                              #        console_script 定义为准；PYTHONPATH 随 desk 服务进程继承。
                              #     GUI App 的 PATH 没有 /opt/homebrew，bundle 态不得裸调 "hf"。
    data_root: Path           # $LOCALMODELDESK_DATA_ROOT 或 ~/Library/Application Support/LocalModelDesk
    config_path: Path         # data_root/config.json
    logs_dir: Path            # data_root/logs
    sessions_dir: Path        # data_root/sessions
    history_path: Path        # data_root/history.jsonl
    models_root: Path         # 来自 config（默认 data_root/models）
    outputs_root: Path        # 来自 config（默认 data_root/outputs）

def resolve_paths(*, data_root: Path | None = None,
                  resources_root: Path | None = None) -> PathRoots
```

- `resolve_paths()` 是 `api:resolvePaths` 的实现：先定静态根（§1.3 判定 + 环境变量），
  再 `read_config()` 取 `models_root` / `outputs_root` 合成完整 `PathRoots`。
  显式入参仅供测试注入假目录树；优先级 入参 > 环境变量 > 默认。
- 副作用极小：只确保 `data_root` 与 `logs_dir` 存在（`mkdir(parents=True, exist_ok=True)`）；
  `models_root`、`outputs_root` 的创建分别归 firstrun 与 library/media 的首次写入，
  resolve 本身不创建它们（首运前 models 根尚未选定）。
- 路径均 `expanduser().resolve()` 后返回绝对路径。

### 2.2 `config.py` — `data:deskConfig` / `api:readConfig` / `api:writeConfig`

`data:deskConfig` 的形状与默认值（`config_version = 1`）：

```json
{
  "config_version": 1,
  "first_run_done": false,
  "models_root": "<data_root>/models",
  "outputs_root": "<data_root>/outputs",
  "gateway": { "enabled": true, "host": "0.0.0.0", "port": 8770 }
}
```

```python
@dataclass(frozen=True)
class GatewayConfig: enabled: bool; host: str; port: int

@dataclass(frozen=True)
class DeskConfig:
    config_version: int
    first_run_done: bool
    models_root: Path
    outputs_root: Path
    gateway: GatewayConfig
    needs_setup: bool          # 派生字段：文件不存在 或 first_run_done 为假（R-foundation-03）
    def to_json(self) -> dict  # 序列化（needs_setup 不落盘）

def read_config(roots) -> DeskConfig
def write_config(roots, config: DeskConfig) -> None
def update_config(roots, **fields) -> DeskConfig   # 锁内 读-改-写，供 HTTP PUT 用
```

- **缺键补默认（R-foundation-02）**：`read_config` 对顶层与 `gateway` 子字典做
  逐键合并——文件里有的键取文件值，缺的键取默认值；未知键忽略但在 `write_config`
  时原样保留（round-trip 不丢新版本写入的键）。文件不存在 → 返回纯默认 +
  `needs_setup=True`，**不创建文件**。
- **损坏即报错**：`config.json` 存在但 JSON 解析失败 → 抛 `ConfigCorruptError`
  （带文件路径与解析错误）。不静默重建、不回退默认——错误就是错误（见 §6 假设 A3）。
- **原子写（R-foundation-06）**：同目录建 `config.json.tmp-<pid>-<random>` →
  写入 → `flush()` + `os.fsync()` → `os.replace(tmp, config_path)`。任何一步抛异常：
  尽力 `unlink` 临时文件后原样上抛；`config.json` 因 `os.replace` 的原子性要么是
  旧完整内容、要么是新完整内容。
- **并发**：模块级 `threading.Lock` 串行化所有写与读-改-写；多线程（HTTP handler
  是多线程的）同时 `update_config` 不会互相覆盖丢字段。

### 2.3 `firstrun.py` — `api:completeFirstRun` / `api:adoptLegacyModels`

```python
def complete_first_run(roots, models_root: Path | None = None) -> DeskConfig
```

（R-foundation-03）`models_root` 缺省为 `data_root/models`。流程：

1. `mkdir(parents=True, exist_ok=True)` 目标目录；
2. 可写性探测：写入并删除 `<models_root>/.lmd-write-probe`；
3. 任一步失败 → 抛 `NotWritableError`（含目录与 OS 错误原文），**配置不落盘、
   不回退默认目录**；
4. 成功 → `update_config(models_root=..., first_run_done=True)`，返回新配置。

```python
def adopt_legacy_models(roots, legacy_root: Path,
                        mode: Literal["point", "move"],
                        target_root: Path | None = None) -> AdoptResult
```

（R-foundation-04）识别 `legacy_root` 下的 `llms/`、`minimax-h3/`、`minimax-music3/`
三个子树（存在且为目录即认）；一个都没有 → `LegacyRootError`。
**任何模式、任何分支都不重新下载、不删除源数据。**

- **point 模式**：把 `models_root` 直接设为 `legacy_root`（legacy 布局与 §1.5 的
  models 布局约定一致，无需搬动），并置 `first_run_done=True`。零字节 IO。
- **move 模式**：`target_root` 缺省为 `data_root/models`。步骤：
  1. 拒绝 `target_root` 等于或位于 `legacy_root` 之内（`Path.is_relative_to`）；
  2. 逐子树统计字节数（`os.walk` 累加 `st_size`，不跟随符号链接）；
  3. 判同卷：比较 `legacy_root` 与 `target_root`（先 mkdir）的 `st_dev`；
  4. **同卷** → 空间检查恒过（rename 不占新空间），对每个子树
     `os.rename(src, target_root/<name>)`；目标已存在同名非空目录 → 该子树抛
     `AdoptConflictError`（不合并、不覆盖）；
  5. **跨卷** → 先查 `shutil.disk_usage(target_root).free`，`free < total_bytes + 1GiB
     安全余量` → 抛 `InsufficientSpaceError`，消息含 需要/可用/差额 三个字节数；
     足够则逐文件复制（`copy2` 保时间戳；已存在且字节数一致的目标文件跳过，
     使中断后重试可续）；**复制完成后源目录保持原样不删**，结果里注明
     `source_retained=True` 由用户自行回收；
  6. 全部子树成功 → `update_config(models_root=target_root, first_run_done=True)`；
     中途失败 → 抛 `AdoptError`，携带 已完成/未完成 子树清单，**不写配置**；
     重试是幂等的（同卷：已搬走的子树在源侧已不存在，自动跳过；跨卷：同字节文件跳过）。

```python
@dataclass(frozen=True)
class AdoptResult:
    mode: str; models_root: Path
    adopted: list[str]           # ["llms", "minimax-h3", ...]
    moved_bytes: int             # point 模式为 0
    source_retained: bool        # 跨卷复制时 True
```

### 2.4 `capabilities.py` — 能力探测（R-foundation-05）

```python
@dataclass(frozen=True)
class Capability: present: bool; path: str; detail: str   # detail: 缺失原因，present 时为 ""

def probe_capabilities(roots) -> dict[str, Capability]
# 键固定为: "mlx_h3"（bundle 态：pylibs/h3/mlx_h3/ 包目录存在；dev 态：mlx_h3_cmd[0] 存在且可执行）
#          "venv"（venv_python 存在且可执行；dev 态恒 present=sys.executable）
#          "models_root"（目录存在）
#          "music_runtime"（能 import mlx_minimax_music3 的静态近似：
#                           bundle 态查 pylibs/music/mlx_minimax_music3/ 包目录存在；dev 态查当前环境可 import）
#          "config"（config.json 可解析；损坏时 present=False，detail=解析错误，见 §1.4）
```

探测是只读、快速（纯 stat / 一次 import 尝试），结果作为 `data:pathRoots` HTTP
表示的一部分对外（§3）。**探测失败改变的是状态字段，永远不阻止服务启动。**
media / llm 模块在动手前消费此状态并以明确错误拒绝，而不是启动时死。

### 2.5 `errors.py` — 类型化异常

```python
class FoundationError(Exception): code: str; http_status: int; payload: dict
class ConfigCorruptError(FoundationError)    # code="config_corrupt",   500
class NotWritableError(FoundationError)      # code="not_writable",     400
class LegacyRootError(FoundationError)       # code="legacy_root_invalid", 400
class AdoptConflictError(FoundationError)    # code="adopt_conflict",   409
class InsufficientSpaceError(FoundationError)# code="insufficient_space", 409
                                             #   payload={"needed_bytes","free_bytes","shortfall_bytes"}
class AdoptError(FoundationError)            # code="adopt_failed",     500
                                             #   payload={"adopted":[...],"remaining":[...]}
```

### 2.6 `routes.py` — HTTP 适配层

foundation 自己的端点（挂在 `desk/app.py` 的路由表上；shell 首运面板与 ui 消费）：

| 方法 | 路径 | 对应 | 成功响应 |
|---|---|---|---|
| GET | `/api/config` | `api:readConfig` | `data:deskConfig` JSON（含 `needs_setup`） |
| PUT | `/api/config` | `api:writeConfig` | 更新后的 `data:deskConfig`（body 为待改字段的子集，锁内合并） |
| GET | `/api/paths` | `api:resolvePaths` | `data:pathRoots` JSON + `"capabilities": {...}` |
| POST | `/api/first-run` | `api:completeFirstRun` | body `{"models_root"?: str}` → 新 `data:deskConfig` |
| POST | `/api/adopt` | `api:adoptLegacyModels` | body `{"legacy_root": str, "mode": "point"\|"move", "target_root"?: str}` → `AdoptResult` JSON |

错误信封统一：`{"error": {"code": "<errors.py 的 code>", "message": "...", ...payload}}`，
HTTP 状态取异常的 `http_status`。适配层不含业务逻辑，只做参数解析 + 调库函数 + 映射异常。

---

## 3. 数据流

### 3.1 启动（dev 与 bundle 完全同一条路径）

```
python -m desk（dev） / python/bin/python3.13 -s -m desk（bundle，shell 拉起，packaging §1.3 契约）
  → paths.resolve_paths()          # bundle.json 有无 → 定 mode 与 resources_root
  → capabilities.probe_capabilities(roots)
  → DeskApp(127.0.0.1:8766) ← foundation.routes + 各兄弟模块路由
  → serve_forever()                # 无论 mlx-h3/venv/models 是否缺失
```

### 3.2 首运

```
shell(NSOpenPanel) / ui:firstRunPane
  → GET /api/config                # needs_setup=true → 进首运流程
  → (a) POST /api/first-run {models_root}          # 选目录 / 用默认
    (b) POST /api/adopt {legacy_root, mode:"point"} # 收编：指向
    (c) POST /api/adopt {legacy_root, mode:"move"}  # 收编：搬动
  → firstrun.* → config.update_config(原子写)
  → 响应 needs_setup=false 的新配置 → ui 进入正常台面
```

### 3.3 兄弟模块取路径（进程内）

```
resources/llm/media/library/gateway
  → foundation.resolve_paths() → PathRoots（含 config 派生的 models_root/outputs_root）
  → foundation.read_config()   → gateway 段等
```

配置被 PUT / 首运改变后，兄弟模块下一次 `resolve_paths()` 即见新值（无缓存穿透
问题：`resolve_paths` 每次现读 config；它只做一次 stat 级 IO，热路径可承受）。

---

## 4. 错误处理

| 情形 | 行为 |
|---|---|
| `config.json` 不存在 | 非错误：默认配置 + `needs_setup=true`（R-foundation-03） |
| `config.json` 损坏 | `ConfigCorruptError` → 500 `config_corrupt`；不重建不回退（错误保持错误） |
| 旧配置缺键 | 非错误：逐键补默认（R-foundation-02） |
| 首运目录不可写 | `NotWritableError` → 400，含 OS 错误原文；配置不落盘（R-foundation-03） |
| 收编根无任何已知子树 | `LegacyRootError` → 400 |
| move 目标空间不足 | `InsufficientSpaceError` → 409，含差额字节（R-foundation-04） |
| move 目标已有同名子树 | `AdoptConflictError` → 409；不合并不覆盖 |
| move 中途失败 | `AdoptError` → 500，带 已完成/未完成 清单；配置不写；重试幂等 |
| 原子写中途崩溃 | 旧 `config.json` 完好（`os.replace` 原子性，R-foundation-06） |
| mlx-h3 / venv / models 缺失 | 非错误：`capabilities` 状态字段；服务照常起（R-foundation-05） |
| `config.json` 损坏（启动时） | 服务仍绑定端口并注册路由（§1.4）；`capabilities["config"].present=False`；依赖 config 的端点持续报 500 `config_corrupt`——不静默重建、不假成功 |

原则重申：任何路径都没有「静默回退」「假成功」——要么明确成功，要么类型化异常带
机器可读 code 上抛到 HTTP 信封。

---

## 5. 测试（pytest，全部 `tmp_path`，快速确定性）

`tests/test_foundation_paths.py`
- dev 判定：假仓库树（无 `bundle.json`）→ `mode=="dev"`、各路径落在假树内；
- bundle 判定：假树写入 `bundle.json` → `mode=="bundle"`、`venv_python` 指向
  `python/bin/python3.13`、`mlx_h3_cmd` 与 `hf_cmd` 为内嵌解释器前缀（含 `-s`）、
  `mlx_h3_env`/`music_env` 的 PYTHONPATH 指向 `pylibs/h3`、`pylibs/music`；
- `LOCALMODELDESK_DATA_ROOT`（monkeypatch）与显式入参的优先级；
- resolve 后 `data_root`、`logs_dir` 已创建，`models_root` 未创建。

`tests/test_foundation_config.py`
- 无文件 → 全默认 + `needs_setup=True`，且磁盘上不产生文件；
- 缺键文件（只有 `{"models_root": ...}`）→ 其余键为默认，gateway 子字典逐键合并；
- 未知键 round-trip 保留；
- 损坏 JSON → `ConfigCorruptError`；
- **原子写注入测试**：先写好一份旧配置；monkeypatch `os.replace` 抛异常 / 让序列化中途抛
  → 断言旧文件字节不变、目录里无残留 tmp（或 tmp 已清）；
- 并发 `update_config`：多线程各改不同字段 N 次，终态无丢失字段、文件可解析。

`tests/test_foundation_firstrun.py`
- 默认目录：不传 `models_root` → `<data_root>/models` 被创建、`first_run_done=True`；
- 指定目录：传 `tmp_path/ext` → 落盘值为该目录；
- 不可写：`chmod 0o500` 的父目录 → `NotWritableError`，`config.json` 不存在或不变；
- probe 文件事后不残留。

`tests/test_foundation_adopt.py`（假权重 = 几个几十字节的假 `.safetensors`）
- point：假 legacy 树（含 `llms/x/y/a.safetensors` 等）→ `models_root==legacy_root`、
  `first_run_done=True`、源树字节不动、`moved_bytes==0`；
- 无已知子树 → `LegacyRootError`；
- move 同卷：`tmp_path` 内 src→dst，断言 rename 后源侧子树消失、目标侧内容完整、
  config 指向目标；目标已有同名非空目录 → `AdoptConflictError`；
- move 跨卷（monkeypatch 同卷判定为 False + monkeypatch `shutil.disk_usage`）：
  - free 充足 → 逐文件复制、**源树完好**、`source_retained=True`；
  - free 不足 → `InsufficientSpaceError`，`shortfall_bytes` 数值精确；
  - 复制中途注入异常 → `AdoptError` 带清单、config 未写；重跑同调用成功且已复制文件未重拷
    （对 copy 计数断言）；
- `target_root` 位于 `legacy_root` 内 → 拒绝。

`tests/test_foundation_capabilities.py`
- 五个键齐全；bundle 假树摆/不摆 `pylibs/h3/mlx_h3/` 包目录、dev 假环境有/无可执行 mlx-h3，分别断言 `present` 与 `detail`；
- 全缺时 `probe_capabilities` 正常返回（不抛）；
- **A16 行为测试**：`LOCALMODELDESK_DATA_ROOT=tmp_path` 下调 `setup_logging` 并打一条
  日志 → `tmp_path/logs/desk.log` 存在且含该行；当前工作目录与仓库目录内**没有**新增
  任何 `.log` 文件；
- **损坏配置下的启动**：写坏 `config.json` 后走 `__main__` 的组装函数（不真
  `serve_forever`，起在 `127.0.0.1:0`）→ 端口绑定成功、`capabilities["config"].present
  is False`、GET `/api/config` 返回 500 且 code 为 `config_corrupt`。

`tests/test_foundation_invariants.py`（仓库级静态断言，替 census A16/A19 站岗）
- `desk/` 下所有 `.py`：`Path.home()` 与 `expanduser` 仅允许出现在 `foundation/paths.py`
  （R-foundation-01）；
- `desk/` 下无 `raise SystemExit`、无 `sys.exit(`（R-foundation-05 / census A19）；
- `desk/` 下 `logging.FileHandler` / `basicConfig(` / `RotatingFileHandler` 仅允许出现在
  `foundation/paths.py` 的 `setup_logging`——文件日志配置单点，杜绝相对路径日志回到
  代码目录（census A16）；
- `desk/foundation/` 不 import 任何 `desk.` 兄弟子包（根模块无消费）。

HTTP 适配层测试并入上述文件：用 `DeskApp` 起在 `127.0.0.1:0` 临时端口，对 §2.6 五个
端点各打一发正常 + 一发错误请求，断言状态码与错误信封 code。全套无网络、无真权重、
无 reality gate。

---

## 6. Assumptions（内部决定，未越出模块边界）

- **A1 HTTP 骨架归属**：registry 没有「台面 HTTP 服务器」这个接口，但 R-foundation-05
  是对服务启动行为的要求，故把极薄的路由表骨架（`desk/app.py`）与入口
  （`desk/__main__.py`）放进 foundation 的交付范围。它零业务、约百行、可反悔；兄弟
  模块只依赖 `add_routes` 这一个注册点。各 `api:*` 的语义仍以 registry 名义定义，
  骨架只是运输层。
- **A2 bundle 标记（Phase 1.2 已对齐 packaging §1.4）**：标记文件名 `<resources_root>/bundle.json`，
  由 packaging 写入；foundation 只判存在性。bundle 内布局契约（`python/`、`pylibs/{desk,music,h3}/`、
  `desk/static/`）见 §1.5，与 packaging 设计 §1.3 一致；shell 判「内嵌运行时存在」用的是同一个文件，
  不存在第二个标记。
- **A3 损坏配置不自愈**：`config.json` 损坏时报 `ConfigCorruptError` 而不是静默重建，
  遵循「错误保持错误」的冻结约定；spec 只豁免「缺键」，未豁免「损坏」。
- **A4 gateway 默认值**：`{"enabled": true, "host": "0.0.0.0", "port": 8770}`。Phase 0
  冻结了「监听 0.0.0.0、无鉴权、端口 8770 可配置」，故默认开启；关闭开关是 ui
  settingsPane 的既有控件。
- **A5 收编即完成首运**：`adoptLegacyModels` 成功后置 `first_run_done=True`——它是首运
  面板上与「选目录」并列的另一条完成路径（shell R-shell-07 / ui R-ui-09 均如此消费）。
- **A6 move 的非破坏语义**：同卷用 `os.rename`（不复制不删除）；跨卷复制后**保留源**并
  在结果里声明，由用户自行回收。这同时满足 R-foundation-04 的「不得删除源」与本轮
  「不得删动真实权重」的授权红线；验收一律 `tmp_path`。跨卷空间校验留 1 GiB 安全余量。
- **A7 H3 调用形态（Phase 1.2 已对齐 packaging §1.3）**：dev 态 `mlx_h3_cmd` 为单元素，解析顺序
  `$LOCALMODELDESK_MLX_H3` → `shutil.which("mlx-h3")` → `~/.local/bin/mlx-h3`（现状安装位置）；
  bundle 态无独立二进制，前缀为 `(python/bin/python3.13, "-s", "-c", "from mlx_h3.cli import main; main()")`
  并配 `mlx_h3_env` 的 `PYTHONPATH=pylibs/h3`。所有内嵌解释器子进程一律带 `-s`
  （packaging 运行期契约：禁用用户 site-packages）。
- **A8 dev 态 venv**：`venv_python = sys.executable`（开发者从装齐依赖的 venv 里起服务）；
  现有 `.venv-desk` / `.venv-music3` 双 venv 布局不被延续——bundle 是「单内嵌解释器 + 三套
  pylibs」（packaging §1.3，无任何 venv），dev 按装齐全部依赖的单环境开发。
- **A9 resolve_paths 每次现读 config**：不做进程内缓存，保证 PUT /api/config 与首运后
  所有模块立即见到新 `models_root`/`outputs_root`；代价是每次一趟小文件读，可接受。
- **A10 端点路径**：`/api/config`、`/api/paths`、`/api/first-run`、`/api/adopt` 是运输层
  内部命名（registry 管语义名，不管 URL）；ui / shell 设计以本表为准。
