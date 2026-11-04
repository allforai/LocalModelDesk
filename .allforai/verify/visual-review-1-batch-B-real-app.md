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
