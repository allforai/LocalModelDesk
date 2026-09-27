# 媒体会话遗留 Minor 修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉 GitHub issues #16–#20 中仍成立的媒体会话遗留问题（先修用户可见的），并按条目关闭 issue。

**Architecture:** 按 issue 分任务：#19 跨会话引用与选择框（前端）→ #18 会话控制器与卡片（前端）→ #16 作业与拼接健壮性（后端）→ #17 ffmpeg 原语去重与加锁（后端）→ #20 测试缺口与 e2e 假执行器 → 关闭 issue。每个任务自带测试；不改 spec 规定的用户可见文案，除非本计划明确给出新文案。

**Tech Stack:** Python（pytest）、原生 ES module（`node --test`）、Playwright e2e、ffmpeg。

**Spec:** GitHub issues #16、#17、#18、#19、#20（`gh issue view <n>`，条目带 main `889836d` 上的 file:line）；行为规则的上游 spec：`docs/superpowers/specs/2026-09-25-media-sessions-base-design.md`（B-xx）、`2026-09-27-music-sessions-design.md`（M-xx）、`2026-09-27-video-sessions-design.md`（V-xx）、`2026-09-27-video-soundtrack-design.md`（S-xx）。

## Global Constraints

- 图片页零回归：`tests/js/image_pane.test.js` 断言不改。
- B-33：启动前任一步失败都不写会话——**不因本计划改变**。
- 新文案（逐字）：选择框读列表失败「会话列表读不出来：<原因>」；引用查询网络失败时首帧/参考图/歌说明保持原选择不变，页面错误行显示「暂时读不到图片会话，请稍后重试」（音乐为「暂时读不到音乐会话，请稍后重试」）；拼接读不出时长「读不出第 N 段的时长，无法拼成成片」（`joined_error.code = "join_failed"`）。
- 输出文件名：`h3-<stamp>-<8hex>.mp4`、`music3-<stamp>-<8hex>.wav`（与 joined/compose 同式）。
- 测试命令：`node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`（`tests/test_shell_window.py` 4 个间歇环境失败除外）；改 `desk/static` 必跑 `python3 -m pytest tests/e2e -q`。
- 提交中文 `fix(media-sessions): …` / `refactor(media-sessions): …` / `test(media-sessions): …`，结尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`；提交信息里引用 issue 号（如「#19」），不写 `Fixes`（关闭在 Task 6 统一做）。

## Review Focus

1. **引用查询失败 ≠ 引用已失效**：网络错误时不得清空用户已选的首帧/参考图/歌 —— Task 1「transient lookup keeps selection」。
2. **快速双击「重新拼接」**：只发一个合成请求 —— Task 2「double rejoin sends once」。
3. **取消拼接时 ffmpeg 句柄抛异常**：落定为 `join_cancelled` 而不是 `join_failed` —— Task 3。
4. **同一秒内两个同类作业**：输出文件名不同 —— Task 3。
5. **选择框里歌的分段文件已删但成片还在**：不再显示为可选（与后端 `find_done` 一致）—— Task 1。

---

### Task 1: #19 跨会话引用与选择框

**Files:** Modify `desk/static/js/panes/video.js`（`loadLinked` ~108-113、`checkMissing` ~317-323、引用校验调用处）、`desk/static/js/widgets/media_picker.js`（`musicOutput` 9-12、会话列表加载 161-171）；Test `tests/js/video_pane.test.js`、`tests/js/media_picker.test.js`

**Interfaces:** Produces `loadLinked(kind, id) → session | null | undefined`：`null` 表示 404（真的不在），`undefined` 表示读取失败（未知）；缓存只存成功与 404。`musicOutput(attempt)` 语义改为：本段 `output` 在（`!output_missing`）才可选，返回值优先未缺失的 `joined_output`，否则 `output`。

- [ ] **Step 1: 失败测试**
  - `video_pane.test.js`「transient lookup keeps selection」：已选图片会话首帧后，「在这段基础上改」一个 ref 首帧的尝试，而 `GET /api/media-sessions/image/<id>` 返回 500 → 首帧说明仍为「首帧：图片会话「…」第 N 次」（或回填前的说明），不出现「引用的图片已不在」，错误行「暂时读不到图片会话，请稍后重试」；同样场景返回 404 → 仍显示「引用的图片已不在」并清空（原行为）。对歌（music_ref）同样两条，文案「暂时读不到音乐会话，请稍后重试」/「引用的歌已不在」。
  - `video_pane.test.js`「refine target gone shows chip missing」：「在这段基础上改」一个续写段（有 `continues`）后，会话刷新时它的前段 `output_missing` → 提示条显示「第 N 次的文件已不在，不能接着往下生」，「生成视频」禁用（与续写型一致）。音乐页同理（`music_pane.test.js`，文案「不能接着写」）。
  - `media_picker.test.js`：`listSessions` reject（`new Error("网络断了")`）→ 对话框显示「会话列表读不出来：网络断了」，「取消」返回 null，无未处理 rejection（用 `process.on("unhandledRejection")` 计数断言为 0）；音乐项 `output_missing: true, joined_output: "j.wav"` → 不出现在列表。
- [ ] **Step 2:** `node --test tests/js/video_pane.test.js tests/js/media_picker.test.js` → FAIL
- [ ] **Step 3: 实现**

```js
// video.js
async function loadLinked(kind, id) {
  const key = `${kind}/${id}`;
  try { linkedSessions.set(key, await api.getMediaSession(kind, id)); }
  catch (error) {
    if (error?.status === 404) linkedSessions.set(key, null);
    else return undefined;            // 读取失败：不缓存，不当作「已不在」
  }
  return linkedSessions.get(key);
}
```

  各引用校验点：`undefined` → 保留当前选择、`setError("暂时读不到图片会话，请稍后重试")`（音乐同理）；`null` 或找不到尝试 → 原「已不在」逻辑。`linkedForCard` 遇 `undefined` 不写缓存、下次渲染再试（加一个 5 秒内不重复请求的时间戳防抖，`linkedLoading` 已有去重）。
  `checkMissing`：`ref.type === "refine"` 且 `ref.continues` 时，也检查 `ref.continues` 指向的尝试是否 `canContinue`，否则 `ref.missing = true`；提示条文案走 `chipText({type:"continue", index: <前段序号>, missing:true})`。音乐页 `music.js` 的 `checkMissing` 同样补上。

```js
// media_picker.js
export function musicOutput(attempt) {
  if (typeof attempt?.output !== "string" || !attempt.output || attempt.output_missing) return null;   // 与后端 find_done 一致
  if (typeof attempt.joined_output === "string" && attempt.joined_output && !attempt.joined_missing) return attempt.joined_output;
  return attempt.output;
}
```

  列表加载 IIFE 包 `try/catch`：失败时在会话栏位置显示一行 `.inline-error`「会话列表读不出来：<error.message>」，右侧空；「取消」照常。
- [ ] **Step 4:** `node --test tests/js/`；`python3 -m pytest tests/e2e/test_video_sessions.py tests/e2e/test_video_soundtrack.py -q`
- [ ] **Step 5: Commit** `fix(media-sessions): 引用读不到不再当作已删除；选择框读列表失败有提示、可选歌与后端一致（#19）`

---

### Task 2: #18 会话控制器与卡片

**Files:** Modify `desk/static/js/panes/media_session.js`（`prunePicks` 453、`exitPicking` 567-572、`startCompose` 586-600、`renderCard` 调用参数）、`desk/static/js/widgets/music_session_card.js`、`desk/static/js/widgets/video_session_card.js`、`desk/static/js/pure/media_session.js`、`desk/static/js/pure/music_session.js`、`desk/static/js/pure/video_session.js`、`desk/static/js/panes/music.js`、`desk/static/js/panes/video.js`；Test `tests/js/media_session_pane.test.js`、`tests/js/music_pane.test.js`、`tests/js/video_pane.test.js`、`tests/js/media_session.test.js`

**Interfaces:** Produces `pure/media_session.js`: `positionOf(attempts, id) → number`（-1 表示不在）、`pickBadge(index) → string`（0–19 圈码 ①–⑳，≥20 为 `(${index+1})`）；`widgets/segment_switch.js`（新建）`renderSegmentSwitch(doc, {labels:[a,b], checked, onChange}) → node`（radiogroup + ArrowLeft/ArrowRight/Home/End 切换并聚焦）；`renderCard` 参数新增 `actionsBlocked: string`（为空表示可用，否则为不可用原因，同 IS §7.6）。

- [ ] **Step 1: 失败测试**
  1. 「double rejoin sends once」：点两次「重新拼接」（第一次未返回前）→ `POST /api/media/compose` 只一次。
  2. 有作业在跑时「重新拼接」按钮 `disabled`，`title` 为忙碌原因。
  3. 挑选模式中某已选尝试在会话刷新后变 `output_missing` → 合成栏列表与「合成（K 段）」同步减少（不需用户再操作）。
  4. `exitPicking`（「取消」）后焦点在「挑几段合成…」按钮。
  5. 展开的续写段：成片 `<audio>` 触发 `error` → 播放器切回本段 `output`、隐藏「成片 | 只听这一段」切换、卡片不标「文件已不在」、「接着写下一段」仍可用；本段 `<audio>` error → 仍按原规则标文件不在（视频同理）。
  6. `pickBadge(0) === "①"`、`pickBadge(19) === "⑳"`、`pickBadge(20) === "(21)"`。
  7. 切换会话后 `brokenIds` 清空（先在会话 A 标 broken，切到 B 再切回 A 并刷新，文件已恢复时该段可续写）。
  8. 分段切换：焦点在「成片」按 ArrowRight → 「只听这一段」`aria-checked="true"` 并获得焦点、播放源切换；ArrowLeft 回来。
- [ ] **Step 2:** `node --test tests/js/` → 新用例 FAIL
- [ ] **Step 3: 实现**
  - `startCompose`：入口 `if (pending || currentAvailability().disabled) return;`。控制器把 `currentAvailability()` 的 `disabled ? reason : ""` 作为 `actionsBlocked` 传给 `renderCard`；两张卡片的「重新拼接」按钮在 `actionsBlocked` 非空时 `disabled` 且 `title = actionsBlocked`（有 `problem.reason` 时 reason 优先）。
  - `renderTimeline` 里把 `prunePicks()` 换成：`const before = picks.length; prunePicks(); if (picks.length !== before) renderPicks();`。
  - `exitPicking`：末尾 `compose.startBtn.focus?.()`（仅在由用户操作退出时；`startCompose` 成功后的退出不抢焦点——加参数 `{focus = true}`，成功路径传 `false`）。
  - 卡片 `player()`：成片源出错时 `audio.src = serveOutput(attempt.output)`、移除切换控件，不调用 `onBroken`；只有当前源就是本段 `output` 时出错才调用 `onBroken`。视频卡片同理。
  - `pickBadge`、`positionOf` 放 `pure/media_session.js`，两张卡片与 `music_session.js`、`video_session.js` 的 `cardTitle`/`chainLine` 改用 `positionOf`（删除各自内联的 `position`）；`cardTitle` 合并为 `pure/media_session.js` 的 `sessionCardTitle(attempt, index, attempts, {composeWord = "合成"})`，音乐/视频的 `cardTitle` 删除并改调用它（视频的配乐标题分支保留在 `video_session.js`，先判断 op soundtrack 再回落到通用函数）。
  - `renderSegmentSwitch` 取代两张卡片里的手写 radiogroup。
  - `music.js`/`video.js` 的 `onSessionSwitch` 里 `brokenIds.clear()`。
- [ ] **Step 4:** `node --test tests/js/`；`python3 -m pytest tests/e2e -q`
- [ ] **Step 5: Commit** `fix(media-sessions): 重新拼接受忙碌门控、合成栏随刷新同步、成片坏了退回单段播放等（#18）`

---

### Task 3: #16 作业与拼接健壮性

**Files:** Modify `desk/media/service.py`；Test `tests/test_media_continue.py`、`tests/test_media_service.py`、`tests/test_media_music_ref.py`、`tests/test_media_video_refs.py`

**Interfaces:** Produces 输出名带 8hex；`_run_join` 取消分类；`_join_command` 读不出时长抛 `JoinInputError(n)`（模块内异常，`_run_join` 映射为 join_failed + 新文案）。

- [ ] **Step 1: 失败测试**
  1. `test_media_continue.py`「cancel while join handle raises」：`join_script` 用一个 `wait()` 抛 `RuntimeError` 的 handle，在拼接阶段 `cancel_job()` → 尝试 `done` + `joined_error.code == "join_cancelled"`。
  2. 「unreadable wav duration」：音乐续写，patch `wav_seconds` 对第 1 段返回 `None` → `joined_error == {"code":"join_failed","message":"读不出第 1 段的时长，无法拼成成片"}`，不 spawn ffmpeg 拼接。
  3. `test_media_service.py`：固定时钟下连续两次视频作业（第一次完成后立即第二次）输出名不同，均匹配 `^h3-\d{8}-\d{6}-[0-9a-f]{8}\.mp4$`；音乐同理 `^music3-…\.wav$`。更新所有断言固定输出名的旧测试（按正则或读取 `snap["output"]`，不放宽其它断言）。
  4. `test_media_continue.py`「frame cleanup on non-MediaError」：patch `_resolve_refs` 抛 `RuntimeError` → 请求抛出、`.inputs/` 中无新增 png。
  5. 「busy before frame extraction」：有作业在跑时发续写请求 → 409 `media_busy`，`subprocess.run`（截帧）未被调用。
  6. `test_media_video_refs.py`：`mode="image"` 带 `refs.ref_image` → 400 且文案为引用名不被允许的「引用参数有误：ref_image」（由 `_check_ref_names` 给出），不是「素材与生成模式不匹配」。
  7. `test_media_service.py`：`start_video_job(..., seed=None, force="x")` 校验失败时 `secrets.randbelow` 未被调用（monkeypatch 计数）；图片、音乐同理。
- [ ] **Step 2:** 运行确认失败。
- [ ] **Step 3: 实现**
  - 输出名：`h3-{stamp}-{uuid.uuid4().hex[:8]}.mp4`、`music3-{stamp}-{uuid.uuid4().hex[:8]}.wav`（`_start` 474、487 行附近）。
  - `_run_join`：`except Exception` 分支先 `with self._lock: cancelled = self._cancel_requested`，若取消 → 删 target、返回 `JOIN_CANCELLED`；`_run_join` docstring 补一句「依赖 join 期间 `_state.status` 保持 running，`_cancel_requested` 才只属于本作业」。
  - `_join_command` 音乐分支：逐段 `wav_seconds(path)`，为 `None` 时抛 `JoinInputError(n)`（1 起）；`_run_join` 捕获它返回新文案的 join_failed，不 spawn。
  - `start_video_job`：截帧前加轻量忙碌预检 `with self._lock: busy = self._state["status"] == "running"`，忙则抛 `media_busy`（`_start` 内的检查保留）；`except MediaError:` 清理改为 `except Exception:`（清理后原样 re-raise）。
  - `from_ref`：`(mode == "image" and wants_ref_frame) or (mode == "music_ref" and "ref_image" in ref_names)`。并把 `_check_ref_names(refs, VIDEO_REF_NAMES[mode])` 上移到 `_video_assets` 素材检查之前（它属于参数校验，仍在会话检查之前，符合 B-32「参数 → 会话」顺序），这样不被允许的引用名先得到「引用参数有误：<名称>」。
  - 三个 `start_*_job`：`_check_seed(seed)` 只在全部参数校验通过后调用；先单独校验 seed 合法性（不抽随机数）：新增 `_validate_seed(seed)`（None 通过，非法抛），`_check_seed` 改为 `_validate_seed(seed); return seed if seed is not None else secrets.randbelow(2**32)`，在校验末尾调用。
- [ ] **Step 4:** `python3 -m pytest -q --ignore=tests/e2e`
- [ ] **Step 5: Commit** `fix(media-sessions): 拼接取消与时长读失败的分类、输出名防撞、截帧前先查忙碌等（#16）`

---

### Task 4: #17 ffmpeg 原语去重与加锁

**Files:** Modify `desk/media/compose.py`、`desk/media/inputs.py`、`desk/media/service.py`；Test `tests/test_media_compose.py`、`tests/test_media_compose_job.py`、`tests/test_media_inputs.py`

**Interfaces:** Produces `compose.find_tool(name) -> str | None`（覆盖变量有效用它；无效则**退回 PATH**；都没有返回 None）；`inputs._tool(name, default)` 改为 `compose.find_tool(name) or default or name`；`compose.probe_size` 超时抛 `ValueError`；service 内 `_run_to_input(builder, suffix, code, message) -> Path`；`_drop_flags(items) -> list[bool]`；`_join_command(kind, parts, target, ffmpeg, size=None)`（`ffmpeg` 必填，视频 `size` 可预先给）。

- [ ] **Step 1: 失败测试**
  - `test_media_compose.py`：`LOCALMODELDESK_FFMPEG` 指向不存在的文件、PATH 有 ffmpeg → `find_tool("ffmpeg")` 返回 PATH 上的；`probe_size` 在 `subprocess.run` 抛 `TimeoutExpired` 时抛 `ValueError`。
  - `test_media_inputs.py`：`_tool("ffprobe")` 与 `compose.find_tool("ffprobe")` 对同一环境给出同一结果（覆盖有效/无效两种）。
  - `test_media_compose_job.py`「probe outside lock」：patch `compose.probe_size` 为阻塞 0.5 秒的函数，另起线程调用 `start_compose_job`，期间主线程 `job_status()` 在 0.1 秒内返回。
- [ ] **Step 2:** 确认失败。
- [ ] **Step 3: 实现**
  - `compose._find` 改名 `find_tool` 并按接口退回 PATH；`ffmpeg_path()/ffprobe_path()` 调它；`inputs._tool` 用它。
  - `probe_size` 捕获 `subprocess.TimeoutExpired`/`OSError` → `ValueError`。
  - `_run_to_input`：抽出 `_extract_last_frame` 与 `_clip_audio` 共同的「建 `.inputs` → 运行（60 秒超时）→ 判定 → 失败删文件抛 `MediaError(code, message, 500)`」；两处改调用它（`_clip_audio` 的时长与 ffmpeg 可用检查留在自身）。
  - `_drop_flags(items)`：`[False] + [items[i].get("continues") == items[i-1]["id"] for i in range(1, len(items))]`，`_join_plan` 与 `start_compose_job` 共用。
  - `_join_command`：删除 `ffmpeg or compose.ffmpeg_path()`，`ffmpeg` 必填；视频接受 `size`。`start_compose_job` 在调用 `_start` **之前**（不持锁）算 `size = compose.probe_size(...)`（失败 → 500 `spawn_failed` 前的同一路径：抛 `MediaError("join_failed", "读不出第一段的画面尺寸", 500)`，不写会话），把 size 捕获进 `compose_command` lambda。
- [ ] **Step 4:** `python3 -m pytest -q --ignore=tests/e2e`
- [ ] **Step 5: Commit** `refactor(media-sessions): ffmpeg 查找单一来源、截取与丢帧规则去重、探测尺寸移出锁外（#17）`

---

### Task 5: #20 测试缺口与 e2e 假执行器

**Files:** Modify `desk/testing/fakes.py`（`FakeMediaExecutor.spawn` 233-239）、`desk/testing/`（脚本对象）；Test `tests/test_media_service.py`、`tests/test_media_compose_job.py`、`tests/test_media_continue.py`、`tests/test_media_inputs.py`、`tests/test_media_image_service.py`、`tests/test_media_compose.py`、`tests/test_media_music_ref.py`、`tests/test_media_video_refs.py`、`tests/js/video_session.test.js`、`tests/js/media_picker.test.js`、`tests/test_e2e_fakes.py`、新 `tests/e2e/test_join_failure.py`

**Interfaces:** Produces e2e 脚本 API：`script.fail_next_ffmpeg(code=1)`——下一次无 `--output` 的命令以该退出码结束且不写输出（之后恢复自动成功）。

- [ ] **Step 1: 补测试（逐条对应 #20 清单，均为新增或收紧断言，不改产品代码）**
  1. `test_bad_video_or_music_seed_is_400`：音乐分支断言 `(code, message) == ("invalid_params", "种子须为 0–4294967295 的整数")`。
  2. `test_media_compose_job.py`：续写对（b continues a）合成 → 生成图含 `[1:v]trim=start_frame=1`；`kind="music"` 合成成功（输出 `music3-compose-*.wav`、命令含 `acrossfade`）；片段文件被删 → 404 `segment_missing`。
  3. `close()` 发生在拼接阶段（`join_script="block"`）→ 尝试 `done` + `join_cancelled`，`close()` 返回前已落定；拼接失败时 history 条目无 `joined_output` 键。
  4. `media_picker.test.js`：打开后焦点在第一个会话按钮；快速从会话 A 切到 B 时，A 的迟到响应不覆盖 B 的内容（让 A 的 `getSession` 晚于 B resolve）。
  5. `test_media_inputs.py:81`、`test_media_image_service.py:61`：`pytest.raises` 收紧为断言具体 `code`（按各参数化用例实际值）。
  6. `video_session.test.js`：`readVideoParams` 非法画幅 →「高级参数里的数值有误：画幅无效」、非法时长 →「高级参数里的数值有误：视频时长无效」。
  7. `test_soundtrack_command…`：断言 `-map 0:v -map 1:a` 相邻出现。
  8. `test_media_music_ref.py`：组合失败（引用的歌已删 + 有作业在跑）→ 404 `ref_missing`（S-02 顺序：引用在 busy 之前）。
  9. `test_media_video_refs.py`：`mode="text"` 带 `refs.ref_audio` 或 `refs.ref_image` → 400 `invalid_params`。
- [ ] **Step 2: e2e 假执行器**：`fakes.py` 加脚本方法 `fail_next_ffmpeg(code=1)`（布尔/计数标志），`spawn` 对无 `--output` 命令在标志置位时返回 `FakeMediaHandle([Exit(code)], output_path, …)` 并清标志；`tests/test_e2e_fakes.py` 加单测。
- [ ] **Step 3: 新 e2e `tests/e2e/test_join_failure.py`**（夹具照 `tests/e2e/test_music_sessions.py`）：音乐页生成一段 → `script.fail_next_ffmpeg()` → 「接着写下一段」生成 → 卡片出现「这一段生成好了，但成片没拼成：拼接成片失败」与「重新拼接」按钮 → 点「重新拼接」→ 合成卡片出现。
- [ ] **Step 4:** 全量三组测试。
- [ ] **Step 5: Commit** `test(media-sessions): 补齐评审遗留的测试缺口，e2e 可脚本化拼接失败（#20）`

---

### Task 6: 关闭 issue

- [ ] **Step 1:** 对 #16–#20 逐个 `gh issue comment <n> --body …`：列出每个清单条目的处理结果（已修：提交短 SHA；不改：原因），其中 #16 的三条不改项写明：
  - 白名单外参数键不记 null：没有调用方依赖「未传」与「空值」的区别，保持现状。
  - 合成/配乐在启动阶段失败不挂会话尝试：这是 B-33「启动前任一步失败都不写会话」的规定，错误已在界面错误行显示。
  - `_resolve_paths` 早于能力检查导致配置损坏时错误顺序：配置损坏在应用启动时即进入致命错误页（R-config-corrupt-01），作业接口实际到不了这一步，不改。
- [ ] **Step 2:** 更新 issue 正文的勾选框（`gh issue edit <n> --body-file`，把已处理条目改成 `- [x]`，不改项加「（不改：原因）」）。
- [ ] **Step 3:** 合并到 main 并推送后 `gh issue close <n> --comment "已在 <merge sha> 修复"`。
