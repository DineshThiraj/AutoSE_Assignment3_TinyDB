# Two retrospective decision experiments

These are recorded local architectural comparisons. Historical prompt- and handoff-variant proposals were not executed. No paid calls or hosted treatment runs are counted.

## E1 · D7 testing authority

| Variant | Procedure | Observed outcome |
| --- | --- | --- |
| A · Candidate report as authority | Historical controlled local fixture against the old validator. A candidate-controlled success report was presented without completed assertions. | Old testing gate accepted once. It reported 229 cases, with zero assertions executed. |
| B · Independent supervisor | Recorded real local Docker harness at `f6c727d`. Supervisor checks isolated baseline and generated execution, coverage, completion, and typed result protocol. | Positive accepted (228+4). Unfixed defect and forged-verdict negative cases both rejected. Five actual container observations. |

The old result is documented in the archived model-assisted security review. B uses a distinct forged-result mechanism, so this is a before/after comparison of the authority boundary with controls, not an identical-input benchmark or a detection rate. The authorized result moved outside the candidate process and kept candidate JUnit diagnostic. See [ADR-011](../architecture/decisions/ADR-011.md), the [remediation summary](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/blob/f6c727df6eaa708046e5258321e3f9865ad3d914/results/PR8_REMEDIATION.md), and the [Docker summary](../results/docker-observed.json).

## E2 · D9 spending enforcement

| Variant | Procedure | Observed outcome |
| --- | --- | --- |
| A · Read-only grant validation | Historical local protocol test ran three concurrent copies with the same one-call grant and a provider double. | 3/3 concurrent copies reached the fake provider. |
| B · Atomic per-call consumption | Repeated the three-copy, one-slot concurrency test against the reference consumption service with an atomic mocked ref backend. | 1/3 reached the fake provider. 2/3 stopped. |

The controller now consumes and verifies a bound receipt before provider HTTP, and burns uncertain reservations. This is a local mock concurrency comparison. GitHub ref atomicity, hosted service entitlement, model cost and latency were not measured. See [ADR-012](../architecture/decisions/ADR-012.md) and [observed remediation results](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/blob/f6c727df6eaa708046e5258321e3f9865ad3d914/results/PR8_REMEDIATION.md).

Run B’s controlled local regressions with `PYTHONPATH=.:workflow python -m pytest -c /dev/null -o addopts= -p no:cacheprovider -q workflow/tests/test_consumption.py workflow/tests/test_authority_backend.py`. This repeats controller checks, not the archived host Docker run or private evaluation.
