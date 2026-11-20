# Observed partial run and continuation

The traces below are **three separate runs** with distinct origins. They do not form one hosted transaction. The [original planned sequence](sequence-plan.svg) is retained.

| Trace | Observed message sequence | Boundary |
| --- | --- | --- |
| [Hosted 44069611603](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44069611603) | Issue comment event → admission job → final evidence job | All 39 downstream jobs skipped. No generated branch, PR or review. |
| [Hosted 44280528872](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44280528872) | Existing draft PR #8 at `f6c727d` → older protected-base verifier → `tinydb-tests` success | CI on infrastructure changes only. No new-authority execution established. |
| [Local Docker 20261118T084516Z](../../results/docker-observed.json) | Coordinator fixture commit → trusted supervisor → observed Docker workers → independently recorded cases → local verdict | Positive 228+4; defective and forged-result controls rejected. Stops before hosted release. |

Proposed continuation for an authorized issue: validated spec and design → isolated implementation/authority → publish exact candidate → authenticated protected dispatch → trusted App check on exact head → fresh reviewer → publisher posts verdict → human merge decision. The App, hosted authorization and late release recovery are unresolved. None of these proposed downstream messages was observed in the hosted issue run.
