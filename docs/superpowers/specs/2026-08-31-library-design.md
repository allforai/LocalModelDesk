# 模块设计：library

**日期** 2026-08-31
**对应 spec** `2026-08-31-library-spec.md`
**覆盖需求** R-library-01 … R-library-07
**替换现状** `media-gui/server.py` 中 `_append_history` / `_read_history` / `_outputs` / `_serve_media` /
`/api/chat/save` + `/api/chat/history`（单会话，写在代码目录），以及 `outputs/history.jsonl`、
`media-gui/chat-history.json` 两处落错位置的数据（census A14 / A15）。

---

## 架构

library 是纯持久化模块：三个互不依赖的 Store + 一个薄门面 + 一个与传输无关的 HTTP 适配层。
不做推理、不碰 arbiter、不认识 mlx-lm。所有路径来自 foundation（`api:resolvePaths` / `data:pathRoots`），
模块内不出现任何 `Path.home()` 或写死目录（R-library-07）。

```
desk/library/
  __init__.py     # 导出 LibraryService
  history.py      # HistoryStore   —— 作业历史 history.jsonl（追加式 JSONL）
  outputs.py      # OutputsStore   —— 成品列表 + Range 字节流（含纯函数 parse_range）
  sessions.py     # SessionStore   —— 多会话聊天，sessions/<id>.json 每会话一文件
  http.py         # 传输无关的请求处理函数 + 路由表（供服务组装层挂载）
```

分层原则：**Store 层只认 `Path` 与 dict，完全可用 `tmp_path` 单测**；`http.py` 只做
「参数解析 → 调 Store → 组 Response」，返回值是普通 dataclass，不依赖任何 socket / 框架，
同样可直接单测。真正把路由挂到 127.0.0.1:8766 的 HTTP 服务组装不属于本模块
（属于后续把各模块路由表合并起来的服务组装点）。

### 存储位置（消费 `data:pathRoots`，与 foundation 冻结目录约定一一对应）

| 数据 | 位置 | 来源字段 |
|---|---|---|
| 作业历史 | `<data root>/history.jsonl` | `pathRoots` 的数据根（foundation 约定文件名 `history.jsonl`） |
| 成品 | `<outputs root>/` | `pathRoots` 的 `outputs_root`（config 可配） |
| 聊天会话 | `<data root>/sessions/<id>.json` | `pathRoots` 的数据根（foundation 约定目录名 `sessions/`） |

`LibraryService(roots)` 在构造时把三个具体路径算好注入三个 Store；测试直接用 `tmp_path`
构造假 roots，绕过 foundation 真实现。

---

## 组件

### 1. `HistoryStore`（history.py）— R-library-03 / 04 / 07

```python
class HistoryStore:
    def __init__(self, history_file: Path): ...
    def append(self, entry: dict) -> dict     # 补齐 id/ts 后原子追加，返回完整 entry
    def list(self, limit: int | None = None) -> list[dict]  # 新→旧
    def by_output(self) -> dict[str, dict]    # 供 OutputsStore 合并用：output 文件名 → entry（跳过 output 为 null 的条目）
```

**`data:historyEntry` 契约**（media 通过 `api:appendHistory` 写入，逐字段）：

```json
{
  "id": "32位hex（library 生成）",
  "ts": "2026-08-31T10:11:12（library 生成，本地时间 ISO）",
  "kind": "video | music",
  "status": "done | failed | cancelled",
  "output": "h3-20260831-101112.mp4 | null（失败/取消可无产出）",
  "duration_s": 123.4,
  "error": "失败原因 | null",
  "params": { "…media 传入的全部参数原样保存，含 prompt…" }
}
```

- `append` 校验必填字段 `kind`、`status`（缺失抛 `ValidationError`，**不写半条**）；
  `id`、`ts` 缺省时由 library 填充；`params` 原样透传不做解释。
- **原子并发追加**（R-library-03）：Store 持一把 `threading.Lock`；每次 append 在锁内
  `json.dumps(entry) + "\n"` 先在内存组完整行，再以 `"a"` 模式打开、单次 `write`、关闭。
  单进程多线程下每行完整；服务是单进程（见 Assumptions）。
- `list`：逐行解析，**坏行跳过不报错、也绝不改写文件**（读宽容、写严格；进程崩溃留下的
  截断尾行不毒化整个历史）；按文件序反转即新→旧（追加即时序）；`limit` 截前 N 条。
- **R-library-04**：`list` 返回的 entry 里 `params` 原样在场，前端「再做一版」直接从
  `api:listHistory` 的结果取 `params` 回填，无需第二个取回接口（registry 中也没有）。

### 2. `OutputsStore`（outputs.py）— R-library-01 / 02

```python
class OutputsStore:
    def __init__(self, outputs_root: Path, history: HistoryStore): ...
    def list(self) -> list[dict]                       # api:listOutputs
    def resolve(self, name: str) -> Path | None        # 越权/缺失 → None
    def serve(self, name: str, range_header: str | None) -> Response  # api:serveOutput

def parse_range(size: int, header: str | None) -> RangePlan  # 纯函数，单独可测
```

**`api:listOutputs` 条目**（磁盘为准，历史做富化——覆盖孤儿文件）：

```json
{
  "name": "h3-20260831-101112.mp4",
  "kind": "video | music | file",
  "bytes": 8388608,
  "ts": "历史里的 ts；孤儿则取文件 mtime",
  "orphan": false,
  "history_id": "…| null"
}
```

- 扫描 `outputs_root` 一层，后缀 ∈ `{.mp4, .wav, .m4a, .webm}`（后两者兼容既有旧成品文件）；
  目录不存在返回 `[]` 不报错。
- 与 `HistoryStore.by_output()` 按文件名 join：有历史 → 取其 `kind/ts/id`；
  无历史 → `orphan: true`，`kind` 按前缀推断（`h3-`→video、`music3-`→music、其余→file）。
  历史里有、磁盘上没有的条目只出现在 `api:listHistory`（那是记录，不是成品）。
- 排序 `ts` 降序。

**路径安全（R-library-02 后半）**：`resolve(name)` 规则——URL 解码后的 name 含 `/`、`\`、
`..` 分段，或 `os.path.realpath(outputs_root / name)` 不以 `realpath(outputs_root) + os.sep`
开头，或目标不是普通文件 → `None`，HTTP 层回 404。symlink 逃逸也被 realpath 前缀检查拦住。

**Range（R-library-02）**：`parse_range` 按 RFC 7233 单区间实现，返回
`RangePlan(status, start, length)`：

| 输入 | 结果 |
|---|---|
| 无 Range / 非 `bytes=` 前缀 / 语法非法 / 多区间 | 200，整文件 |
| `bytes=a-b`（a ≤ b，a < size） | 206，`[a, min(b, size-1)]` |
| `bytes=a-`（a < size） | 206，`[a, size-1]` |
| `bytes=-n`（n > 0） | 206，末尾 `min(n, size)` 字节 |
| `bytes=a-` 且 a ≥ size；`bytes=-0`；size == 0 且带 Range | 416，`Content-Range: bytes */<size>` |

响应头：一律 `Accept-Ranges: bytes`；206 附 `Content-Range: bytes <start>-<end>/<size>`
与准确 `Content-Length`。Content-Type 按后缀：mp4→`video/mp4`、wav→`audio/wav`、
m4a→`audio/mp4`、webm→`video/webm`。

`serve` 返回的 `Response.body` 对文件流是 `FileSlice(path, start, length)` 描述符，
由服务组装层负责分块写 socket；单测直接读该切片断言字节与文件对应区间一致，无需起服务。

### 3. `SessionStore`（sessions.py）— R-library-05 / 06 / 07

```python
class SessionStore:
    def __init__(self, sessions_dir: Path): ...
    def list(self) -> list[dict]                                   # api:listChatSessions
    def create(self, title=None, model=None) -> dict               # api:createChatSession
    def update(self, session_id: str, patch: dict) -> dict         # api:updateChatSession
    def delete(self, session_id: str) -> None                      # api:deleteChatSession
```

**`data:chatSession` 契约**：

```json
{
  "id": "uuid4 的 32 位 hex",
  "title": "新会话 | 用户改名",
  "model": "所用模型 key | null",
  "created": "ISO 时间",
  "updated": "ISO 时间",
  "messages": [ { "role": "user|assistant", "content": "…", "reasoning": "…可选" } ]
}
```

- 每会话一个文件 `sessions/<id>.json`；`id` 由 library 生成（`uuid4().hex`），
  `update`/`delete` 先用 `^[0-9a-f]{32}$` 校验 id，不匹配按不存在处理（顺带杜绝路径注入）。
- **写入原子**：同目录临时文件 + `os.replace`（与 R-foundation-06 同款手法）；
  序列化失败时旧文件完好。Store 内一把 `threading.Lock` 串行化写。
- `create`：生成 id、`created`/`updated`、空 `messages`；`title` 缺省 `"新会话"`；落盘后返回。
- `update`：patch 允许键 `title`（重命名）、`model`、`messages`（整体替换）；
  其他键抛 `ValidationError`；`messages` 必须是 list（内部结构 library 不解释，原样存）；
  每次 update 刷新 `updated`。id 不存在抛 `NotFoundError`——**不静默新建**。
- `delete`：删除该文件即删除持久化（R-library-06 后半）；id 不存在抛 `NotFoundError`。
- `list`：读目录下全部 `*.json`，返回**完整** `data:chatSession` 对象数组，按 `updated`
  降序——前端切换会话直接用 list 结果，无需单独 get 接口（registry 无 get；见 Assumptions）。
  某文件损坏时返回 `{"id": "<文件名>", "corrupt": true}` 占位——不隐藏、不伪造、不整表失败。
- 「重启后仍在」：状态全在磁盘，Store 无内存缓存，重新构造对象读同一目录即还原（R-library-06）。

### 4. `LibraryService`（__init__.py）与 `http.py`

`LibraryService(roots)`：装配三个 Store，按 registry 名暴露 Python 方法
（`append_history` ↔ `api:appendHistory` 等）。**media 走进程内 Python 调用**
`append_history`（同进程无需 HTTP），UI 走 HTTP。

**旧历史一次性收编（census A15，library 自己承担）**：构造时若
`<data root>/history.jsonl` **不存在** 且 `<outputs root>/history.jsonl` **存在**
（现状代码把历史写在 outputs 目录内；用户把 `outputs_root` 指回旧 outputs 目录即命中），
则把后者**逐字节复制**到数据根——只 copy，**绝不移动、绝不删除源文件**（outputs 目录
冻结不可动），复制经 同目录临时文件 + `os.replace` 落地。目标已存在则什么都不做
（幂等；不合并、不覆盖用户已有新历史）。两个路径均来自 `pathRoots`，无硬编码。
旧格式行可被 `list` 直接读取（字段同源，缺 `id` 的旧行照常展示，宽容读）。

`http.py` 路由表（挂载点前缀由服务组装层统一，路径为本模块对 ui 的契约）：

| registry | 方法与路径 | 请求 | 响应 |
|---|---|---|---|
| `api:listOutputs` | `GET /api/outputs` | — | 200 条目数组 |
| `api:serveOutput` | `GET /api/outputs/<name>` | `Range` 头可选 | 200/206/416 字节流；逃逸/缺失 404 |
| `api:listHistory` | `GET /api/history?limit=N` | — | 200 `historyEntry` 数组（新→旧） |
| `api:listChatSessions` | `GET /api/sessions` | — | 200 `chatSession` 数组 |
| `api:createChatSession` | `POST /api/sessions` | `{title?, model?}` | 200 新 `chatSession` |
| `api:updateChatSession` | `PATCH /api/sessions/<id>` | `{title? \| model? \| messages?}` | 200 更新后对象；404/400 |
| `api:deleteChatSession` | `DELETE /api/sessions/<id>` | — | 200 `{"deleted": id}`；404 |

`api:appendHistory` 不设 HTTP 端点：registry 中它的唯一消费者是 media（进程内），
不给 0.0.0.0 侧多开一个可写面。

处理函数签名统一为 `handler(request: LibRequest) -> Response`，
`LibRequest = (path_params, query, headers, json_body)`、
`Response = (status, headers, body: bytes | FileSlice)`，两者皆 dataclass——测试直接构造。

---

## 数据流

```
media 作业结束 ──(进程内)── append_history(entry) ──锁内单次写──▶ history.jsonl
UI 素材库面板 ── GET /api/history ── HistoryStore.list ──▶ entry[]（params 原样，供回填）
UI 素材库面板 ── GET /api/outputs ── 扫盘 ⋈ by_output() ──▶ 成品[]（孤儿 orphan:true）
UI 播放器    ── GET /api/outputs/<name> + Range ── resolve→parse_range ──▶ 206 + FileSlice
UI 聊天面板  ── /api/sessions CRUD ── SessionStore ──临时文件+os.replace──▶ sessions/<id>.json
```

会话消息的写入路径：前端在每轮流式回复完结后把整份 `messages` 通过
`api:updateChatSession` 写回（与现状 `/api/chat/save` 的整体覆盖语义一致，只是多会话化、
原子化、挪到数据根）。

---

## 错误处理

统一异常层级 `LibraryError` → `NotFoundError` / `ValidationError`；
http.py 映射：`NotFoundError`→404、`ValidationError`→400、Range 不可满足→416、
其余 `OSError` 原样冒泡为 500 并带 `{"error": str(exc)}`。原则对齐冻结约定：**错误就是错误**。

| 情形 | 行为 |
|---|---|
| 成品 name 逃逸 / 不存在 / 不是普通文件 | 404，绝不读 outputs 根之外（R-library-02） |
| Range 语法非法 | 按无 Range 处理，200 全量（RFC 允许忽略） |
| Range 不可满足 | 416 + `Content-Range: bytes */<size>` |
| appendHistory 缺 `kind`/`status` | `ValidationError`，一个字节都不落盘 |
| history.jsonl 内坏行 | list 跳过；文件永不被改写 |
| 会话 id 不存在 / 格式非法 | `NotFoundError`（update 不静默新建，delete 不假装成功） |
| update patch 带未知键 / messages 非 list | `ValidationError` |
| 请求体非合法 JSON（POST/PATCH） | `ValidationError` → 400（http.py 在调 Store 前解析并拦截） |
| 会话文件损坏 | list 中以 `corrupt: true` 占位呈现，单文件损坏不拖垮整表 |
| 写盘 OSError（磁盘满等） | 冒泡 500；os.replace 原子性保证旧文件完好 |

---

## 测试

全部 pytest + `tmp_path`，零真实路径、零网络、零推理，确定性快跑（对齐 spec 验收取向）。

`tests/test_library_history.py`
- append 补齐 `id`/`ts`；params 原样往返（R-library-04）。
- 并发：8 线程 × 50 条 append，断言恰 400 行、每行 `json.loads` 成功、每条 id 唯一（R-library-03）。
- 缺 `kind` 抛 ValidationError 且文件行数不变。
- 手工插入坏行 + 截断行，list 跳过且文件字节不被改写；limit 与新→旧排序。
- 旧历史收编：`tmp_path` 下造 `outputs/history.jsonl`、数据根无历史 → 构造 LibraryService 后
  数据根出现同字节副本、源文件原封不动；数据根已有历史 → 源不动、目标不被覆盖（幂等，A15）。

`tests/test_library_outputs.py`
- `parse_range` 表驱动：全量 / `a-b` / `a-` / `-n` / 越界 416 / 非法回退 200 / 空文件 416。
- serve 断言：206、`Content-Range`、`Content-Length`、FileSlice 读出的字节与源文件
  对应区间逐字节相等；`bytes=0-1023` 恰 1024 字节。
- 逃逸用例：`../x`、绝对路径、`%2e%2e%2f` 解码后、指向根外的 symlink → 全部 404（R-library-02）。
- 孤儿：磁盘放 `h3-x.mp4` 无历史 → 出现在 list 且 `orphan: true`、kind 推断正确；
  有历史的成品带 `history_id`；历史有而磁盘无的不出现在 outputs（R-library-01）。

`tests/test_library_sessions.py`
- create → list → update(改名/换 model/替换 messages) → delete 全往返（R-library-05）。
- 「重启」：同目录重新构造 SessionStore，会话与消息俱在；delete 后文件确实消失（R-library-06）。
- 未知 id / 非法 id（`../../x`）→ NotFoundError；未知 patch 键 → ValidationError。
- 原子性：注入序列化失败（不可 JSON 化对象），断言旧文件内容完好。
- 损坏文件 → list 出现 `corrupt: true` 占位，其余会话正常。

`tests/test_library_http.py`
- 直接构造 LibRequest 调 http.py 处理函数，断言状态码与 JSON 形状（404/400/416 映射各一例，
  含请求体非法 JSON → 400）。

`tests/test_library_no_stray_writes.py`（R-library-07 的强制点——「不写代码目录」是禁止性
需求，仅靠 tmp_path 用例证明不了没有旁路写）
- 把 cwd 切到另一个只读 `tmp_path`（`chmod 500`），用独立 roots 跑一遍
  append/list/serve/session CRUD 全流程，事后断言只读目录仍为空且 roots 之外无新文件——
  任何写死相对路径或 cwd 写入都会在此炸掉。
- 静态断言：`desk/library/` 源码内不含 `Path.home(`、`expanduser(`、以 `/Users`、
  `/Applications`、`~` 开头的路径字面量（存储位置只能来自注入的 roots）。

验收命令：`python3 -m pytest tests/test_library_*.py -q` —— 无 reality gate，本模块全部可自证。

---

## Assumptions（模块内部决定，均不改变边界/接口/范围）

1. **单进程假设**：历史与会话的并发安全按「一个 desk 服务进程、多线程」设计
   （threading.Lock + 单次 write / os.replace）。App 形态即单实例内嵌服务，无跨进程写者。
2. **`api:appendHistory` 仅进程内 Python 调用**，不开 HTTP 端点——registry 内其唯一消费者
   media 与 library 同进程，且不向无鉴权监听面多暴露一个写接口。
3. **`api:listChatSessions` 返回完整会话（含 messages）**：registry 无单独 get 接口，
   本地会话量级（几十个、每个 ≤ 数十条消息）下整表返回成本可忽略，避免发明新接口。
4. HTTP 具体路径（`/api/outputs`、`/api/history`、`/api/sessions/...`）是 library 对 ui 的
   模块内契约；registry 只约束 `api:*` 语义名，不约束 URL。
5. 消息内部结构（role/content/reasoning）library 不校验、原样存取；其语义由 llm/ui 约定。
6. 成品后缀集合 `{.mp4, .wav, .m4a, .webm}`：前两个是 media 的产出约定，后两个兼容
   outputs 目录里既有旧文件（现状代码同款集合）。
7. `pathRoots` 消费方式：取 `outputs_root` 与数据根两个字段；`history.jsonl` 文件名与
   `sessions/` 目录名遵循 foundation spec 冻结的目录约定（该约定由 foundation 定义、
   本模块消费，不构成新路径硬编码点）。
8. 时间戳一律本地时间 `%Y-%m-%dT%H:%M:%S` ISO 字符串，与现状 history.jsonl 一致；
   旧历史的落位由本模块的一次性收编（§4）完成——foundation/packaging 均不做此事，
   library 是 census A15 的唯一承担者。
9. **旧单会话聊天 `media-gui/chat-history.json` 不自动导入**（census A14）：它位于代码
   目录，`pathRoots` 里没有任何字段能指向它，App 形态下代码目录也不可依赖；A14 的
   动作「移到用户数据根、改多会话」由 SessionStore 的新存储设计整体承担。旧文件
   原地保留、绝不删除（删除旧文件属 packaging A18 清理范畴），用户如需旧内容可
   自行查看该 JSON——不做静默丢弃，也不伪造成一个「迁移完成」。
