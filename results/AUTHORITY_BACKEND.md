# Independent test execution follow-up — operationally BLOCKED

This appends corrections to PR #8, starting at
`e9b5d1387880b7503ffd286d2a32b393e93b1c80`. The full original security report and
its local reproduction limitations were read. No remote deployment, paid call,
issue trigger, secret provisioning, private-test execution or merge occurred.

The **HIGH** finding concerned candidate authority over the verdict producer.
The backend now executes the original pinned test bytes in a trusted interpreter
that never imports candidate Python. TinyDB API operations cross a bounded typed
JSON bridge into a separate candidate process. Production requires Docker with a
pinned, inspected image ID, no network, a read-only root, dropped capabilities,
resource limits and only candidate source, worker adapter and fixture scratch
mounts. Reports, control files, trusted tests and completion records are outside
all worker-writable mounts. Host fixture callbacks are narrowly registered from
immutable tests; their I/O uses no-follow directory traversal and records violations.
This guard mediates trusted callbacks; it is not a Python sandbox.

Generated tests are parsed and interpreted as data, with a restricted syntax and
bounded evaluation. Their module bodies never execute in the trusted interpreter.
Baseline and generated suites use separate sessions/processes. Trusted pytest
hooks independently collect IDs and setup/call/teardown outcomes. The supervisor
requires genuine pytest completion, a successful OS exit, successful worker exit,
no timeout/protocol/filesystem violation, matching report hash, all 228 original
IDs and generated-file/acceptance-criterion coverage. Candidate XML, messages or
exit zero cannot supply these authoritative facts. No remote signing fallback or
production signing credential is used. Archived signature-parser tests remain.

Before testing, a publisher-only phase freezes a detached candidate commit without
creating a branch or PR. Read-only execution verifies that GitHub's immutable Git
objects match the complete source snapshot and issue/run commit message. Records
bind repository, issue number/content hash (or PR number), admitted run, current
Actions run/attempt/job, exact commit, source/plan hashes, a fresh nonce, controller
code hash, image ID, baseline hash and recorded interpreter/dependency identities.
Nonce directories are reserved atomically and never recycled after uncertainty.
Release verifies the frozen commit again and publishes that same tested SHA.
Existing exact-head CI, fresh reviewer context/read-only reviewer permissions,
one-use spending consumption, numerical budgets and human-only merge remain.

| Regression coverage | Direct local result |
| --- | --- |
| Controlled known public fix, actual supervisor/bridge execution | 228 original + 4 generated cases pass; record explicitly `verified: false`, `fixture_only: true` |
| Original unfixed source, generated `assert False`, stricter incorrect Mapping check | Actual independent suites fail; no success record is produced |
| Generated top-level execution, report writes, reflection, unsupported syntax | Rejected before worker startup |
| Missing completion; altered nonce/run/commit/issue/environment/report/exit/coverage/phases; failed worker/timeout | Rejected |
| Reused execution nonce, unknown verdict/callback/frame types, missing result value | Rejected; protocol violations latch failure |
| Shared scratch symlink or callback file descriptor targeting verifier data | Actual OS guard denies access; protected bytes remain unchanged |
| Wrong hosted run/job/attempt, differing remote source/message, wrong image | Rejected with explicit API/Docker contract doubles; no hosted claim |
| Detached freeze, changed commit metadata/source, wrong tested head/issue/run | Publication denied; valid contract publishes the pretested SHA without another commit |

Full local result: **456 passed, zero failures/errors/skips**: **228 unchanged
native TinyDB baseline cases + 228 controller cases**. This adds 61 regressions
(53 backend, 8 publication) to the previous 395. The new backend's positive
integration also executes the byte-identical 228-case suite through its bridge;
that nested execution is not an additional top-level pytest count. The first full
run had two new test-double setup failures; fixing their overly broad subprocess
interception produced the stated complete passing run. Both logs are preserved.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=workflow:. /home/user/AutoSE_A2_work/.venv312/bin/python -m pytest -c /dev/null -o addopts= -p no:cacheprovider workflow/tests tests -q
PYTHONDONTWRITEBYTECODE=1 /home/user/AutoSE_A2_work/.venv312/bin/python workflow/generate_workflows.py
git diff --check
```

Generated workflows remain synchronized with their source and mirrors. Four
bounded freeze phases are added (62 total jobs); execution gets read-only GitHub
access for exact source lookup, without model, consumption or publisher credentials.
Trusted pytest/PyYAML install before candidate execution. The verifier records their
versions/code hashes. Actions and package dependencies remain trusted supply-chain
assumptions; version pins/hashes recorded after installation are not provenance proof.

**Remaining blockers and security limits:** Docker socket access is denied here.
Production container isolation, hosted immutable-object freezing, mounts, process
termination, filesystem race resistance and evidence upload have not been verified
operationally. Local fixture execution is explicitly unsandboxed, accepts only
coordinator-controlled data and cannot authorize any production gate. Structural
mount tests use doubles. The API bridge is a constrained compatibility profile,
not proof of native Python equivalence for arbitrary subclasses/type introspection;
passing finite tests cannot exclude overfitting or establish semantic correctness.
The trusted controller, immutable tests, interpreter, dependencies, kernel/Docker
and GitHub identity/artifact integrity must remain uncompromised. This substantial
new boundary needs independent review and hostile-container validation before any
closure or enablement claim. Actionlint/ShellCheck are unavailable.

Hosted run [44145180923](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44145180923)
genuinely passed at the prior e9b5d13 head. It executes the trusted base controller
from main, not this backend or its new regression suite. No hosted run of these
corrections occurred. Bootstrap/deployment must preserve protected-main review;
an existing base-controller green check is insufficient verification of this patch.

Both `live.json` and `test-authority.json` remain disabled; the latter has no image
digest. Smallest next step: independently review this patch, then validate it on a
disposable no-secret Docker host using controlled fixtures and a reviewed pinned
image, without inference or issue triggers. Deployment and real hosted verification
remain blocked. Consumption-service deployment, student provider/hard-cap/secret
evidence, separate paid authorization and full protection preflight are still open.

All **3,049 frozen payload files / 19 private tests** verify unchanged; manifest
SHA-256 remains `b48cb49922d0957472e8231b3f088af378125278a35c387fcc0c38ab3b5d32d8`.
Private tests were not run or published. **#4** still conflicts with the unchanged
regex baseline; **#7** remains clarification-only without a finalized product oracle.
Implementation and checks are Codex-assisted self-validation, not a separately
staffed independent audit or student spending approval.

Exact changed-file/hash manifest and actual console/JUnit/security/freeze evidence:
`~/AutoSE_A3_work/evidence/authority_backend/`. The commit SHA is recorded there and
in workspace `PROGRESS.md` after committing; it is not inserted into its own tree.
