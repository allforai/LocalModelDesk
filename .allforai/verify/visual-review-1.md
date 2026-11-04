# Visual review 1 — image sessions, verify round 3 (merged verbatim from the two batch reports)

Reviewer: {'id': 'reviewer-1', 'backend': 'Claude Code fresh-context sub-agent', 'model': 'claude-opus-5-5'}  
Overall status: **passed_with_warnings**  
Inspected screenshots: 76


---

<!-- verbatim: visual-review-1-batch-A-harness.md -->

# Visual review 1 — batch-A-harness

Reviewer: reviewer-1 (Claude Code fresh-context sub-agent, claude-opus-5-5)

**Status: passed_with_warnings**

All 54 screenshots (27 states x wide/narrow) opened and judged. Layout (session list + 新会话, timeline, composer with folded 高级参数) is intact at both widths; no occlusion, clipping, horizontal scroll, blank/broken image frames, or 种子 on the image page. Every per-state must-show item is visible. Two minor issues (duplicated prompt on expanded non-image cards; top bar shows 媒体：空闲 right after an image job starts) and four notes.

## Blockers
None.

## Majors
None.

## Minors
### R1-batch-A-harness-001 (inconsistent_expanded_card)
- Screenshots: `.allforai/verify/screens/attempt-failed-wide.png`, `.allforai/verify/screens/attempt-failed-narrow.png`, `.allforai/verify/screens/attempt-cancelled-wide.png`, `.allforai/verify/screens/attempt-cancelled-narrow.png`, `.allforai/verify/screens/attempt-interrupted-wide.png`, `.allforai/verify/screens/attempt-interrupted-narrow.png`, `.allforai/verify/screens/attempt-file-missing-wide.png`, `.allforai/verify/screens/attempt-file-missing-narrow.png`, `.allforai/verify/screens/verify-failed-and-cancelled-wide.png`, `.allforai/verify/screens/verify-failed-and-cancelled-narrow.png`
- Criteria: timeline-three-rounds (展开卡片以完整提示词代替摘要); attempt-failed/attempt-cancelled/attempt-file-missing
- Observation: Expanded failed / cancelled / interrupted / file-missing cards keep the prompt summary in the header row AND print the full prompt again below the icon block (e.g. 会失败的一张 twice), whereas expanded completed cards replace the summary with the full prompt. Not a blocking defect, but the same prompt reads twice and the rule is applied inconsistently.
- Repair: For expanded non-image cards, drop the header summary line (or drop the body prompt when it equals the summary) so each expanded card shows the prompt exactly once.

### R1-batch-A-harness-002 (stale_global_status)
- Screenshots: `.allforai/verify/screens/running-wide.png`, `.allforai/verify/screens/running-narrow.png`, `.allforai/verify/screens/running-other-session-wide.png`, `.allforai/verify/screens/running-other-session-narrow.png`, `.allforai/verify/screens/delete-confirm-running-wide.png`, `.allforai/verify/screens/delete-confirm-running-narrow.png`
- Criteria: global (outside image-sessions per-state list); running / running-other-session
- Observation: While an image attempt is shown as 生成中（已用 0秒） the top bar still reads 媒体：空闲 · 可开下一件重活 / 可开工. In running-other-session-new-empty and busy-other-media the top bar does reflect the job (图片生成中 / 视频生成中), so this looks like header polling lag right after submit rather than wrong logic; the image page itself is correct.
- Repair: Refresh the top-bar status immediately when an image job is submitted (or when the image pane observes a running job), and confirm on batch B (real app) that the header flips to 图片生成中 within a second.

## Notes
### R1-batch-A-harness-003 (duplicated_status)
- Screenshots: `.allforai/verify/screens/running-other-session-wide.png`, `.allforai/verify/screens/running-other-session-narrow.png`, `.allforai/verify/screens/busy-other-media-wide.png`, `.allforai/verify/screens/busy-other-media-narrow.png`
- Criteria: running-other-session; busy-other-media
- Observation: The disabled-reason line is shown twice: once inside the expanded card under the action buttons and again under the composer (「甲会话：正在生成」正在生成图片 / 媒体作业进行中). Required copy is present; the repetition is just visual noise.
- Repair: Optional: keep only the composer status line, or keep the in-card line as a short hint tied to the disabled 换个构图.

### R1-batch-A-harness-004 (copy_mismatch)
- Screenshots: `.allforai/verify/screens/runtime-unavailable-wide.png`, `.allforai/verify/screens/runtime-unavailable-narrow.png`, `.allforai/verify/screens/model-missing-wide.png`, `.allforai/verify/screens/model-missing-narrow.png`
- Criteria: runtime-unavailable; model-missing
- Observation: runtime-unavailable: header still says 模型文件完整 · 可离线生成 while generation is impossible; both states keep the empty hint 点「生成图片」 although the button is disabled. Status lines themselves are correct.
- Repair: Optional: when the runtime is missing, drop 可离线生成 from the header; consider muting the empty-state instruction when 生成图片 is disabled.

### R1-batch-A-harness-005 (empty_region)
- Screenshots: `.allforai/verify/screens/session-list-load-failed-wide.png`, `.allforai/verify/screens/session-list-load-failed-narrow.png`
- Criteria: session-list-load-failed
- Observation: The timeline area is completely empty; the reason sits only in the left column and the status line. Meets the criteria (list shows reason + 重试, status 会话还没加载好).
- Repair: Optional: echo a short centred hint in the timeline (e.g. 会话列表读不出来，点左侧「重试」).

### R1-batch-A-harness-006 (evidence_framing)
- Screenshots: `.allforai/verify/screens/library-after-delete-wide.png`, `.allforai/verify/screens/library-after-delete-narrow.png`
- Criteria: library-after-delete
- Observation: The frame is scrolled to the preview, so page tabs/header are not in view and the 'image page no longer lists the session' half is not visible here; it is evidenced by verify-after-delete-*. The library preview shows a real image and the item is listed.
- Repair: Optional: capture library-after-delete scrolled to top or add a paired image-page shot next to it.

## Per-screenshot verdicts
| screenshot | verdict | notes |
|---|---|---|
| `.allforai/verify/screens/first-entry-auto-session-wide.png` | pass | One highlighted 新会话; two-line empty hint centred; 生成图片 enabled; 高级参数 folded; no progress bar, no image frame, no 种子. |
| `.allforai/verify/screens/first-entry-auto-session-narrow.png` | pass | One highlighted 新会话; two-line empty hint centred; 生成图片 enabled; 高级参数 folded; no progress bar, no image frame, no 种子. |
| `.allforai/verify/screens/empty-session-wide.png` | pass | New 新会话 on top and highlighted, previous session below; two-line empty hint; prompt box focused (blue ring; shared draft is by user decision); no previous cards, no 种子. |
| `.allforai/verify/screens/empty-session-narrow.png` | pass | New 新会话 on top and highlighted, previous session below; two-line empty hint; prompt box focused (blue ring; shared draft is by user decision); no previous cards, no 种子. |
| `.allforai/verify/screens/running-wide.png` | pass | Running card last: 第 2 次 · 生成中…（已用 0秒）, progress bar, 取消, folded 日志, no image frame, no action buttons; list shows 生成中; 生成图片 disabled; status 正在生成这个会话里的第 2 次. Earlier failed card uses danger icon block. Top bar still says 媒体：空闲 (R1-002). |
| `.allforai/verify/screens/running-narrow.png` | pass | Running card last: 第 2 次 · 生成中…（已用 0秒）, progress bar, 取消, folded 日志, no image frame, no action buttons; list shows 生成中; 生成图片 disabled; status 正在生成这个会话里的第 2 次. Earlier failed card uses danger icon block. Top bar still says 媒体：空闲 (R1-002). |
| `.allforai/verify/screens/running-other-session-wide.png` | pass | 甲 has 生成中 marker; 乙 highlighted with its own completed card; status 「甲会话：正在生成」正在生成图片 + 回到该会话; 生成图片 and 换个构图 disabled, 在这张基础上改 enabled; no running card of A. Status line repeated inside card (R1-003); top bar says 媒体：空闲 (R1-002). |
| `.allforai/verify/screens/running-other-session-narrow.png` | pass | 甲 has 生成中 marker; 乙 highlighted with its own completed card; status 「甲会话：正在生成」正在生成图片 + 回到该会话; 生成图片 and 换个构图 disabled, 在这张基础上改 enabled; no running card of A. Status line repeated inside card (R1-003); top bar says 媒体：空闲 (R1-002). Narrow: timeline scrollable, card starts just below the header; no overlap. |
| `.allforai/verify/screens/timeline-three-rounds-wide.png` | pass | Scrolled to bottom: 第 3 次 expanded with large real image (well over 192px), full prompt, folded 高级参数, both actions fully visible; bottom edge of 第 2 次 visible above. Title is first prompt with ellipsis. Order/thumbnails confirmed by the -top pair. |
| `.allforai/verify/screens/timeline-three-rounds-narrow.png` | pass | Scrolled to bottom: 第 3 次 expanded with large real image (well over 192px), full prompt, folded 高级参数, both actions fully visible; bottom edge of 第 2 次 visible above. Title is first prompt with ellipsis. Order/thumbnails confirmed by the -top pair. |
| `.allforai/verify/screens/attempt-selected-actions-wide.png` | pass | 第 1 次 expanded with whole image (not clipped, <60vh), full prompt, folded 高级参数, both secondary buttons side by side; only one card expanded; no 种子. |
| `.allforai/verify/screens/attempt-selected-actions-narrow.png` | pass | 第 1 次 expanded with whole image (not clipped, <60vh), full prompt, folded 高级参数, both secondary buttons side by side; only one card expanded; no 种子. |
| `.allforai/verify/screens/refine-prefill-wide.png` | pass | Prompt box holds 第 2 次 prompt with focus ring; chip 沿用第 2 次的构图 with ×; 高级参数 folded; no new/running card; no 种子. |
| `.allforai/verify/screens/refine-prefill-narrow.png` | pass | Prompt box holds 第 2 次 prompt with focus ring; chip 沿用第 2 次的构图 with ×; 高级参数 folded; no new/running card; no 种子. |
| `.allforai/verify/screens/attempt-failed-wide.png` | pass | 失败 badge + reason 生成程序异常退出; danger X icon block, no image frame; 详情 shows exit_nonzero: exit 1 and log tail; both actions visible. Prompt appears twice (R1-001). |
| `.allforai/verify/screens/attempt-failed-narrow.png` | pass | 失败 badge + reason 生成程序异常退出; danger X icon block, no image frame; 详情 shows exit_nonzero: exit 1 and log tail; both actions visible. Prompt appears twice (R1-001). |
| `.allforai/verify/screens/attempt-cancelled-wide.png` | pass | 第 2 次 has 已取消 badge + 这次生成被手动停止; grey icon block; both actions; not stuck in 生成中. Prompt appears twice (R1-001). |
| `.allforai/verify/screens/attempt-cancelled-narrow.png` | pass | 第 2 次 has 已取消 badge + 这次生成被手动停止; grey icon block; both actions; not stuck in 生成中. Prompt appears twice (R1-001). |
| `.allforai/verify/screens/attempt-interrupted-wide.png` | pass | 第 3 次: 失败 badge + 应用在生成途中关闭，这次没有完成; danger icon block; no progress bar, not 生成中; earlier cards show real thumbnails. |
| `.allforai/verify/screens/attempt-interrupted-narrow.png` | pass | 第 3 次: 失败 badge + 应用在生成途中关闭，这次没有完成; danger icon block; no progress bar, not 生成中; earlier cards show real thumbnails. |
| `.allforai/verify/screens/attempt-file-missing-wide.png` | pass | 第 1 次: 图片文件已不在 chip + 可能已在访达中移动或删除; grey picture icon block, no broken image; both actions enabled. |
| `.allforai/verify/screens/attempt-file-missing-narrow.png` | pass | 第 1 次: 图片文件已不在 chip + 可能已在访达中移动或删除; grey picture icon block, no broken image; both actions enabled. |
| `.allforai/verify/screens/model-missing-wide.png` | pass | Header and status line 尚未安装图片模型，请到「资源」页下载; 生成图片 disabled; no 种子. Empty hint still says 点「生成图片」 (R1-004). |
| `.allforai/verify/screens/model-missing-narrow.png` | pass | Header and status line 尚未安装图片模型，请到「资源」页下载; 生成图片 disabled; no 种子. Empty hint still says 点「生成图片」 (R1-004). |
| `.allforai/verify/screens/runtime-unavailable-wide.png` | pass | Status line gives runtime reason (图片 MLX 运行环境缺失…); 生成图片 disabled. Header still says 可离线生成 (R1-004). |
| `.allforai/verify/screens/runtime-unavailable-narrow.png` | pass | Status line gives runtime reason (图片 MLX 运行环境缺失…); 生成图片 disabled. Header still says 可离线生成 (R1-004). |
| `.allforai/verify/screens/busy-other-media-wide.png` | pass | Status 媒体作业进行中; 生成图片 and 换个构图 disabled; no 回到该会话; no 种子; top bar shows 视频生成中. |
| `.allforai/verify/screens/busy-other-media-narrow.png` | pass | Status 媒体作业进行中; 生成图片 and 换个构图 disabled; no 回到该会话; no 种子; top bar shows 视频生成中. |
| `.allforai/verify/screens/rename-wide.png` | pass | Session item turned into input with current title and focus ring, fits inside left column; only one session so 'others unchanged' is trivially true. |
| `.allforai/verify/screens/rename-narrow.png` | pass | Session item turned into input with current title and focus ring, fits inside left column; only one session so 'others unchanged' is trivially true. |
| `.allforai/verify/screens/delete-confirm-wide.png` | pass | Modal 删除会话 with exact body copy (图片仍保留在素材库); 取消 focused, 删除 danger red; no chat copy. |
| `.allforai/verify/screens/delete-confirm-narrow.png` | pass | Modal 删除会话 with exact body copy (图片仍保留在素材库); 取消 focused, 删除 danger red; no chat copy. |
| `.allforai/verify/screens/delete-confirm-running-wide.png` | pass | Base body + appended sentence 这个会话正在生成图片，生成会继续完成…; 取消 focused, 删除 danger. Top bar 媒体：空闲 behind dim (R1-002). |
| `.allforai/verify/screens/delete-confirm-running-narrow.png` | pass | Base body + appended sentence 这个会话正在生成图片，生成会继续完成…; 取消 focused, 删除 danger. Top bar 媒体：空闲 behind dim (R1-002). |
| `.allforai/verify/screens/library-after-delete-wide.png` | pass | Library shows real preview of 将被删除分组的灯塔 and the item listed with 预览/在访达中显示/回填参数; 种子 N in library metadata is exempt (D-50a). Frame is scrolled so page tabs are not visible (R1-006). |
| `.allforai/verify/screens/library-after-delete-narrow.png` | pass | Library shows real preview of 将被删除分组的灯塔 and the item listed with 预览/在访达中显示/回填参数; 种子 N in library metadata is exempt (D-50a). Frame is scrolled so page tabs are not visible (R1-006). Narrow: metadata wraps (种子 on its own line), second item cut by viewport bottom only. |
| `.allforai/verify/screens/session-list-load-failed-wide.png` | pass | List area shows 会话列表读不出来：磁盘读不出来 + 重试; 生成图片 disabled; status 会话还没加载好; no 种子. Timeline area empty (R1-005). |
| `.allforai/verify/screens/session-list-load-failed-narrow.png` | pass | List area shows 会话列表读不出来：磁盘读不出来 + 重试; 生成图片 disabled; status 会话还没加载好; no 种子. Timeline area empty (R1-005). |
| `.allforai/verify/screens/corrupt-session-wide.png` | pass | Item 无法读取的会话 / 文件已损坏 with only delete button; timeline explanation text; 生成图片 disabled with 请选择其他会话或新建一个; no rename button. |
| `.allforai/verify/screens/corrupt-session-narrow.png` | pass | Item 无法读取的会话 / 文件已损坏 with only delete button; timeline explanation text; 生成图片 disabled with 请选择其他会话或新建一个; no rename button. |
| `.allforai/verify/screens/timeline-three-rounds-top-wide.png` | pass | 第 1 次, 第 2 次 collapsed with real thumbnails, summaries and 1024×1024 · 40 步; 第 3 次 expanded below with large image; order correct; no 种子. |
| `.allforai/verify/screens/timeline-three-rounds-top-narrow.png` | pass | 第 1 次, 第 2 次 collapsed with real thumbnails, summaries and 1024×1024 · 40 步; 第 3 次 expanded below with large image; order correct; no 种子. |
| `.allforai/verify/screens/running-other-session-new-empty-wide.png` | pass | New empty session highlighted with empty hint; 甲会话的灯塔 marked 生成中; status + 回到该会话; 生成图片 disabled; top bar correctly shows 图片生成中. |
| `.allforai/verify/screens/running-other-session-new-empty-narrow.png` | pass | New empty session highlighted with empty hint; 甲会话的灯塔 marked 生成中; status + 回到该会话; 生成图片 disabled; top bar correctly shows 图片生成中. |
| `.allforai/verify/screens/verify-four-attempts-wide.png` | pass | 第 4 次 (768×512 · 20 步) expanded with landscape image, full prompt, both actions; title ellipsized; no clipping. |
| `.allforai/verify/screens/verify-four-attempts-narrow.png` | pass | 第 4 次 (768×512 · 20 步) expanded with landscape image, full prompt, both actions; title ellipsized; no clipping. |
| `.allforai/verify/screens/verify-switch-back-wide.png` | pass | 乙会话：沙漠 highlighted with its own 第 2 次; 甲 below; layout clean. |
| `.allforai/verify/screens/verify-switch-back-narrow.png` | pass | 乙会话：沙漠 highlighted with its own 第 2 次; 甲 below; layout clean. |
| `.allforai/verify/screens/verify-after-delete-wide.png` | pass | Only 留下来的会话 remains and is current; its attempt expanded with image and actions. |
| `.allforai/verify/screens/verify-after-delete-narrow.png` | pass | Only 留下来的会话 remains and is current; its attempt expanded with image and actions. |
| `.allforai/verify/screens/verify-failed-and-cancelled-wide.png` | pass | Failed card (内存不足，生成被中止, danger block) + cancelled card (grey block, both actions) after reload; no blank frames. |
| `.allforai/verify/screens/verify-failed-and-cancelled-narrow.png` | pass | Failed card (内存不足，生成被中止, danger block) + cancelled card (grey block, both actions) after reload; no blank frames. |
| `.allforai/verify/screens/verify-selected-full-size-wide.png` | pass | Earlier 第 1 次 selected: header, whole image, prompt, 高级参数 and both actions visible together; refine chip + prefill below; nothing clipped. |
| `.allforai/verify/screens/verify-selected-full-size-narrow.png` | pass | Earlier 第 1 次 selected: header, whole image, prompt, 高级参数 and both actions visible together; refine chip + prefill below; nothing clipped. |


---

<!-- verbatim: visual-review-1-batch-B-real-app.md -->

# Visual review 1 — batch-B-real-app

Reviewer: reviewer-1 (Claude Code fresh-context sub-agent, claude-opus-5-5)
Standard: `.allforai/visual-qa/visual-acceptance-criteria.md`, batch `.allforai/verify/visual-acceptance-batches/batch-B-real-app.md`
Status: **passed_with_warnings**

I opened all 22 screenshots under `.allforai/verify/evidence/real/` as images. None showed occlusion, clipped buttons or titles, a blank or broken image frame, horizontal scroll, 「种子」 in the image-page main flow, or content from another pane. Every real Qwen-Image output rendered: 5 lighthouse images and the bamboo image. The session list, attempts and images are all still there after the restart.

## Blockers
None.

## Majors
None.

## Minors

### R1-batch-B-real-app-001 — expanded cancelled/failed cards show the prompt twice
- Screenshots: `real-attempt-cancelled-wide.png`, `real-attempt-cancelled-narrow.png`, `real-attempt-failed-wide.png`, `real-attempt-failed-narrow.png`, `real-after-restart-*.png`, `real-after-delete-*.png`
- Criteria: timeline-three-rounds 「展开卡片以完整提示词代替摘要」 (expanded-card layout rule), attempt-cancelled / attempt-failed
- Observation: the expanded cancelled card (第 5 次) and the expanded failed card (第 6 次) keep the header row: icon block, prompt summary, size/steps and the reason line. Below that they repeat the same prompt as the full-prompt line. So 「会被取消的一张：雪山日出」 and 「会失败的一张：进程中途被杀掉」 each appear twice. Expanded completed cards do not do this: the large image and full prompt replace the thumbnail and summary. All required elements are present (badge, reason, icon block, 详情, both actions), so this is only redundancy and an inconsistency.
- Repair suggestion: when a card without an image is expanded, hide the summary line in the header, or skip the full-prompt line when it is the same as the summary. That keeps the rule "the full prompt replaces the summary" consistent for every attempt status.

## Notes
- N-1 (`real-after-restart-*.png`): the current session item shows a double focus ring and a solid red delete button. This looks like a focus or hover state left from the pointer or keyboard, not the resting style. It is highlighted correctly and nothing is clipped. Check that the resting style of the current item does not show a filled red trash button.
- N-2 (`real-delete-confirm-*.png`): the title 「删除会话」 and the body text are correct, and 「删除」 is red. In the snapshot I cannot clearly see focus on 「取消」, only a faint border. The criteria require that 「取消」 gets focus. Please confirm this from the probe readback (document.activeElement) and consider a more visible focus ring. In the narrow view the modal covers part of the session list, which is allowed for a modal.
- N-3 (`real-library-after-delete-*.png`): the capture is scrolled down past the header and tabs, so the 素材库 tab itself is not in the frame. The page content (「正在预览：另一个想法：竹林小径，晨雾」, the 预览/在访达中显示/回填参数 rows) shows it is the library, and the deleted session's image previews correctly. 「种子 N」 in the library metadata is exempt under D-50a. On the narrow view the seed number wraps onto a second line, which is fine.
- N-4 (`real-running-*.png`): the narrow header shortens the status to 「媒体：忙 × 忙」. That reads a bit oddly, but it is outside this feature's criteria.
- N-5: in `real-refine-prefill-*`, `real-timeline-three-rounds-*` and `real-attempt-selected-actions-*`, a sliver of the neighbouring card shows at the top or bottom edge of the timeline scroller. This is normal clipping from scrolling, not occlusion.

## Per-screenshot
| screenshot | verdict | key observations |
|---|---|---|
| real-running-wide/narrow | pass | 第 1 次 · 生成中…(已用 Ns), progress bar, 取消, collapsed 日志, list item 「生成中」, 生成图片 disabled, status 「正在生成这个会话里的第 1 次」; no image frame, no action buttons |
| real-refine-prefill-wide/narrow | pass | chip 「沿用第 2 次的构图 ×」, prompt equals attempt 2's prompt (caret visible), 高级参数 collapsed, no new card |
| real-timeline-three-rounds-wide/narrow | pass | 第 3 次 expanded with large real image (well above 192px), full prompt, collapsed 高级参数, both actions fully visible; title is the first prompt |
| real-timeline-three-rounds-top-wide/narrow | pass | order 第 1/2/3 次; collapsed cards with real thumbnails, summary, 「512×512 · 6 步」 |
| real-attempt-selected-actions-wide/narrow | pass | only 第 1 次 expanded, image complete and not clipped, two actions visible |
| real-attempt-cancelled-wide/narrow | pass (minor 001) | 已取消 badge, grey × block, 「这次生成被手动停止」, two actions; prompt repeated |
| real-attempt-failed-wide/narrow | pass (minor 001) | 失败 badge, red × block, 「生成程序异常退出」, 详情, two actions |
| real-after-restart-wide/narrow | pass | two sessions persisted, 6 attempts with thumbnails and icon blocks intact (N-1) |
| real-delete-confirm-wide/narrow | pass | correct title and body, red 删除 (N-2) |
| real-after-delete-wide/narrow | pass | only the lighthouse session remains |
| real-library-after-delete-wide/narrow | pass | real bamboo image preview, item listed (N-3) |
