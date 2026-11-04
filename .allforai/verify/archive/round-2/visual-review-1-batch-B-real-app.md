# Visual review 1: batch-B-real-app

- Reviewer: reviewer-1 (claude -p fresh context, model claude-opus-5-5)
- Batch: `.allforai/verify/visual-acceptance-batches/batch-B-real-app.md`
- Standard: `.allforai/visual-qa/visual-acceptance-criteria.md`
- I opened all 22 screenshots and judged each one by looking at the image. The .json records were not used to pass anything.
- **Status: passed_with_warnings.** No blockers or majors. There are 2 minor issues and 3 notes.

## Summary of what I saw

- **Layout, both widths:** In every image-page screenshot the session list is on the left with 「新会话」 on top, the timeline is on the right, and the composer (prompt, 「生成图片」, collapsed 「高级参数」) is at the bottom. Nothing overlaps and nothing is off-screen. There is no sign of horizontal overflow.
- **Action buttons:** 「在这张基础上改」 and 「换个构图」 sit side by side and are fully visible on every expanded completed, cancelled and failed card, at both widths. No button text is clipped.
- **Real images:** All thumbnails and expanded images show real Qwen-Image outputs: watercolour lighthouses and a bamboo path. I saw no blank frames, broken icons or grey placeholders. The cancelled card uses a grey × icon block and the failed card a red × icon block, and neither has an image frame.
- **「种子」:** The word does not appear anywhere on the image page. It appears only in the 素材库 metadata, which D-50a exempts.
- **After restart:** Both sessions are still listed. The lighthouse session is highlighted with 6 次生成. Attempts 4, 5 and 6 are shown with the thumbnail, the cancelled block and the failed block.
- **Delete:** The dialog title and body match the criteria exactly. After deleting, the list holds only the lighthouse session. The 素材库 preview shows the deleted session's bamboo image as a real picture.

## Per-screenshot verdicts

| screenshot | verdict | observation |
|---|---|---|
| real-running-wide.png | pass | Card shows 「第 1 次 · 生成中…（已用 3秒）」 with a progress bar, 「取消」 and a collapsed 「日志」. The list item has 「生成中」. 「生成图片」 is disabled and the status line reads 「正在生成这个会话里的第 1 次」. There is no image frame and no action buttons. |
| real-running-narrow.png | pass | Same as wide (已用 5秒). The layout fits. |
| real-refine-prefill-wide.png | pass | Chip 「沿用第 2 次的构图 ×」 is shown. The prompt matches attempt 2 and the caret is in it. 「高级参数」 is collapsed and there is no new card. |
| real-refine-prefill-narrow.png | pass | Same as wide. See the minor issue about the duplicated image. |
| real-timeline-three-rounds-wide.png | pass | Pinned to the end. 第 3 次 is expanded with the large image, full prompt, collapsed 高级参数 and both buttons. |
| real-timeline-three-rounds-narrow.png | pass | Same as wide. |
| real-timeline-three-rounds-top-wide.png | pass | 第 1/2/3 次 appear in order, each with a real thumbnail, prompt summary and 「512×512 · 6 步」. The title is 「一座海边灯塔，黄…」. |
| real-timeline-three-rounds-top-narrow.png | pass | Same as wide. |
| real-attempt-selected-actions-wide.png | pass | 第 1 次 is expanded and the next card is collapsed at the bottom. The large image is complete and both buttons are visible. |
| real-attempt-selected-actions-narrow.png | pass | Same as wide. |
| real-attempt-cancelled-wide.png | pass | Card has the 「已取消」 badge and 「这次生成被手动停止」. It has the grey × block and both buttons. |
| real-attempt-cancelled-narrow.png | pass | Same as wide. |
| real-attempt-failed-wide.png | pass | Card has the 「失败」 badge and the reason 「生成程序异常退出」. It has the red × block, a collapsed 「详情」, a collapsed 高级参数 and both buttons. |
| real-attempt-failed-narrow.png | pass | Same as wide. |
| real-after-restart-wide.png | pass | Both sessions are present with the lighthouse session highlighted. The attempts and their images or icon blocks persist. See note N1. |
| real-after-restart-narrow.png | pass | Same as wide. |
| real-delete-confirm-wide.png | pass | Title is 「删除会话」 and the body is the exact criteria text. 「删除」 uses the danger style. See minor M2 about focus. |
| real-delete-confirm-narrow.png | pass | Same as wide. The modal overlaps the list, which is allowed for a dialog. |
| real-after-delete-wide.png | pass | Only 「一座海边灯塔，黄…」 remains and it is highlighted. The deleted session is gone. |
| real-after-delete-narrow.png | pass | Same as wide. |
| real-library-after-delete-wide.png | pass | The bamboo image preview is real. The entry 「另一个想法：竹林小径，晨雾」 has 预览, 在访达中显示 and 回填参数. 「种子 N」 is exempt. See note N2. |
| real-library-after-delete-narrow.png | pass | Same as wide. The metadata wraps cleanly. |

## Blockers
None.

## Majors
None.

## Minors

**R1-batch-B-real-app-001: the expanded card shows the same image twice**
- Screenshots: real-refine-prefill-narrow.png, real-attempt-selected-actions-narrow.png, real-timeline-three-rounds-narrow.png, plus the wide versions.
- Criteria: attempt-selected-actions 「大图完整显示」 and timeline-three-rounds 「展开：大图」.
- Observation: An expanded card keeps its thumbnail and then shows the same picture again as the "large" image. At 900 px wide the large image is only slightly bigger than the thumbnail (about 150 px against 96 px in CSS terms), so it reads as a duplicate rather than a large view. At 1280 px it is about 195 px, well under the 60vh limit. Nothing is clipped or blank, so this is not a blocking failure.
- Repair: Hide the thumbnail when the card is expanded, or let the large image grow toward the 60vh / column width limit so it is clearly the enlarged view.

**R1-batch-B-real-app-002: I can't see that 「取消」 has focus in the delete dialog**
- Screenshots: real-delete-confirm-wide.png, real-delete-confirm-narrow.png
- Criteria: delete-confirm must show 「「取消」获得焦点」.
- Observation: 「删除」 is clearly in the danger style. 「取消」 looks like a plain secondary button, and I can't see a focus ring or highlight on it. The criterion can't be confirmed from the image, and keyboard users may not be able to tell which button is focused.
- Repair: Give dialog buttons a visible `:focus-visible` ring when focus is set programmatically, or check with a forced focus-visible state and recapture.

## Notes

- **N1 (real-after-restart-\*):** The highlighted lighthouse session shows its pencil button and a solid red trash button, with a double focus ring. This looks like the probe's hover or focus state. The solid red trash button is loud for a resting list item, but it is not a defect under the criteria.
- **N2 (real-library-after-delete-\*):** The captures are scrolled, so the app header and tab bar are out of view. From the images alone I can't confirm the 素材库 tab is active. The content (「正在预览」, 在访达中显示, 回填参数) is consistent with the library pane. Consider capturing with the tab bar visible.
- **N3 (real-running-narrow.png):** The narrow header shortens its status chips to 「媒体：忙 × 忙」, while the wide header reads 「不可：媒体作业进行中」. This is outside the image-sessions scope. I mention it only because the shortened wording is vague.
