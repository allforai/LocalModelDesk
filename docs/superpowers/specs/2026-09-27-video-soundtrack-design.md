# 模块设计：视频配乐（video-soundtrack，第 3b 块）

**日期** 2026-09-27
**来源** 用户 2026-09-24/25 决定「D 两种都要」（D1 参考音频实验性、D2 换音轨默认），2026-09-27「全部按照推荐来」。
**上游** `2026-09-27-video-sessions-design.md`（V-xx）、`2026-09-25-media-sessions-base-design.md`（B-xx）、spike 结论（B §0.3：`--ref-audio` 须 2–15 秒且必须同时有参考图或参考视频；参考素材不能与首帧/尾帧同用）。

每条 **[S-xx]** 可写成测试断言。

---

## 0. 范围与非目标

- 范围：D2 换音轨作业与界面；D1「配乐参考（实验性）」生成方式；通用媒体选择框。
- [S-00a] 不做音乐页反向入口（「给视频配乐」）。
- [S-00b] 不做配乐起止/淡入淡出调节（D2 从歌的第 0 秒开始）。
- [S-00c] 不新增内存硬拒绝；D1 估算同普通视频。
- 台面未发布，不谈兼容。

---

## 1. D2 换音轨（后端）

- [S-01] 新接口 `POST /api/media/soundtrack`，体 `{session_id, source, refs: {soundtrack: {kind:"music", session_id, attempt_id}}, force?}`；`kind` 固定 video。
- [S-02] 校验顺序：参数（`source` 字符串、`refs.soundtrack` 结构）→ 视频会话（必填，同 V-01）→ `source` 为本会话 done 且文件在的尝试（`segment_not_found` / `segment_missing`）→ 音乐引用解析（`ref_missing`「引用的音乐已不在」）→ `media_busy` → ffmpeg（503「需要 ffmpeg 才能拼接成片」）→ 启动。不走 arbiter、模型检查、内存提醒（同 B-45）。
- [S-03] 输入视频：`source` 有未缺失的 `joined_output` 用它，否则用 `output`。
- [S-04] 命令：`compose.soundtrack_command(ffmpeg, video, audio, output)`：视频流拷贝，音频 `aac`，音频 `apad` 补静音，时长以视频为准（`-shortest` 在 apad 之后生效）；输出最后一个参数（B §6 约定）。原 `replace_audio_command` 替换为此（仅此处用）。
- [S-05] 尝试：`op = "soundtrack"`，`params = {"source": <attempt_id>}`，`refs = {"soundtrack": <music ref>}`，`continues = null`；成功 `output` 为 `h3-soundtrack-<stamp>-<8hex>.mp4`；失败 `failed` + `join_failed`，未完成时删除半成品（同合成）。
- [S-06] history 条目 `params.op = "soundtrack"`、顶层 `refs`；`fillPlan` 对 `op ∈ {compose, soundtrack}` 返回 null。
- [S-07] 配乐尝试可被续写（B-35 放宽到 op soundtrack）与参加合成（`find_done` 不区分 op）。

## 2. D1 配乐参考（后端）

- [S-10] `start_video_job` 接受 `mode = "music_ref"`：必须有参考图（`ref_image` 上传素材 id，或 `refs.ref_image = {kind:"image", …}`，二选一，否则 400「参考图只能从上传或图片会话二选一」/ 缺失 400「请先选择参考图」）与 `refs.ref_audio = {kind:"music", …}`（缺失 400「请先选择一首歌」），以及 `audio_start`（秒，≥0 的数，默认 0）。
- [S-11] 注册引用槽：`video.ref_image → image`、`video.ref_audio → music`（与 `first_frame` 并列）。`music_ref` 不能与 `continues`、`first_frame`、`last_frame`、`ref_video`、`refs.first_frame` 同用（400 invalid_params，文案「配乐参考不能和首帧、尾帧或续写同时使用」）。
- [S-12] 截取：服务端在启动前用 ffmpeg 从歌中 `audio_start` 起截取 `clip = clamp(frames / 24, 2, 15)` 秒到 `.inputs/<hex>.wav`；歌短于 `audio_start + 2` 秒 → 400「这首歌从第 N 秒起不足 2 秒」；截取失败 → 500 `audio_clip_failed`「没能截取这段音乐」；之后任一步失败删除截取文件（同 B-37 做法）。
- [S-13] 命令：`build_h3_command(..., ref_image=<path>, ref_audio=<path>)` 追加 `--ref-image <path> --ref-audio <path>`（H3 Ref2VA，spike 已验证可跑）。`params` 记 `mode="music_ref"`、`audio_start`、`ref_image`（上传 id 或 null），尝试 `refs` 记引用。
- [S-14] 估算同普通视频（`estimate_bytes("video", params)`），标 predicted。

## 3. 通用媒体选择框

- [S-20] `widgets/media_picker.js::openMediaPicker(doc, {kind, title, emptyText, listSessions, getSession, serveOutput})`：`kind ∈ {image, music}`；图片为缩略图网格（同 V-23），音乐为列表：每项「第 N 次 · <风格描述摘要>」+ `<audio controls preload="none">` 试听 + 「选这首」按钮；只列 done 且文件在的尝试（音乐优先成片 `joined_output`，无则 `output`）。返回 `null | {ref, title, index, label}`（`label` 为风格描述摘要，图片为提示词摘要）。
- [S-21] `widgets/image_picker.js` 删除，视频页首帧改用 `openMediaPicker({kind:"image", title:"从图片会话选首帧", emptyText:"这个会话还没有生成好的图片"})`；音乐 `title` 由调用方给，`emptyText`「这个会话还没有生成好的歌」。

## 4. 界面

- [S-30] 视频卡片（done 且文件在、非挑选模式）动作区增加次级按钮「配乐…」：打开音乐选择框（标题「选一首歌配到这段视频」）→ 选中即 `POST /api/media/soundtrack`（`source` = 该尝试）→ 新卡片追加并选中。不可用条件同「换个版本」（有作业在跑等），原因同一套。
- [S-31] 配乐卡片：折叠标题「第 N 次 · HH:MM · 配乐：<风格描述摘要> · 基于第 M 次」（M 取不到则省略该段；风格描述取不到显示「配乐」）；展开播放 `output`；动作只有「接着往下生」与「配乐…」。
- [S-32] 「生成方式」下拉新增「配乐参考（实验性）」。选中时素材区：参考图区（「上传图片」+「从图片会话选…」+ 说明）、歌区（「从音乐会话选…」+ 所选歌说明「歌：<风格描述摘要>」+ 试听）、数字框，标签「从第几秒开始」（默认 0，≥0）、说明「实验性：画面不保证跟随音乐节奏；参考图只影响画面风格，不作为第一帧。截取与视频等长、2–15 秒的一段音乐。」。
- [S-33] 提交：`mode:"music_ref"`、`audio_start`、`ref_image`（上传 id）或 `refs.ref_image`、`refs.ref_audio`。缺参考图「请先选择参考图」、缺歌「请先选择一首歌」（前端先校验）。
- [S-34] 「在这段基础上改」对 music_ref 尝试回填参考图来源、歌、起始秒；引用失效时对应说明「引用的图片已不在」/「引用的歌已不在」并清空。「换个版本」原样重发（新种子）。
- [S-35] 900×700：新增的素材在已有可滚动的素材区内（V 块 50vh 规则），不增加输入区固定行。

## 5. 测试与完成标准

- 后端：soundtrack 接口各错误码与顺序；`soundtrack_command` 真 ffmpeg 小测（歌短于视频 → 输出时长 = 视频；歌长 → 截断）；music_ref 校验、截取时长 clamp、截取失败清理、命令含 `--ref-image`/`--ref-audio`；history/fillPlan。
- 前端：`openMediaPicker` 两种 kind；视频页「配乐…」请求体；配乐卡片文案与动作；music_ref 素材区显隐、提交体、回填与引用失效。
- e2e `tests/e2e/test_video_soundtrack.py`：音乐页生成一首 → 视频页生成一段 → 「配乐…」选这首 → 配乐卡片出现、会话文件 `op=="soundtrack"`、`refs.soundtrack` 正确；切到「配乐参考（实验性）」→ 从图片会话选参考图、从音乐会话选歌 → 生成 → 会话文件 `params.mode=="music_ref"`、`refs.ref_audio` 正确。
- 全量三组测试。

## 6. 自审闭环

| 环 | 落点 |
|---|---|
| 被引用的歌/图后来被删 | S-02/S-10 后端 404；S-34 回填提示 |
| 截取出的音频文件 | S-12 失败清理；成功时与上传素材同生命周期（`.inputs/`） |
| 配乐作业中断/失败 | S-05 删除半成品，同合成 |
| 配乐结果再加工 | S-07 可续写、可合成 |
| 素材库回填 | S-06 配乐条目不给回填 |

## 7. 待决问题

无。本文决定：S-00b D2 从第 0 秒起（最常见需求，调节留待以后）；S-12 D1 截取长度按视频时长夹在 2–15 秒；S-04 以视频长度为准补静音/截断（不改变画面）。
