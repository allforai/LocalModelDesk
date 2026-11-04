# Independent visual review 2 — batch-B-real-app

Inspected all 20 listed screenshots directly as images. failed_visual_review: 5 major issues, 1 minor and 2 notes; 7 screenshots fail and 13 pass their assigned visual checks (including warnings). No missing or unreadable screenshots. No evidence JSON or other reviewers’ reports were read.

Reviewer: reviewer-2 · codex exec · GPT-6. Every listed PNG was opened using the image-viewing tool. Judgments are based on visible pixels and the supplied criteria. No prohibited review/reconciliation/audit files were opened.

## Blockers

None.

## Majors

### R2-batch-B-real-app-001 — missing_required_element

Criteria: attempt-selected-actions / D-72, D-74, D-86; AC-7; batch visual question 2

Screenshots:

- `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png`
- `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png`

Observation: Both screenshots show an expanded lighthouse image but neither action button. The attempt header is above the visible timeline area, so its number cannot be verified. In narrow, the image bottom is also cut off at the timeline/composer boundary. Wide shows the full large image, but still no actions.

Repair suggestion: Size the expanded image against the available timeline height and keep the actions visible; scroll the selected card into an appropriate position. Re-capture both widths showing the attempt identity, complete image and both complete action labels. This evidence does not establish whether the buttons exist farther down the scroll area.

### R2-batch-B-real-app-002 — missing_required_element

Criteria: timeline-three-rounds / D-71–D-74; AC-1, AC-2, AC-7

Screenshots:

- `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png`
- `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png`

Observation: Attempt 1 is mostly above the timeline viewport: only the bottom of its thumbnail/card is visible. Attempts 2 and 3 have real lighthouse thumbnails and readable metadata, but attempt 3’s expanded image extends below the viewport, and its detailed prompt, advanced-parameter control and both actions are not visible. The required three-card sequence and expanded-card contents are not fully demonstrated.

Repair suggestion: Arrange or size the three-round state to show the required sequence and expanded controls at both widths; provide complementary scroll-position screenshots if the full state cannot fit. Do not use DOM records as a substitute for missing visual evidence.

### R2-batch-B-real-app-003 — missing_required_element

Criteria: attempt-cancelled / D-84, D-85; AC-7

Screenshots:

- `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png`

Observation: Attempt 5 visibly has an 已取消 badge and a grey X icon block, with no broken image or running indicator. Its lower text is cut at the timeline boundary and both required actions are outside the captured area. The wide counterpart does show both actions.

Repair suggestion: After resizing, bring the expanded cancelled card fully into view or reduce its vertical footprint; re-capture narrow with its explanatory text and both actions visible.

### R2-batch-B-real-app-004 — seed_word_in_main_flow

Criteria: Global rules: no visible 种子 except inside expanded 高级参数; batch visual question 4

Screenshots:

- `.allforai/verify/evidence/real/real-library-after-delete-wide.png`
- `.allforai/verify/evidence/real/real-library-after-delete-narrow.png`

Observation: Library metadata visibly includes 种子 889538739 for the bamboo image and 种子 1248066557 for the cancelled attempt; wide also shows another seed on a lower row. These are plain list metadata, not an expanded advanced-parameter block. The supplied global rule explicitly applies to every screenshot and gives no library exception.

Repair suggestion: Move seed metadata into expanded advanced parameters in the library as well, or obtain an explicit acceptance-standard scope revision before re-review. Under the current standard these screenshots fail.

### R2-batch-B-real-app-005 — missing_required_element

Criteria: library-after-delete / D-30; AC-5: 图片页会话列表里已无该会话

Screenshots:

- `.allforai/verify/evidence/real/real-library-after-delete-wide.png`
- `.allforai/verify/evidence/real/real-library-after-delete-narrow.png`

Observation: The bamboo image is visibly rendered and listed with its matching title, satisfying the preview portion. Neither library screenshot shows the image-page session list, so the required absence of the deleted session is not visually demonstrated. This is an evidence gap, not a claim that deletion failed.

Repair suggestion: Add paired post-deletion image-page screenshots showing the remaining session list, alongside the library preview, and include them in the acceptance batch for inspection.


## Minors

### R2-batch-B-real-app-006 — missing_required_element

Criteria: delete-confirm / D-90; required 取消 focus

Screenshots:

- `.allforai/verify/evidence/real/real-delete-confirm-wide.png`
- `.allforai/verify/evidence/real/real-delete-confirm-narrow.png`

Observation: The modal title, image-retention wording and red 删除 action are clear and fit both widths. However, 取消 has no distinct visible focus indicator; a strong blue outline remains visible around the background session item. Pixels alone cannot establish the actual focused DOM element.

Repair suggestion: Ensure initial focus moves to 取消 and give it a visible keyboard-focus indicator; capture that state. Verify focus behavior separately rather than infer it from these screenshots.


## Notes

### R2-batch-B-real-app-007 — evidence_limit

Criteria: refine-prefill; AC-3; global rules

Screenshots:

- `.allforai/verify/evidence/real/real-refine-prefill-wide.png`
- `.allforai/verify/evidence/real/real-refine-prefill-narrow.png`
- `.allforai/verify/evidence/real/real-after-restart-wide.png`
- `.allforai/verify/evidence/real/real-after-restart-narrow.png`

Observation: Refine screenshots show a focused, prefilled prompt matching attempt 2, an 沿用第 2 次的构图 chip with ×, and collapsed composer advanced parameters. Restart screenshots show both sessions, restored lighthouse thumbnails and cancelled attempt 5. These are visual observations; ARIA values, persistence causality, naturalWidth and exact scroll metrics cannot be proved from pixels. Normal clipping at a scroll-container boundary is not by itself evidence of overlapping DOM regions.

Repair suggestion: Retain these visual checks and verify semantic attributes and restart causality separately. Do not treat the known missing document scrollbar in WKWebView snapshots as a defect.

### R2-batch-B-real-app-008 — status_inconsistency

Criteria: running-other-session; global status consistency

Screenshots:

- `.allforai/verify/screens-recapture/running-other-session-wide.png`
- `.allforai/verify/screens-recapture/running-other-session-narrow.png`

Observation: Both harness screenshots correctly show A as generating, B selected with a completed gradient image, a named busy message, 回到该会话, enabled refine styling and disabled generate/recompose styling. The top global strip nevertheless says 媒体：空闲 and 可开工, contradicting the session-level busy state.

Repair suggestion: Make the harness supply consistent global busy status, then confirm the same consistency with real-app evidence; the screenshots alone do not show whether this discrepancy exists outside the harness.

## Per-screenshot inspection

Pass means the assigned visual state is supported, subject to the listed minor warnings and evidence limits. Fail includes missing required visual evidence; it does not assert an unobserved implementation defect.

- **PASS** `.allforai/verify/evidence/real/real-running-wide.png` — state `real-running`, wide. Running attempt 1, progress bar, cancel, collapsed log, session generating marker, disabled-looking generate and correct current-session status are visible; no image placeholder or attempt actions.
- **PASS** `.allforai/verify/evidence/real/real-running-narrow.png` — state `real-running`, narrow. Running attempt 1, progress bar, cancel, collapsed log, session generating marker, disabled-looking generate and correct current-session status are visible; no image placeholder or attempt actions.
- **PASS** `.allforai/verify/evidence/real/real-refine-prefill-wide.png` — state `real-refine-prefill`, wide. Attempt 2 prompt matches the focused composer; composition chip and × are visible; advanced parameters stay collapsed and there is no new running card. Expanded image continues within a scrollable timeline.
- **PASS** `.allforai/verify/evidence/real/real-refine-prefill-narrow.png` — state `real-refine-prefill`, narrow. Attempt 2 prompt matches the focused composer; composition chip and × are visible; advanced parameters stay collapsed and there is no new running card. Expanded image continues within a scrollable timeline.
- **FAIL** `.allforai/verify/evidence/real/real-timeline-three-rounds-wide.png` — state `real-timeline-three-rounds`, wide. FAIL: attempt 1 is mostly outside the viewport; attempt 3 details and both actions are not visible. Visible thumbnails render real lighthouse pictures.
- **FAIL** `.allforai/verify/evidence/real/real-timeline-three-rounds-narrow.png` — state `real-timeline-three-rounds`, narrow. FAIL: attempt 1 is mostly outside the viewport; attempt 3 details and both actions are not visible. Visible thumbnails render real lighthouse pictures.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-selected-actions-wide.png` — state `real-attempt-selected-actions`, wide. FAIL: both actions and the attempt header are outside the captured area. Wide shows a full lighthouse image; narrow cuts off its bottom.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-selected-actions-narrow.png` — state `real-attempt-selected-actions`, narrow. FAIL: both actions and the attempt header are outside the captured area. Wide shows a full lighthouse image; narrow cuts off its bottom.
- **PASS** `.allforai/verify/evidence/real/real-attempt-cancelled-wide.png` — state `real-attempt-cancelled`, wide. Cancelled badge and grey X block are visible, with no image placeholder or running state. Wide shows both actions; narrow hides the lower expanded contents and both actions.
- **FAIL** `.allforai/verify/evidence/real/real-attempt-cancelled-narrow.png` — state `real-attempt-cancelled`, narrow. Cancelled badge and grey X block are visible, with no image placeholder or running state. Wide shows both actions; narrow hides the lower expanded contents and both actions.
- **PASS** `.allforai/verify/evidence/real/real-after-restart-wide.png` — state `real-after-restart`, wide. Two sessions remain visible; the lighthouse session is selected with five attempts counted. Attempts 3 and 4 show real thumbnails; attempt 5 is cancelled. Earlier attempts are outside the scroll viewport. Narrow clips lower expanded contents, but the assigned AC-3 visual persistence check is supported.
- **PASS** `.allforai/verify/evidence/real/real-after-restart-narrow.png` — state `real-after-restart`, narrow. Two sessions remain visible; the lighthouse session is selected with five attempts counted. Attempts 3 and 4 show real thumbnails; attempt 5 is cancelled. Earlier attempts are outside the scroll viewport. Narrow clips lower expanded contents, but the assigned AC-3 visual persistence check is supported.
- **PASS** `.allforai/verify/evidence/real/real-delete-confirm-wide.png` — state `real-delete-confirm`, wide. Correct modal title and retention wording, fully visible buttons and danger styling. Cancel focus is not visually distinguishable; minor warning.
- **PASS** `.allforai/verify/evidence/real/real-delete-confirm-narrow.png` — state `real-delete-confirm`, narrow. Correct modal title and retention wording, fully visible buttons and danger styling. Cancel focus is not visually distinguishable; minor warning.
- **FAIL** `.allforai/verify/evidence/real/real-library-after-delete-wide.png` — state `real-library-after-delete`, wide. FAIL: real bamboo image and matching library row render, but seeds appear in plain metadata and post-deletion session-list absence is not shown.
- **FAIL** `.allforai/verify/evidence/real/real-library-after-delete-narrow.png` — state `real-library-after-delete`, narrow. FAIL: real bamboo image and matching library row render, but seeds appear in plain metadata and post-deletion session-list absence is not shown.
- **PASS** `.allforai/verify/screens-recapture/running-other-session-wide.png` — state `running-other-session`, wide. B selected with its finished gradient image; A has generating marker; named busy status and return action visible; generate/recompose look disabled and refine enabled. Top global status is inconsistent (note).
- **PASS** `.allforai/verify/screens-recapture/running-other-session-narrow.png` — state `running-other-session`, narrow. B selected with its finished gradient image; A has generating marker; named busy status and return action visible; generate/recompose look disabled and refine enabled. Top global status is inconsistent (note).
- **PASS** `.allforai/verify/screens-recapture/model-missing-wide.png` — state `model-missing`, wide. Missing-image-model message is visible in header and status line; generate looks disabled; selected empty session, composer and collapsed advanced parameters fit.
- **PASS** `.allforai/verify/screens-recapture/model-missing-narrow.png` — state `model-missing`, narrow. Missing-image-model message is visible in header and status line; generate looks disabled; selected empty session, composer and collapsed advanced parameters fit.
