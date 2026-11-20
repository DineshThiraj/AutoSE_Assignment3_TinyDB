# Stage map · submission snapshot

The [original design view](stage-map.md) remains preserved. Each stage writes a checkpoint with a gate status. The controller uses a fail-closed transition graph and a two-round review bound.

| Stage and authority | Input | Output and artifact | Check | Feedback and failure |
| --- | --- | --- | --- | --- |
| Requirements role via broker | Frozen issue, A1 skill, bounded source | Provenance, criteria, uncertainty and `spec.md` | Testable requirements and scope | Critical ambiguity yields `needs_clarification` |
| Design role via broker | Validated spec, A2 constraints, pinned source | File/function mapping and `design.md` | Map every criterion and assess invariants | Incomplete mapping stops. Reviewer may route back to design. |
| Implementer and executor | Spec/design and bounded source | `diff.patch`, compile evidence, detached candidate | Relative allowlisted files and fixed compile | Bounded repair, then stop |
| Test author and trusted supervisor | Frozen candidate, AC map and original suite | `test_report.md`, diagnostic XML and authoritative evidence | 228 case identities and generated coverage bound to candidate/run/environment | Return to implementation inside attempt and time bounds |
| Publisher and protected verifier | Authoritative result, current base and candidate | Fork branch, PR, `pr.md` and CI evidence | Match exact SHA and full allowed tree delta. Require current trusted App result. | Pending evidence blocks. Late-resume path remains incomplete. |
| Isolated reasoning reviewer and publisher | Issue, current head source, diff, optional fixed test result | `review.md`, intended head-specific review and readiness | Fresh evidence-based verdict. Publisher rechecks CI and head. | Route findings to affected stage. Stop unapproved after two rounds. |

Model credentials remain with the broker. The executor has read-only GitHub access and isolated containers. The reviewer can request a fixed test but cannot push. The publisher posts its verdict. `MERGE_READINESS_CHECK` records gates and a pending human decision; automation cannot authorize a merge.
