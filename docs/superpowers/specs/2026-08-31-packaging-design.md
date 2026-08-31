# 模块设计：packaging

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-packaging-spec.md`
**覆盖需求** R-packaging-01 … R-packaging-09

---

## 1. 架构

### 1.1 一句话

五个幂等的 bash 脚本（`scripts/`），把干净 checkout 变成一个自包含、已签名、可验证的
`LocalModelDesk.app`，并提供安装与卸载；所有破坏性动作参数化，可整体指向 tmp 假目录。

### 1.2 输入 / 输出

| 输入 | 说明 |
|---|---|
| `macos/*.swift` | shell 模块的 Swift 源（packaging 只编译，不设计其内部） |
| `desk/`（含 `desk/static/`） | Python 服务包与静态前端 |
| `packaging/` | 构建静态资产：plist 模板、三份 pinned 依赖锁、图标源、版本号、entitlements |
| 构建机工具 | `swiftc`、`codesign`、`uv`（`/opt/homebrew/bin/uv`，实测 0.12.5）——**仅构建期需要**，产物零引用 |

| 输出 | 说明 |
|---|---|
| `dist/LocalModelDesk.app` | 自包含产物；拷到 `/Applications` 即可运行 |

### 1.3 产物 bundle 布局（本模块的核心契约）

```
LocalModelDesk.app/Contents/
  Info.plist                      # R-packaging-03
  MacOS/LocalModelDesk            # swiftc 编译的 shell 可执行文件
  Resources/
    AppIcon.icns
    bundle.json                   # bundle 标记（见 1.4；foundation 以此判定“App 内运行”）
    desk/                         # Python 包原样拷入（含 desk/static/）
    python/                       # 可迁移 CPython 3.13.x（python-build-standalone，经 uv 获取）
      bin/python3.13
      lib/...
    pylibs/                       # 三套独立 site-packages（uv pip install --target）
      desk/                       #   mlx_lm==0.31.3 等（含 huggingface_hub，供 resources 下载用）
      music/                      #   mlx_minimax_music3==0.0.1a0 等
      h3/                         #   mlx_h3==0.0.1a3 等
    requirements/                 # 构建时实际使用的三份锁文件拷贝（溯源用）
```

运行期环境契约（foundation `api:resolvePaths` 据此向 llm / media 发路径；packaging 只保证布局存在且可导入）：

| 角色 | 解释器 | `PYTHONPATH` | 入口 |
|---|---|---|---|
| desk 服务 | `Resources/python/bin/python3.13` | `Resources` + `Resources/pylibs/desk` | `-m desk` |
| mlx-lm 内部服务 | 同上 | `Resources/pylibs/desk` | `-m mlx_lm server` |
| H3 视频 | 同上 | `Resources/pylibs/h3` | 模块 `mlx_h3.cli:main`（实测 console_script 即此函数） |
| Music 3 | 同上 | `Resources/pylibs/music` | `mlx_minimax_music3` 包（media 模块定调用形态） |
| HF 下载（resources） | 同上 | 随 desk 服务继承（`Resources` + `Resources/pylibs/desk`，huggingface_hub 在内） | `-c "from huggingface_hub.cli.hf import main; main()"`（hf console_script 入口；foundation `data:pathRoots.hf_cmd` 据此拼前缀） |

上述所有进程一律带 `-s` 启动（禁用用户 site-packages），`PYTHONPATH` 显式给定——
否则内嵌解释器会静默读取 `~/.local/lib/python3.13/site-packages`，一个「碰巧靠用户机器上装过的包才能跑」
的 bundle 会通过一切检查。这是 R-packaging-02「不依赖用户级 site-packages」的**运行期强制点**
（shell / foundation 拼命令时照此执行；verify 的 V6 以同样方式冒烟，见 2.4）。

选 `--target` 平铺目录而不是 venv 的原因（这是自包含性的关键决定）：

- venv 的 `pyvenv.cfg` 写死绝对 `home =` 路径、`bin/` 脚本 shebang 写死构建机路径——bundle 拷到
  `/Applications` 后全部失效，且必然触发 R-packaging-05 的自包含扫描；
- `--target` 产物内部全是相对引用；三个环境共用同一个内嵌解释器（三者实测同用 mlx 0.32.2、
  同为 CPython 3.13，无解释器分叉必要）；
- 构建后删除 `pylibs/*/bin/`（shebang 带构建机绝对路径，且无人消费——一律 `python -m` / import 调用），
  并禁止字节码预编译（pyc 内嵌构建路径，还虚增体积）。

### 1.4 bundle 标记 `Resources/bundle.json`

```json
{ "app": "LocalModelDesk", "bundle_version": "<VERSION>", "python": "python/bin/python3.13" }
```

foundation 的 spec 写明「靠是否存在 bundle 标记判断」运行形态；packaging 是这个标记的**生产者**。
它不是注册表接口，属于 foundation `api:resolvePaths` 之下的实现契约；键名以 foundation 设计为准，
本文按上表先行（见 Assumptions A7）。

### 1.5 脚本 ↔ 注册表接口映射

| 注册表接口 | 实现 |
|---|---|
| `api:buildAppBundle` | `scripts/build-app.sh` |
| `api:signAppBundle` | `scripts/sign-app.sh` |
| `api:verifyAppBundle` | `scripts/verify-app.sh` |
| `api:installApp` | `scripts/install-app.sh` |
| `api:uninstallApp` | `scripts/uninstall-app.sh` |

---

## 2. 组件

所有脚本统一 `set -euo pipefail`；破坏性/写盘路径全部可用参数覆盖。

### 2.1 `packaging/` 静态资产（新增顶层目录）

| 文件 | 用途 |
|---|---|
| `Info.plist.template` | 含 `@VERSION@` 占位；键齐：`CFBundleIdentifier`、`CFBundleName`、`CFBundleExecutable`、`CFBundleShortVersionString`、`CFBundleVersion`、`CFBundleIconFile`、`LSMinimumSystemVersion`、`CFBundlePackageType`、`NSHighResolutionCapable` |
| `VERSION` | 单点版本号（如 `1.0.0`），同时填 ShortVersion 与 BundleVersion |
| `python-version.txt` | 内嵌 CPython 精确版本（`cpython-3.13.15`，与现役三个 venv 一致） |
| `requirements-desk.txt` / `-music.txt` / `-h3.txt` | **全 `==` 钉死**的锁文件（由 `uv pip compile` 从对应 `.in` 生成；`.in` 顶层各只有一行：`mlx-lm==0.31.3` / `mlx-minimax-music3==0.0.1a0` / `mlx-h3==0.0.1a3`） |
| `entitlements.plist` | 空 dict。全部 Mach-O 用同一 Developer ID 签名，hardened runtime 的库校验天然通过，不需要任何豁免（见 Assumptions A5） |
| `icon/icon-1024.png` | 图标源；构建期 `sips` + `iconutil` 派生 `AppIcon.icns` |

### 2.2 `scripts/build-app.sh` — `api:buildAppBundle`（R-packaging-01/02/03）

```
用法: build-app.sh [--output dist] [--identity "…"] [--adhoc] [--python-version X]
```

步骤（任一步失败即 `exit 1`，不产出半成品）：

1. **staging**：在 `<output>/.staging.$$/LocalModelDesk.app` 下搭骨架；`trap` 保证退出时删 staging。
2. **Swift 编译**：`xcrun swiftc -O macos/*.swift -o Contents/MacOS/LocalModelDesk
   -target arm64-apple-macos<LSMinimumSystemVersion>`。
3. **拷 desk 包**：`Contents/Resources/desk/`（排除 `__pycache__`、测试）。
4. **内嵌 Python**：`UV_PYTHON_INSTALL_DIR=<staging tmp> uv python install <pinned>`，
   把整棵可迁移 CPython 拷进 `Resources/python/`（python-build-standalone 构建本身可迁移）。
5. **三套 pylibs**：对每套
   `uv pip install --python Resources/python/bin/python3.13 --target Resources/pylibs/<name>
   --no-compile-bytecode -r packaging/requirements-<name>.txt`；
   然后 `rm -rf pylibs/<name>/bin`；锁文件拷入 `Resources/requirements/`。
6. **Info.plist**：模板替换 `@VERSION@` 落盘；`plutil -lint` 校验。
7. **图标**：`sips` 生成 iconset 各尺寸 → `iconutil -c icns` → `Resources/AppIcon.icns`。
8. **bundle.json** 落盘。
9. **签名**：调 `sign-app.sh`（透传 `--identity` / `--adhoc`）。
10. **验证**：调 `verify-app.sh <staging app>`，失败即整体失败。
11. **原子发布**：`rm -rf <output>/LocalModelDesk.app.old` → 既有产物先 `mv` 成 `.old` → staging `mv` 到位 → 删 `.old`。
    `dist/LocalModelDesk.app` 这个名字上**永不存在**半成品。

可重复性：uv 自带缓存，二次构建不重复下载；步骤全幂等。

### 2.3 `scripts/sign-app.sh` — `api:signAppBundle`（R-packaging-04）

```
用法: sign-app.sh <app 路径> [--identity "…"] [--adhoc]
```

- 身份解析：`--identity` > 环境变量 `CODESIGN_IDENTITY` > `security find-identity -v -p codesigning`
  里唯一的 `Developer ID Application`（实测本机为 `SUPERSTRING TECH K.K. (B49F324XWZ)`）。
  找不到即报错并打印候选列表；`--adhoc` 用 `-s -`（开发/测试用，跳过 timestamp）。
- **由内向外**：
  1. `find Contents/Resources -type f` 里筛出全部 Mach-O（按 magic 判断：`.so`、`.dylib`、
     `python3.13` 等可执行），逐个
     `codesign --force --options runtime --timestamp --entitlements packaging/entitlements.plist -s <id>`；
  2. 签 `Contents/MacOS/LocalModelDesk`；
  3. 最后对 `.app` 整体签一次（封 resource seal）。
- `--force` 保证幂等，可对已签 bundle 重签。

### 2.4 `scripts/verify-app.sh` — `api:verifyAppBundle`（R-packaging-05）

```
用法: verify-app.sh <app 路径> [--source-root <checkout 根>]
```

只读。**收集全部失败后统一报告**再 `exit 1`（一次跑出完整问题清单），检查项：

| # | 检查 | 命令/方法 |
|---|---|---|
| V1 | 签名 | `codesign --verify --deep --strict --verbose=2` 退出码 0 |
| V2 | plist 键 | `PlistBuddy -c Print:<key>` 逐键断言 2.1 表全部存在且非空 |
| V3 | **自包含扫描** | `grep -ra` 全 bundle 搜禁串：`/opt/homebrew`、`<source-root 绝对路径>`（默认 `git rev-parse --show-toplevel`）、`$HOME/.local/share/uv`、`$HOME/.local/bin`；命中即列出文件与串 |
| V4 | 无 venv 残留 | bundle 内不存在任何 `pyvenv.cfg`、不存在 `pylibs/*/bin/`、`pylibs/` 下无 `__pycache__` |
| V5 | 结构 | `Resources/python/bin/python3.13` 存在且可执行；`desk/`、`pylibs/{desk,music,h3}/`、`bundle.json`、`AppIcon.icns` 存在 |
| V6 | 导入冒烟 | 用**内嵌** python 带 `-s`（与 1.3 运行期契约一致，排除用户 site-packages 兜住导入的假阳性）依次跑：`PYTHONPATH=Resources:Resources/pylibs/desk -c "import desk"`（与 desk 服务真实 PYTHONPATH 一致，`desk` 包顶层可能导入第三方依赖）、`PYTHONPATH=pylibs/desk -c "import mlx_lm"`、`PYTHONPATH=pylibs/music -c "import mlx_minimax_music3"`、`PYTHONPATH=pylibs/h3 -c "import mlx_h3.cli"`、`PYTHONPATH=pylibs/desk -c "from huggingface_hub.cli.hf import main"`（验证 resources 的 hf 下载入口在锁定版本里存在；只导入，不推理，秒级） |
| V7 | 旧脚本已亡 | `--source-root` 下 `initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`、`media-gui/start.sh` 均不存在（R-packaging-08 的机检半） |

### 2.5 `scripts/install-app.sh` — `api:installApp`（R-packaging-06）

```
用法: install-app.sh [--app dist/LocalModelDesk.app] [--dest /Applications]
```

1. 先跑 `verify-app.sh`，不过不装。
2. 若 `<dest>/LocalModelDesk.app` 已存在：读其 `Info.plist` 确认 `CFBundleIdentifier`
   等于我们的 bundle id 才 `rm -rf`（防误删同名异物），否则报错退出。
3. `ditto <app> <dest>/LocalModelDesk.app`（ditto 保 xattr 与签名）。

验收永远走 `--dest <tmp>`；对真实 `/Applications` 的安装只出现在人工 runbook（授权红线）。

### 2.6 `scripts/uninstall-app.sh` — `api:uninstallApp`（R-packaging-07）

```
用法: uninstall-app.sh [--app-path /Applications/LocalModelDesk.app]
                       [--data-root "~/Library/Application Support/LocalModelDesk"]
                       [--launch-agents-dir ~/Library/LaunchAgents]
                       [--purge-data] [--dry-run]
```

动作（每一步失败不阻塞后续，最后汇总；`--dry-run` 只打印计划）：

1. **卸 LaunchAgent**（吸收 census A11）：
   `launchctl bootout gui/$(id -u)/com.aa.localmodeldesk`（容错 `|| true`）；
   删 `<launch-agents-dir>/com.aa.localmodeldesk.plist`。
2. **删 App**：读 `<app-path>/Contents/Info.plist`，`CFBundleIdentifier` 匹配才删；不匹配报错不删。
3. **数据**：默认**一概不动**。仅 `--purge-data` 时删用户数据，且执行**模型多重保护**：
   - 逐条枚举 `<data-root>` 的直接子项，跳过 `models/`；
   - 读 `<data-root>/config.json` 的 `models_root`，该路径及其子树无条件跳过
     （覆盖模型根被首运改到外置盘/收编目录的情况）；
   - `config.json` **存在但解析失败**（损坏/非 JSON/缺 `models_root` 键）时，**拒绝执行整个 purge**：
     非零退出并说明「模型根未知，不删任何数据」——绝不在模型根不可知时靠猜删数据
     （`config.json` 不存在则按默认布局处理：自定义模型根只能经首运写入 config，故不存在 config 即不存在自定义根）；
   - 名为 `llms`、`minimax-h3`、`minimax-music3` 的目录无条件跳过（收编目录被指为 data 邻位时的兜底）。
4. **通用护栏**：所有 `rm -rf` 前断言路径为绝对路径、非 `/`、非 `$HOME` 本身、确实存在；不跟随符号链接。

**模型权重在任何路径组合下都不会被本脚本删除**——这是不变量，测试专门证明（见 §5）。

### 2.7 旧脚本收编与删除（R-packaging-08，执行期动作）

| 旧脚本 | 行为去向（注册表接口） | 证明方 |
|---|---|---|
| `initModels.sh`（目录/状态/下载） | `api:listCatalog`、`api:verifyModel`、`api:startDownload` | resources 测试 |
| `run-h3.sh` | `api:startVideoJob` | media 测试（逐参数比对） |
| `run-music3.py` | `api:startMusicJob` | media 测试 |
| `unload-llm.sh`（按端口杀） | `api:reapLlmPort`、`api:unloadLlm` | arbiter / llm 测试 |
| `media-gui/start.sh` | `api:spawnEmbeddedServer` | shell |

packaging 侧职责：在上述模块合入后 `git rm` 五个脚本；机检 = verify-app.sh 的 V7 +
census「重跑方式」的 grep 全绿。**顺序约束**：删除排在对应模块任务之后（执行计划里显式依赖）。

### 2.8 README 改写（R-packaging-09，文档交付）

改写为**安装后的真实行为**，必须包含：

1. 安装：`scripts/build-app.sh` → 拷 `/Applications`；签名形态（Developer ID + hardened runtime，
   **未公证**，首启可能需右键打开）。
2. **不自启**：删除「开机自启」表述；旧 LaunchAgent 由 `uninstall-app.sh`（或安装 runbook）卸除；
   B20 改写为「打开 App 即全部可用」。
3. 菜单栏形态：关窗不退、菜单栏 Quit 才停服务。
4. 模型目录：默认 `~/Library/Application Support/LocalModelDesk/models`，首运可改；
   既有 339G 走收编不重下；换机器 = 装 App 后在资源面板补下。
5. **对外 API 事实陈述**：OpenAI + Anthropic 兼容接口监听 `0.0.0.0:8770`、**无鉴权**，
   同网段任何设备可驱动本机模型（Phase 0 人类确认的风险，README 不得再写「推理不出门」）。
6. 旧脚本已删除，对应操作在 App 内的位置。

机检：`tests/test_packaging.py::test_readme_states_real_behavior`（见 5.1）断言以上事实性内容在场、
过时表述已亡——README 不改写则测试红，防止本条沦为「写了等于做了」。

---

## 3. 数据流

### 3.1 构建期

```
checkout ──┬─ macos/*.swift ── swiftc ──────────────► Contents/MacOS/LocalModelDesk
           ├─ desk/ ── 拷贝 ─────────────────────────► Resources/desk/
           ├─ packaging/python-version.txt ── uv ────► Resources/python/      （网络：PBS 镜像）
           ├─ packaging/requirements-*.txt ── uv ────► Resources/pylibs/{desk,music,h3}/ （网络：PyPI）
           ├─ packaging/Info.plist.template + VERSION► Contents/Info.plist
           └─ packaging/icon/ ── sips/iconutil ──────► Resources/AppIcon.icns
                    │
                    ▼
        sign-app.sh（由内向外签名） ─► verify-app.sh（V1–V7 全过） ─► 原子 mv ─► dist/LocalModelDesk.app
```

### 3.2 运行期（packaging 只定契约，不写运行代码）

```
用户双击 .app ─► MacOS/LocalModelDesk（shell 模块，api:spawnEmbeddedServer）
                    │  按 1.3 环境契约拼命令：Resources/python/bin/python3.13 -s -m desk
                    ▼
              desk 服务（foundation 见 Resources/bundle.json → bundle 模式，api:resolvePaths
              把 pylibs/h3、pylibs/music、内嵌解释器路径发给 media / llm）
```

### 3.3 安装 / 卸载

```
install-app.sh: verify ─► （同 id 时清旧）─► ditto ─► <dest>/LocalModelDesk.app
uninstall-app.sh: bootout+删 plist ─► 校 id 删 .app ─► [--purge-data] 删数据（models 三重跳过）
```

---

## 4. 错误处理

| 情形 | 行为 |
|---|---|
| 构建任一步失败 | `set -e` + `trap` 清 staging；`dist/LocalModelDesk.app` 保持上一次完好产物或不存在，**永无半成品**（R-packaging-01） |
| 找不到签名身份 | sign-app.sh 报错并打印 `security find-identity` 候选；不静默降级 ad-hoc |
| uv / 网络失败 | 非零退出，报出具体是 python 还是哪份 requirements；staging 清理 |
| verify 命中禁串 | 列出**每个**命中文件与禁串后 exit 1（收集全量，不首错即停） |
| install 目标已存在但 bundle id 不符 | 报错退出，不删不覆盖 |
| uninstall 各步失败 | 记录、继续、末尾汇总非零；plist 不存在不算错（幂等） |
| uninstall 路径护栏触发 | 拒绝执行该 rm 并明确说明，绝不静默跳过 |
| `--purge-data` 但 `config.json` 损坏不可解析 | 拒绝整个 purge，非零退出并说明「模型根未知」；不删任何数据 |
| 一切失败 | 只报错，不伪造成功、不造兜底产物（冻结约定「错误保持错误」） |

---

## 5. 测试

### 5.1 快速确定性验收（pytest，`tests/test_packaging.py`，无网络、无真实证书、全 tmp_path）

脚本全部参数化，测试对**微型假 bundle**（几 KB 的伪造树 + `codesign -s -` ad-hoc 签名）执行：

| 测试 | 断言 |
|---|---|
| `test_plist_template_renders_all_keys` | 渲染后的 plist `plutil -lint` 过，2.1 全键在且非空 |
| `test_verify_flags_homebrew_reference` | 假 bundle 植入含 `/opt/homebrew/...` 的文件 → verify 非零且指认该文件 |
| `test_verify_flags_checkout_reference` | 植入 `--source-root` 路径串 → 非零 |
| `test_verify_flags_pyvenv_and_bin` | 植入 `pyvenv.cfg` / `pylibs/desk/bin/` → 非零 |
| `test_verify_passes_clean_fixture` | 干净假 bundle（ad-hoc 签、plist 齐、结构齐、桩 python 通过 V6 桩导入）→ 0 |
| `test_verify_reports_all_failures_at_once` | 植入两类问题 → 输出同时含两条 |
| `test_install_to_tmp_dest` | `--dest tmp` 落成完整 bundle；已存在异 id 同名目录时拒绝 |
| `test_uninstall_removes_app_and_plist` | tmp 假 `/Applications`、假 LaunchAgents、PATH 里 launchctl 桩 → app 与 plist 消失，桩记录到 bootout 调用 |
| `test_uninstall_keeps_data_by_default` | 无 `--purge-data` → data root 分毫未动 |
| `test_uninstall_purge_never_touches_models` | `--purge-data`：`models/` 内假权重、config 指向的**外部** models_root、邻位 `llms/` 目录三者全存活；其余（config、sessions、logs、outputs、history）消失 |
| `test_uninstall_purge_refuses_on_corrupt_config` | data root 里放损坏的 `config.json`（非 JSON / 缺 `models_root`）+ 自定义名假模型目录 → `--purge-data` 非零退出，**整树分毫未动** |
| `test_readme_states_real_behavior` | README 含 `0.0.0.0:8770` 与「无鉴权」事实陈述、默认模型目录路径；不含「推理不出门」、开机自启表述、四个已删旧脚本名（R-packaging-09 机检半；菜单栏行为归 reality gate） |
| `test_uninstall_dry_run_touches_nothing` | `--dry-run` 后整树 hash 不变 |
| `test_uninstall_wrong_bundle_id_refuses` | 假 app 的 id 不符 → 不删、非零 |
| `test_requirements_locks_are_pinned` | 三份锁每行为 `==` 钉死，且不含 `file://`、`/Users/`、`/opt/` |
| `test_no_legacy_scripts_in_repo` | R-packaging-08 五个旧脚本不存在（执行期删除后转绿） |

破坏性动作只对 tmp_path 假目录执行；测试代码不出现真实 `/Applications`、真实模型路径（授权红线）。

### 5.2 构建期自检（确定性但慢/需网，不进 pytest）

`scripts/build-app.sh && scripts/verify-app.sh dist/LocalModelDesk.app` ——
V1–V7 全绿即 R-packaging-01/02/03/04/05 的完整机器证明（V6 用内嵌解释器真实导入三套依赖）。

### 5.3 reality gate（人工 runbook，不得伪造）

1. `install-app.sh`（真 `/Applications`，人工执行）→ 双击启动；
2. 首运弹目录选择、可收编既有 339G；
3. 菜单栏状态正确；关窗不退；菜单栏 Quit 后 `lsof -iTCP:8766 -iTCP:8767 -iTCP:8770` 无监听；
4. 未公证提示：首启右键打开一次通过 Gatekeeper；
5. `uninstall-app.sh`（真机、人工）后 `launchctl print gui/$UID/com.aa.localmodeldesk` 报不存在、
   App 消失、模型原地未动。

---

## Assumptions（内部决定，未触碰模块边界/公共接口）

- **A1 bundle id**：`com.aa.localmodeldesk`，与既有 LaunchAgent 标签同源，卸载脚本按此标签 bootout。
- **A2 最低系统**：`LSMinimumSystemVersion = 15.0`（构建机 26.6.2；mlx 0.32 对新系统无上界要求，15.0 覆盖有余）。
- **A3 内嵌解释器**：uv 管理的 python-build-standalone `cpython-3.13.15`（与现役三个 venv 的解释器版本一致），一个解释器共享给三套 pylibs。
- **A4 三套 pylibs 分置**：镜像现状（`.venv-desk` / `.venv-music3` / uv tool `mlx-h3`），避免跨包依赖解析冲突；实测三者 mlx 同为 0.32.2，将来可合并但本轮不做（YAGNI）。
- **A5 entitlements 为空**：全部 Mach-O 用同一 Developer ID 签名，hardened runtime 库校验天然通过；MLX 走 Metal，不需要 JIT/unsigned-memory 豁免。若 reality gate 实跑发现需要豁免，加项属 packaging 内部改动。
- **A6 目录组织**：构建输入放新顶层 `packaging/`，可执行脚本按冻结约定放 `scripts/`，产物落 `dist/`（gitignore）。
- **A7 bundle 标记**：文件名 `Resources/bundle.json`、键如 §1.4；此为 packaging↔foundation 的实现层契约（公共面仍是 `api:resolvePaths`），以 foundation 设计文档最终键名为准，冲突时 packaging 从之。
- **A8 版本单点**：`packaging/VERSION` 同时供 `CFBundleShortVersionString` 与 `CFBundleVersion`。
- **A9 图标**：仓库检入 1024px PNG 占位图标，构建派生 icns；美术素材非本轮范围。
- **A10 `--adhoc` 签名模式**：仅供开发构建与测试 fixture 使用，让 `codesign --verify` 在无 Developer ID 环境也可测；正式构建默认走 Developer ID，不静默降级。
- **A11 uv 为构建机前置依赖**：仅构建期使用（取解释器与装依赖），产物内零引用，verify V3 的禁串扫描顺带证明这一点。
