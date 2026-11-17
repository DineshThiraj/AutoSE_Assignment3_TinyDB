# Setup required before a real hosted slice

2026-11-17 correction checkpoint: main now exists and is protected with required
tinydb-tests; hosted baseline run 44068724918 passed 228 tests and issues #3–#7 exist.
The infrastructure paragraph below is historical bootstrap evidence, superseded by
the workspace progress/audit records. For the current disabled, single-issue D6
controls and missing student evidence, read [D6_TRIAL.md](D6_TRIAL.md). Full runtime
protection preflight, account evidence, secret verification and paid approval remain
blockers. No live enablement or paid execution is included in these corrections.

Observed fork: DineshThiraj/AutoSE_Assignment3_TinyDB, public, correct upstream parent, master at the original pin. Issues are disabled, main absent, master unprotected and no rulesets returned. The connected integration reports repository admin/push flags but its collaborator/detailed-protection administrative reads returned 403; gh cannot connect in this environment. No remote changes have been made.

1. Provide a usable authorized administrative route or configure the fork in GitHub Settings. Enable Issues and Actions and permit GitHub Actions to create PRs/reviews where supported. Preserve every existing ref. Do not create another repository or rewrite master.
2. Bootstrap the reviewed local design and implementation lineage using normal new branches/fast-forward publication. Set main as default, then enforce PR-only updates, required tinydb-tests CI, no bypass (including admins/apps), no force pushes and no deletion. The initial CI runner must exist on the reviewed base before using exact-head CI for generated issue PRs. The initial bootstrap needs a concrete reviewed publication plan; the workflow cannot merge itself.
3. Verify actual policy using an administrative read/UI export. Runtime prefers detailed classic-protection verification. A read-only GITHUB_TOKEN cannot be granted administration by a workflow permissions stanza. For rulesets, the fallback checks the live effective rules through the metadata-read API and requires workflow/config/repository-preflight.json to contain a separately verified no-bypass record, evidence locator, exact canonical effective-rules hash and expiry within 24h. GitHub hides bypass actors from callers lacking ruleset write access. The fallback therefore does not claim to observe bypass changes; reverify with the admin route immediately before enabling a run. Missing evidence fails closed.
4. Resolve D6: supported exact provider/model/effort, measured usage protocol, provider-enforced hard cap, secure repository secret AUTOSE_MODEL_API_KEY, separate explicit paid authorization with numeric amount and expiry. No model/pricing/cap support has been established. An optional Responses adapter exists; another selected provider may need an adapter. Never enable config merely to bypass missing evidence.
5. With architecture committed, local tests passed and setup evidence verified, create exactly the five drafted issues, then authorize/trigger one nonexperimental vertical slice. Approve pending bot-token CI if required. Record actual Actions URLs, PR/head/check/review URLs and failures. Debug using saved artifacts before freezing experiments. No local fixture URL may be entered as hosted evidence.

Primary API references checked 2026-11-17: https://docs.github.com/en/rest/repos/rules and https://docs.github.com/en/actions/tutorials/authenticate-with-github_token . A hard-cap verification record must come from the selected provider, not these GitHub references. No settings, secrets or caps are claimed configured.

Exact-history publication needs a genuine Git push. The current connector create-commit interface cannot supply author/committer timestamps/timezones; reconstructing local commits through it changes their SHAs. Once the local bootstrap branch is committed, a usable Git transport must publish it unchanged. Do not synthesize replacement design commits or use force.
