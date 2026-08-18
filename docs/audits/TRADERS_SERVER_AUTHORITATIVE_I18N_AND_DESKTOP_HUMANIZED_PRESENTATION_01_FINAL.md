# TRADERS_SERVER_AUTHORITATIVE_I18N_AND_DESKTOP_HUMANIZED_PRESENTATION_01

## Verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SERVER_AUTHORITATIVE_I18N_AND_DESKTOP_HUMANIZED_PRESENTATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
```

This task changed tracked server and desktop source, tests and documentation
only. It performed no production deployment or restart and no database, grant,
Control, trading, canary or LIVE mutation. Nothing was pushed. Mobile source
remained byte-for-byte at its original Git commit.

## Baselines and commits

| Repository | Branch | Before | Project-state commit |
|---|---|---|---|
| server | `feature/engine-platform` | `48ee2c2e874e528f28d4bde8581037e9faaa53bf` | `87ac12af0d900ed1d35baf09dd95294ed6fc1649`, `5b7bd7c` |
| desktop | `main` | `e16e48fdb78e605d0c3c6232946537ee241a8708` | `e14ac27dc7f9b441c666a97bc7598f124e962311`, `7737046` |
| mobile | `main` | `013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db` | unchanged |

All three roots were clean at the safety gate. No reset, clean, rebase,
worktree, repository copy or archive was used.

## Architecture and contract

`app/i18n` owns 792 namespaced keys in each of RU and EN. Validation proves
zero missing keys, exact placeholder parity, bounded schema content and a
canonical public-content SHA-256. The proven catalog identity is
`8792dfefd2e4e0fabd8251263c8d093282e372ba6d794d7b9a5df0cb7b101884` and
version `i18n-8792dfefd2e4e0fa`. Ninety-eight public state enum values and all
106 funnel reason values are covered in both locales. The reason gate derives
102 values directly from the Setup, Strategy, Risk and Paper source enums and
adds four projection-owned reasons. Business APIs and objects keep raw values.

Exactly two source-only GET routes were added: manifest and locale catalog.
The source contract moved from 25 GET / 0 write to 27 GET / 0 write. Static
catalog export has no DB dependency, no per-key queries and no write route.
Unknown locale validation is the standard 422 response. The current production
runtime was not changed and remains its previously accepted 25 GET / 0 write.

## Desktop remediation

The previous 816-line hand-maintained desktop catalog was replaced by a loader
for a generated, DO-NOT-EDIT server snapshot. The server generator also owns
the generated desktop Help catalog. The desktop uses the existing guarded
Readonly transport for manifest/catalog fetches, renders immediately from a
valid LKG/bootstrap, downloads only on identity change, validates locale,
schema, canonical hash and placeholders, and atomically replaces the cache.
Invalid input never replaces the LKG.

The Market Strategy root cause was a hardcoded `READ_ONLY` argument in
`MarketView.update_state`; the server DTO and desktop model already exposed
`strategy_status`. The column now binds that field, while access mode remains
top-level only. Dashboard Markets is now a bounded `ttk.Treeview` with
localized headers and the existing aggregate data, adding no request.

Scenarios use context-specific scenario/status/direction namespaces. Funnel
stage/status/reason are human labels with the raw reason confined to details.
PAPER/Control uses contextual boolean labels, human control/canary states and
human reconciliation statuses; technical policy IDs are not primary labels.
`current_mutation_ready` remains exactly next-operator-ARM-transition
readiness. Known code fallbacks in the changed normal UI are zero; genuinely
unknown future codes show a localized generic label and raw diagnostic detail.

The shared completion state previously retained the `LOADING` presentation
because success had no completed timestamp/render branch. Successful page
loads now record `completed_at` and render localized `Updated HH:MM:SS` while
real in-flight work still shows loading. Locale switching changes no business
state and persists only the local preference.

## Test and scanner evidence

```text
SERVER_FOCUSED_I18N_API = 32 passed
SERVER_CONTRACT_RETRY = 216 passed
SERVER_EXTENDED_READONLY_SECURITY = 2563 passed, 2 skipped
DESKTOP_FOCUSED_I18N = 16 passed, 13 subtests passed
DESKTOP_FULL = 1441 passed, 2 skipped, 3020 subtests passed
SERVER_COMPILE = PASS
DESKTOP_COMPILE = PASS
DIFF_CHECK = PASS_BOTH_REPOSITORIES
SECURITY_SCANNER_REGRESSION = PASS_IN_EXTENDED_SERVER_SELECTION
SECRET_SCANNER_REGRESSION = PASS_NO_SECRET_FIELDS_AND_TRACKED_SECURITY_TESTS
NORMAL_UI_RAW_MACHINE_CODE_LEAK_TEST = PASS
GENERATED_BOOTSTRAP_MATCHES_SERVER_CATALOG = PASS
```

The extended server selection emitted only a Starlette deprecation warning and
an unrelated Windows temporary-directory cleanup warning. An initial desktop
attempt in the server venv lacked the external `cryptography` package; the
approved desktop system-Python environment then completed the full green run.
There was no product assertion failure hidden by that environment distinction.

## Mobile and next action

The contract is JSON/platform-neutral and shares exactly the same keys and RU/EN
semantics with future Android. Mobile source was not touched. The next source
task is `TRADERS_MOBILE_SERVER_I18N_CONSUMER_MIGRATION_01`, followed by
`TRADERS_CROSS_CLIENT_I18N_PARITY_ACCEPTANCE_01`. If Android first requires
runtime availability, a separate narrow Readonly i18n deployment acceptance
must be authorized; this task did not perform it.
