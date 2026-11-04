# Image sessions: visual acceptance closure audit

- Auditor: reviewer-1 (claude -p fresh context)
- Reconciliation: `.allforai/verify/ui-visual-reconciliation.json`, status **failed_visual_review**
- **Closure status: OPEN.** 6 of 8 blocking items have not been repaired or re-reviewed.

## Checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Both independent reports exist and neither read the other before writing | **pass** | Both `visual-review-{1,2}.{json,md}` exist, merged verbatim from their batch files. `reviewer-prompt.txt` rule 3 forbids reading other `visual-review-*` or reconciliation/audit files. Reviewer 2 states explicitly that it read no other report. The batch files were written almost at the same time (A: 05:26 / 05:27; B: both 05:44), and neither report cites the other's ids. Caveat: reviewer 1 has no explicit non-reading statement. |
| 2 | Every required state × viewport in the manifest was inspected by both reviewers | **pass** | 20 states × 2 viewports = 40 required. `required_missing=[]` and `files_missing=[]`. Both `inspected[]` lists are the same 68 paths (40 required + 8 supplementary + 16 real-app + 4 re-captures), each with a verdict from both reviewers. |
| 3 | Every issue cites screenshots that exist | **pass** | All cited `.png` paths in both reports exist (checked with `ls`). The reconciler also opened 4 screenshots where the reviewers disagreed. |
| 4 | Every blocking issue is routed to a repair owner | **pass** | U-01 to U-08 cover every blocker/major from both reviewers. Each has a category and an owner. No major was dropped or downgraded. |
| 5 | Repairs executed and re-captured / re-reviewed | **pending** | Only U-07 and U-08 are closed: re-captured (`pytest-e2e-recapture.json`: 2 passed), marked superseded in the manifest, and passed by both reviewers. U-01 to U-06 are untouched. |

## Blocking union (merged by root cause)

| id | Root cause | Raised by | Category → owner | State |
|---|---|---|---|---|
| U-01 | At 900×700 the timeline is not scrolled to the expanded card's action row after settle, expand or resize. `probe.json`: scrollTop 10/46 and 144/180; buttons at y 543–578 against a timeline bottom of 558. | R1-A-001, R2-A-003, R2-A-002 (narrow), R1-B-003, R2-B-003 | code_gaps → image-session-repair | open |
| U-02 | With a real 512² image, the expanded card is taller than the timeline, so an earlier attempt's header, image and two actions are never visible together. | R1-B-001, R2-B-001 | code_gaps → image-session-repair | open |
| U-03 | No timeline-three-rounds capture shows 第1→第2→第3 plus the expanded 第3's image, prompt, 高级参数 and actions. | R2-A-002, R1-B-002, R2-B-002 | test_gaps → image-session-verify (after U-01/U-02) | open |
| U-04 | The cancelled card has no explanation line. The message `已取消：这次生成被手动停止` is stored, but the UI reason is null. | R1-B-004 (major), R1-A-006 (minor), R2-A-006 (minor) | code_gaps → image-session-repair | open |
| U-05 | library-after-delete: no capture shows the image-page list after the delete (the API listing shows the session gone). | R1-B-005, R2-B-005, R1-A-009 (minor) | test_gaps → image-session-verify | open |
| U-06 | 素材库 rows show `种子 <n>`. The criteria as written forbid it; whether the library counts as 主流程 is undefined. | R2-A-005, R2-B-004 (major); R1-A-010, R1-B-012 (note) | contract_gaps → image-session-repair | open |
| U-07 | running-other-session was captured with an empty session B. | R1-A-002, R2-A-001 | test_gaps → image-session-verify | **resolved by re-capture** |
| U-08 | The model-missing fixture also removed the runtime, so the wrong status-line reason showed. | R1-A-003, R2-A-004 | test_gaps → image-session-verify | **resolved by re-capture** |

## Disagreements settled

- **种子 in the library:** reviewer 1 rated it a note, reviewer 2 major. Kept as a major (U-06). I opened `library-after-delete-wide.png` and the seeds are visible. The written criteria side with reviewer 2.
- **Cancelled explanation:** reviewer 1 rated it major (B) and minor (A); reviewer 2 rated it minor (A) and did not raise it in B. Kept as a major (U-04). I opened `real-attempt-cancelled-wide.png` and there is no explanation line; the journey record shows the text exists but isn't rendered.
- **Harness timeline-three-rounds-wide:** reviewer 1 passed it, reviewer 2 failed it. I sided with reviewer 2: the 第 1 次 label is scrolled out. Merged into U-03.
- **Harness refine-prefill-narrow:** reviewer 1 passed it, reviewer 2 failed it. The state's own must-show items are all present. The cut-off action row is the U-01 cause, so the screenshot is kept under U-01.
- **Minor/note splits (non-blocking):** delete-dialog focus ring (N-01), header 媒体：空闲 during a job (N-03), harness image at thumbnail size (N-04), real refine-prefill clipping (N-05). Each keeps the higher of the two severities.

## Needed to close

1. image-session-repair: fix U-01, U-02 and U-04. For U-06, get a scope decision on the criteria or hide 种子 in the library.
2. image-session-verify: make the scripted PNG match the declared size. Re-capture attempt-selected-actions, timeline-three-rounds (as a declared top/bottom pair), attempt-cancelled, verify-failed-and-cancelled, the narrow timeline states, and a post-delete image-page list, in both batches where they apply.
3. Both reviewers re-review the re-captured states independently, then re-run this audit.
