# Visual review 1 — batch B (real app + real Qwen-Image)

Reviewer: reviewer-1 · claude -p fresh context · claude-opus-5-5
Status: **failed_visual_review** (5 major, 5 minor, 2 notes)

I opened and inspected all 20 screenshots listed in the batch as images.

## Summary
- Real model output renders correctly in every thumbnail, expanded image and library preview: no blank frames, no broken icons, no grey placeholders.
- Layout at both widths: session list on the left with 「新会话」 on top, timeline on the right, composer at the bottom. No horizontal scroll, and no 「种子」 in the image-page main flow.
- **Main failure:** an expanded attempt card (header + large image up to 60vh + prompt + 高级参数 + action row) is taller than the timeline viewport at both 1280×800 and 900×700. So the two action buttons 「在这张基础上改」「换个构图」, which are AC-7's focus, never appear in the attempt-selected and three-rounds evidence. At narrow width the newest card is also cut in the middle of a line.

## Majors

### R1-001 · attempt-selected-actions: action buttons not visible (missing_required_element)
- Screenshots: `evidence/real/real-attempt-selected-actions-wide.png`, `…-narrow.png`
- Criteria: attempt-selected-actions: both buttons fully visible, large image fully shown and not clipped.
- Observation: after clicking attempt 1, the timeline shows only its large image. The card header (第 N 次) is scrolled away, and neither action button is on screen. At narrow width the large image is also cut at the bottom by the timeline's edge.
- Repair:
  - Cap the expanded image by the timeline's available height, or put the actions beside or above the image.
  - After selecting, scroll the action row into view.
  - Re-capture both widths.

### R1-002 · timeline-three-rounds: rounds 1–3 and the expanded 第 3 次 not fully shown (missing_required_element)
- Screenshots: `evidence/real/real-timeline-three-rounds-wide.png`, `…-narrow.png`
- Criteria: 第 1/2/3 次 in order from top to bottom; 第 3 次 expanded with image, full prompt, 高级参数 and both buttons.
- Observation: only the bottom edge of 第 1 次's thumbnail is visible. On the expanded 第 3 次, the full prompt, 高级参数 and both buttons are below the fold.
- Repair: same layout fix as R1-001. Then capture evidence that actually shows these items, or declare a top capture and a bottom capture.

### R1-003 · narrow: newest card cut mid-line, actions below the fold (missing_required_element / occlusion)
- Screenshots: `evidence/real/real-attempt-cancelled-narrow.png`, `evidence/real/real-after-restart-narrow.png`
- Criteria: attempt-cancelled requires both action buttons; global rule against occlusion and clipped text.
- Observation: the prompt line 「会被取消的一张：雪山日出」 is sliced horizontally by the timeline's bottom edge, and neither button is visible.
- Repair: when an attempt settles or expands, scroll so the card's action row is in view.

### R1-004 · attempt-cancelled: no explanation text (missing_required_element)
- Screenshots: `evidence/real/real-attempt-cancelled-wide.png`, `…-narrow.png`, `evidence/real/real-after-restart-wide.png`
- Criteria: the card must show the 「已取消」 badge **and an explanation**.
- Observation: the card has the badge, the grey × icon block and the two buttons. The only body text is the prompt, repeated; there is no explanation.
- Repair: add an explanation line like the one on failed and interrupted cards.

### R1-005 · library-after-delete: post-delete session list has no evidence (missing_required_element)
- Screenshots: `evidence/real/real-library-after-delete-wide.png`, `…-narrow.png`
- Criteria: the image page's session list no longer contains the deleted session.
- Observation: the 素材库 preview of the real bamboo-path image is correct. But no screenshot in this batch shows the image-page session list after the delete was confirmed.
- Repair: add a #tab=image capture at both widths taken after the delete.

## Minors
- **R1-006** refine-prefill (wide and narrow): the timeline sits at the top, so attempt 2's large image is cut off where the timeline meets the composer. The button that was just clicked is also out of view. All required items for this state are present.
- **R1-007** running-other-session (harness): the header shows 「媒体：空闲 · 可开下一件重活」 while the status line says 甲 is generating. This contradicts itself, though it is probably a harness artifact.
- **R1-008** running-other-session: while viewing 乙, the composer still contains 甲's prompt, which can be misread as 乙's draft.
- **R1-009** model-missing: the empty-state text breaks inside 「在这张基础上／改」. The header also shows a green 可开下一件重活 / 可开工 while no model is installed.
- **R1-010** delete-confirm: 「取消」 shows no visible focus ring, so the requirement that it has focus can't be confirmed from the image.

## Notes
- **R1-011** In the harness screenshots the expanded large image is thumbnail-sized, because the gradient PNG is small. The real-app screenshots render it normally.
- **R1-012** The 素材库 rows show 「种子」. This is outside the image page, so it doesn't break the rule.

## Per-screenshot verdicts
| screenshot | verdict |
|---|---|
| real-running wide / narrow | pass / pass |
| real-refine-prefill wide / narrow | pass / pass (R1-006) |
| real-timeline-three-rounds wide / narrow | fail / fail (R1-002) |
| real-attempt-selected-actions wide / narrow | fail / fail (R1-001) |
| real-attempt-cancelled wide / narrow | fail (R1-004) / fail (R1-003, R1-004) |
| real-after-restart wide / narrow | pass / pass (persistence OK; cut-off noted in R1-003) |
| real-delete-confirm wide / narrow | pass / pass (R1-010) |
| real-library-after-delete wide / narrow | fail / fail (R1-005) |
| running-other-session wide / narrow | pass / pass (R1-007, R1-008) |
| model-missing wide / narrow | pass / pass (R1-009) |
