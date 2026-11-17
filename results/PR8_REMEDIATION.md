# PR #8 security remediation — local verification

This appends corrections to `9ab13c7c668eae22e816cdf3dca2488462df6493` on the
existing `a3/d6-issue3-trial` branch. Earlier commits and the complete original
228-test baseline are preserved. The full security report and its reproduction
limitations were read. No paid API, hosted workflow trigger, issue label/comment,
secret provisioning, protected-main change or merge was performed.

| Original finding | Correction | Defensive regression | Residual risk / status |
| --- | --- | --- | --- |
| **HIGH — candidate-controlled JUnit**, inherited; original executor.py:23,86,100 / engine.py:145 / ci_exact.py:35 | Candidate XML and exit 0 are diagnostic only. The controller writes its own receipt outside the candidate mount. Testing, publisher, release, readiness and exact-head CI require an independent verdict. A pinned Ed25519 public key verifies a signed record bound to nonce, source, exact CI head, run/job/attempt and plan hash. Separate baseline/generated suite identities, completion, exit status, all 228 baseline IDs, generated-file/AC coverage and genuine-result fields are checked. | `test_security_boundaries.py`: valid-looking success XML with failing candidate assertions cannot pass; collection-time early exit cannot pass; signed wrong/incomplete/failed/skipped/stale evidence is rejected. Real OpenSSL verification uses ephemeral test keys. | **Contained by fail-closed gating; operational closure blocked.** No independent execution/signing authority is implemented or deployed here. Its adapter/config are disabled. Merely signing candidate XML is explicitly insufficient. The genuine execution claim depends on a separately audited authority doing independent verification. No production signing key exists in the checkout, runner or candidate. |
| **MEDIUM — grants not atomically consumed**, new D6 gap; original trial.py:214 / broker.py:53,56,93 / cli.py:172 | Before provider HTTP, a limited consumption service atomically creates a fixed `consume-N-K` GitHub ref bound to grant/run/job/attempt/phase/request hash. The broker verifies the durable receipt read-only. Duplicate slots, changed payloads, stale checkpoints, uncertain replies and service failures stop. Reserved numerical envelopes remain burned. A consumption-only reference service has ledger write authority without model credentials; reviewer/broker retain read-only GitHub permissions. | `test_consumption.py`: three independent concurrent copies allow one fake model request; timeout/stale replay and lost consume response remain burned; wrong identity/slot/job/hash, unauthorized operations, unavailable service and expiry are denied. | Corrected at the local protocol/backend boundary. Atomic GitHub writes, HTTPS ingress, authentication and deployment have not been exercised hosted. Admins/other contents-write principals must preserve ledger refs. Provider pricing/limits and genuine project evidence remain assumptions. |
| **LOW — title bypasses body-only scan**, inherited; original engine.py:61,63 / broker.py:134 | Apply the existing credential-pattern screen to every frozen issue field and the complete outbound model context/instructions, before consumption or provider transmission. Failures use constant messages without matched values. | Title/body synthetic-format cases fail admission even with an otherwise matching fixture approval; nested outbound material produces no consumption or model request. | Locally corrected. Regex screening is defense in depth and cannot prove arbitrary content contains no secret. No actual credential was used or transmitted. |

Consumption receipts also bind a fresh per-invocation nonce. A stale successful
service reply cannot authorize another worker, even for the same request hash;
the corresponding defensive test checks this without another model request.

Local result: **395 passed, 0 failed/errors/skips**: 228 unchanged baseline cases
and 167 controller cases, including 45 new defensive regressions. Existing real
TinyDB fixture integration still executes 232 cases. Its provider, publisher and
verification authorities are explicitly test doubles, not hosted evidence. Signed
protocol tests verify cryptographic binding; they do not establish genuine external
test execution. The hosted exact-head success recorded before this remediation
still concerns the earlier revision/base controller, not these corrections.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=workflow:. /home/user/AutoSE_A2_work/.venv312/bin/python -m pytest -c /dev/null -o addopts= -p no:cacheprovider workflow/tests tests -q
git diff --check
```

Workflow generation remains deterministic and mirrored. Broker/reviewer keep
contents/Actions read; only their limited consumption credential is added. Executor
gets a test-authority credential only in the trusted parent; the candidate container
receives neither that credential nor provider/GitHub write credentials. Ledger and
publisher receive no provider key. No merge/auto-merge path was added. Exact-head
identity checks and human-only merge remain mandatory; no green fallback is added.

`live.json` is byte-identical and disabled. `test-authority.json` is also disabled.
Before any future execution, a reviewed HTTPS consumption deployment and token
(`AUTOSE_CONSUMER_TOKEN`) are needed; fresh project-bound `trial.call_consumer`
evidence and its URL enter the paid approval scope. The separate test authority
requires audited independent execution, pinned public verification key, HTTPS URL
and `AUTOSE_TEST_AUTH_TOKEN`. Neither service is provisioned/approved here. Missing
authority means CI/release stay blocked, including for otherwise passing tests.

The reference consumption server binds loopback and exposes only `/v1/consume`;
it is not a production TLS deployment. No automatic provider retry, per-call refund
or idempotency assumption is used. Signed test verification has no local signing
implementation and must never be wired to automatically approve supplied reports.
Signatures authenticate an authority's claims; they cannot make a dishonest or
vulnerable authority's test execution genuine.

Docker daemon access is denied and Git transport cannot resolve github.com.
Consequently no new Docker, hosted REST race, deployed service, hosted corrected CI
or paid execution is claimed. Actionlint/ShellCheck are unavailable. The local
same-attempt regression does not assert that GitHub normally duplicates jobs; it
verifies the reported broker boundary now rejects independent copies.

All 3,049 frozen private payload files verify unchanged; private tests were not run
or published. No standalone exploit reproduction file or secret is in this patch.
#4's unchanged regex baseline conflict and #7's clarification-only oracle remain
unresolved. Implementation and checks were assisted by Codex in the same session;
this is not a separately staffed independent audit or student paid authorization.
