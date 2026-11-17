# One issue-3 trial: reviewable controls, live disabled

PR #8 security corrections supersede the earlier claim that reservations alone
prevent same-attempt replay. Every provider call now needs an atomically consumed
remote slot through a consumption-only service; read-only broker/reviewer jobs
cannot move refs. Candidate JUnit is diagnostic, and independent signed baseline/
generated verification is required before testing/release/CI pass. Both live and
test-authority configurations remain disabled. See
[the remediation report](../results/PR8_REMEDIATION.md) for demonstrated behavior,
external deployment blockers and the incomplete operational test-authority path.

This change prepares controls. It does not select an approved student model, supply
account evidence, authorize payment or demonstrate hosted execution. `live.json`
remains disabled with `trial: null`. Existing design decisions and source/tests stay
unchanged. Implementation assistance: Codex; the student must verify account facts
and give their own separate paid approval.

Only a new, exact `/autose` issue comment by DineshThiraj, on issue #3, within the
approved trigger window can enter. Label events are rejected for this trial. Current
collaborator permission and all existing repository/protection gates still apply.
The approved scope hash covers number, title, body and URL; the admission snapshot
also hashes `updated_at`, which can legitimately change when the comment is posted.

The ledger job has contents write and Actions read, no provider secret and no
target execution. It creates an isolated audit-data Git history, rooted at a commit
containing only `ledger.json`; this is not replacement TinyDB source history.
`refs/tags/autose-d6-issue-3-claim` binds the only trial to one run, configuration,
issue snapshot, base and comment. Sequential `...-grant-N` tags reserve each model
phase's maximum calls, tokens and estimated USD. Ref creation is the atomic winner
selection. There is no ledger ref update, deletion, mutation retry or refund.
Conflicts, lost write replies, missing records and stale checkpoints stop.

Every paid broker call rechecks the remote claim/grant and authorization. Requirements
and design each reserve two calls; other model phases reserve one. A phase cannot
reserve twice for the same round/attempt. Round and attempt ceilings remain two each;
the trial's smaller numerical budgets can stop earlier. `GITHUB_RUN_ATTEMPT != 1`
is rejected by admission, ledger and broker. Re-running a failed job or whole workflow
does not grant paid recovery. Even another approval ID cannot reopen the fixed claim.
Do not delete these audit tags to make a retry work.

The consumption-only authority also creates `...-consume-N-K` atomically before
each provider call. It validates the immutable grant, numerical envelope, exact
run/job/attempt, fixed slot and request hash. Uncertain consumption stays burned.
`trial.call_consumer` needs the same fresh project-bound evidence fields as other
records, `available: true` and an approved HTTPS URL; that URL is part of the paid
scope hash. The broker receives only `AUTOSE_CONSUMER_TOKEN`, not the service's
GitHub write credential. No such service/token/evidence is provisioned here.

Reservations use the documented model's entire 1,050,000-token context plus the
approved output maximum **per call**, rather than guessing input tokens from bytes.
They always price input as the most expensive permitted cache-write category.
Unused and uncertain reservations remain burned. This deliberately needs much more
approved headroom than likely usage; a small budget can block before the first call.
No allowance amount is chosen or authorized here. A future, separately reviewed
exact tokenizer/counting protocol could narrow reservations.

The only implemented candidate is OpenAI Responses `gpt-6.1-sol`, with explicit
`service_tier=default` and `OpenAI-Project` bound to the approved project. No automatic
model, tier or provider fallback exists. Other returned model/tier values stop with
unknown spend. Requests have no tools, stored conversation or target execution.
Allowed effort values remain low/medium/high/xhigh. The public ID is an alias;
actual returned IDs are recorded, not claimed to be dated immutable snapshots.

`trial_budget.json` records claim/grant SHAs, burned totals, observed usage and each
response's actual model, tier, raw input/output/cache usage and estimated USD.
Missing essential counts, cache lifetime details, model or tier never mean zero.
Reasoning usage is already inside output; cache reads/writes are already inside
input. Count each once. Known incomplete responses keep their usage/cost. A killed
job may lose response evidence: its durable maximum reservation remains, requiring
provider reconciliation. Uploaded phase artifacts are immutable per attempt but
retained for 90 days; archive them separately before expiry.

The dated estimate uses Standard long-context rates, plus 10% uplift even on global
requests. USD nanounits per token: ordinary 4400, cached 220, 30m write 5500,
12h write 11000, output 16500. Sum the disjoint input categories and output. This
upper estimate covers short/long context, both cache lifetimes and regional/FedRAMP
uplift for the permitted tier. It excludes invoice tax/FX and is not billed spend.
Reverify rates before enablement; changed rates require a reviewed code/schedule
update. Do not merely refresh a stale evidence timestamp.

Student configuration requirements (all absent/unverified in this change):

- Existing live preflight: supported adapter/model/effort, output/token bounds,
  evidence locators, verified cap flag, separate paid flag and Unix UTC expiry.
- `service_tier: "default"`; structured `trial` with unique `id`, fixed repository,
  `issue: 3`, approved `issue_hash`, `actor` and `approved_by` DineshThiraj,
  `trigger_not_before`, project ID, currency USD, integer `max_calls` (1..24),
  `max_tokens` (same as `token_budget`, at most 25,584,000), exact decimal-string
  `max_usd` (positive, at most 1000), `expires_at` matching the top-level expiry.
- `trial.approval`, `provider_support`, `hard_cap`, `secret`, `pricing` each need:
  `verified: true`, the same `project_id`, a sanitized `locator`, evidence `sha256`,
  `checked_at` and `expires_at`. Evidence is valid at most 24h and must cover the
  entire approval. These are human attestations, not automated billing verification.
- `approval.scope_sha256` must equal `approval_scope_hash(config)`. Its evidence
  must explicitly approve that scope, including model/effort/output, numerical
  calls/tokens/USD, time/repair ceilings and expiry. Selecting a model or supplying
  a key is not paid approval. Acknowledgment must cover already submitted/in-flight
  work that may finish after expiry and provider enforcement latency.
- `provider_support`: `available: true`, exact model and Responses endpoint;
  verify this account/key can use the request schema and default pricing contract.
- `hard_cap`: `enforced: true`, currency USD, exact decimal-string `limit_usd` and
  positive `remaining_usd`, plus `period_ends_at` covering the approval. The cap
  cannot exceed paid approval. Verify actual project scope and enforcement; alerts,
  prepaid credit and auto-recharge settings do not prove this. Provider enforcement
  can overshoot slightly; leave headroom and reconcile actual billing.
- `secret`: `available: true`, name `AUTOSE_MODEL_API_KEY`, verified binding to that
  project. Check metadata and provisioning securely. Never put a key in a record.
  The broker independently requires the actual environment secret.
- `pricing.schedule: "openai-gpt-6.1-sol-2026-11-17"` with verified pricing evidence.

The first future enablement must be a human-reviewed configuration PR on protected
main, after these facts and separate paid approval exist. Do not trigger during
this implementation review. Main's full no-bypass protection preflight remains
unverified; required-check metadata alone cannot satisfy it.

Publisher still alone creates source branches/PRs and posts reviews; it has no
provider key. Model/reviewer jobs have read-only GitHub authority; the reviewer gets
only issue/diff/source, optionally its own test result. Candidate execution stays
inside the no-network/no-secret container. Evaluator files outside the checkout are
never mounted, uploaded or included in model context.

Exact-head trusted PR CI is still mandatory. Missing, pending, approval-required,
failed or skipped checks cannot pass. Humans may need to approve bot-created PR CI.
Polling ends after five minutes; a completed `action_required` is a safe failure.
No automatic paid continuation after late approval exists for this one-use trial.
The workflow can stop unfinished. Self-review rejected by GitHub remains a labelled
COMMENT and cannot become a platform APPROVED review. No merge operation was added;
`merge_authorized` remains false and the final merge decision remains human.

Security assumptions: GitHub atomically creates unique refs and faithfully supplies
run/job identity. Exactly-once broker execution is no longer assumed: duplicate
same-attempt copies must win the same one-use external slot, or stop.
Repository administrators do not rewrite/delete ledger tags or bypass reviewed
controller code. Provider honors the requested default tier, model context/output
limits and verified rates. Attestations correctly bind the project/key. There is
no guarantee against a compromised provider, platform, administrator or dependency.
The model and candidate code receive none of those administrative capabilities.
The separately audited test authority must establish genuine independent baseline
and generated execution; its signature must never just certify candidate XML.
The checked-in adapter has no signer or actual execution backend. Missing genuine
verification leaves required CI/release blocked rather than accepting the report.

Local verification from repository root (no inference or workflow trigger):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=workflow:. /home/user/AutoSE_A2_work/.venv312/bin/python -m pytest -c /dev/null -o addopts= -p no:cacheprovider workflow/tests tests -q
git diff --check
git diff origin/main -- tinydb tests architecture reuse
python3 -c 'import json; assert json.load(open("workflow/config/live.json"))["enabled"] is False'
```

For a future, genuinely supplied config, the following computes scope only; it does
not approve it or call a provider. Do not copy test fixtures into live configuration.

```sh
PYTHONPATH=workflow python3 -c 'from autose.common import json_load; from autose.trial import approval_scope_hash; print(approval_scope_hash(json_load("workflow/config/live.json")))'
```

Evaluation limitations remain: #4 whole-match behavior conflicts with two assertions
in one unchanged original regex baseline test. #7 is clarification-only, with no
approved product API or conflict-resolution oracle. Frozen private tests are unchanged.

Sources rechecked 2026-11-17: [model](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[pricing](https://developers.openai.com/api/docs/pricing.md),
[cache accounting](https://developers.openai.com/api/docs/guides/prompt-caching),
[Responses](https://developers.openai.com/api/reference/resources/responses/methods/create),
[hard spend limits](https://developers.openai.com/api/docs/guides/spend-limits),
[Git references](https://docs.github.com/en/rest/git/refs).
