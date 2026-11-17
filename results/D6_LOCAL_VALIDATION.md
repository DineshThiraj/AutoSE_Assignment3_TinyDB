# D6 correction validation — 2026-11-17

Review base: remote main `929f21ae6dfdfdc52473b5602a328c0d77d44023`, rechecked
through the read-only GitHub connector. The exact signed main commit was imported
locally and its object hash verified; the new review branch preserves that parent.
No existing source history was rewritten. This is Codex-assisted implementation and
local verification, not an independent hosted review or student account approval.

The full local command passed **350 tests**: 228 unchanged TinyDB baseline cases and
122 workflow/controller cases. It includes the existing bounded repair integration
and a new budgeted Responses protocol fixture: seven mocked requests, five remote
ledger-contract reservations and 232 actually executed TinyDB cases (228 original
plus four public fixture regressions). Mocked provider/GitHub values are test doubles;
they do not establish hosted execution, account support, CI or billed costs.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=workflow:. /home/user/AutoSE_A2_work/.venv312/bin/python -m pytest -c /dev/null -o addopts= -p no:cacheprovider workflow/tests tests -q
git diff --check
```

Negative checks cover wrong issue/actor/comment/label/PR/repository, stale trigger,
duplicate trial and phase, stale checkpoint, response loss after a successful claim,
concurrent claim/reservation, admission/claim/reservation/broker reruns, extra rounds
or attempts, expired or changed approval, missing/unavailable provider/secret/cap/
pricing evidence, exhausted calls/tokens/USD, missing actual model/tier/usage/cache
fields, unsupported metadata, excess returned output and unknown usage after timeout.

Structural security checks passed: all YAML mirrors equal; every broker has a
reservation gate; broker/reviewer remain read-only; ledger/publisher/executor do not
receive the provider secret; ledger never updates/deletes refs or executes targets;
no merge endpoint was added; changed files parse and pass the credential-pattern
scan. Baseline source/tests, architecture and reuse artifacts are unchanged.

The private freeze verifier passed for all 3,049 frozen payload files and 19 tests.
Manifest SHA-256 remains
`b48cb49922d0957472e8231b3f088af378125278a35c387fcc0c38ab3b5d32d8`.
Private tests were not rerun, edited, regenerated, added to the checkout or published.

Raw console/JUnit, security checks, file hashes and remote metadata are retained in
the private workspace's `evidence/d6_corrections/`; no private test implementation
appears in this change. Actionlint and ShellCheck are unavailable here; Docker's
daemon socket denies access, so local integration uses explicitly marked trusted
fixtures rather than claiming a new container execution. New hosted
REST reservation behavior and paid inference remain unexecuted; local concurrency
tests verify the GitHub REST contract using an atomic in-memory service double.

Live configuration remains disabled. Account-specific support, enforced cap,
secret metadata and separate scoped paid approval are not supplied. Full no-bypass
runtime protection verification is still blocked; existing protected-main/required
tinydb-tests metadata alone cannot substitute. Git transport cannot resolve
github.com here; the branch/PR must be published through a working authenticated
Git transport. No push, workflow trigger, issue comment/label, paid request,
protection change or merge was performed in this correction task.

Assumptions and operator fields are documented in [D6_TRIAL.md](../workflow/D6_TRIAL.md).
GitHub must atomically create refs and supply honest attempt identity; administrators
must preserve ledger tags and trusted code. Provider must honor the selected default
tier, context/output ceilings and verified prices. Human attestations must bind the
actual key/project. Reservations are never refunded, including after hard kills.
CI approval arriving after the polling window has no automatic paid continuation.

Known limitations are preserved: #4 conflicts with two assertions in one unchanged
original regex test; #7 remains clarification-only without a finalized product API
or conflict-resolution oracle. These corrections do not resolve either evaluation case.
