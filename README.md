# Rhombus AI – LLM Observability & QA Take-home

A scheduled ETL from **AWS S3** (a messy orders CSV) through a cleaning pipeline built by the **Rhombus AI Builder**, to **Google Cloud Storage**. I then put it through 5 schema drift cases and 2 semantic drift cases, and tested it with Playwright UI tests, API tests and an independent Python data validator.

> **Note:** Partway through, my AI-built pipeline disappeared from the Rhombus canvas, and I had to rebuild the entire pipeline. **All findings, drift results and validation in this repo come from the original pipeline.** The rebuilt pipeline was used only to re-run the UI tests. See [Pipeline rebuild](#pipeline-rebuild-before-submission-f11).

**Demo video:** _ADD VIDEO LINK HERE_
**Dashboard (bonus):** _ADD GITHUB PAGES LINK HERE_ (source: [`dashboard/index.html`](https://speranzadeejoe.github.io/Rhombus-ai-assessment/dashboard/)). It covers pipeline health by scenario, a capability heat map, output consistency, execution time, the validation matrix and the run ledger.

---

## Repository layout

| Folder | Contents |
|---|---|
| `ui-tests/` | Playwright UI tests (5): S3 source, AI-built pipeline, GCS destination, schedule, manual run with log assertions |
| `api-tests/` | API tests (3): one authenticated GET, plus 2 negative tests (no auth, and a forged token) |
| `data-validation/` | `validate.py`: compares the GCS output with the S3 input (schema, row counts, cleaning rules, determinism, semantic drift) |
| `datasets/` | The baseline messy CSV plus 7 drift variants |
| `observations/` | One `.md` per drift case (what changed, what I expected, what happened, logs, chatbot, fix, schedule, how to reproduce), the run log, findings notes, and `evidence/` screenshots |
| `dashboard/` | A static dashboard of drift verdicts, the validation matrix and the run ledger |

## Pipeline

`S3 (orders-source, ap-southeast-2)` → remove duplicates → text cleanup → case standardise → 5 LLM nodes (city, order_date, unit_price, quantity, email flags) → `Data Output → GCS (speranza-rhombus-output/orders_cleaned.csv)`. It runs on a daily schedule.

The baseline has 212 rows, which should become 200 unique orders. It contains duplicates, mixed date formats, `$` prices, blank and non-numeric or negative quantities, bad emails, and inconsistent casing and whitespace.

## Setup

Requirements: Node 18+ and Python 3.9+.

```bash
npm install
```

**Login (once).** Google sign-in blocks Playwright's own browser, so the session is captured from a normal browser instead:

```bash
# Windows. Start Edge with remote debugging, then log in to rhombusai.com in it:
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\rhombus-profile
npm run auth          # saves .auth/state.json (git-ignored)
```

**Run the tests**

```bash
npm run test:ui       # 5 UI tests. Also records the API endpoints the UI calls
npm run test:api      # 3 API tests
npm run report        # HTML report
```

**Data validation**

```bash
cd data-validation
pip install pandas matplotlib
python validate.py         # prints PASS/WARN/FAIL, writes validation_results.csv, exits 1 on any FAIL
python plot_results.py     # validation_results.png
```

The project path is set in `playwright.config.ts` (`PROJECT_PATH = '/workflow/4190'`).

### Test design notes
- **No fixed sleeps.** Every wait is on a UI state, using `expect`, `toPass` or the log counts.
- Rhombus shows an "Ad Blocker Detected" modal in automated browsers. `page.addLocatorHandler` dismisses it whenever it appears.
- Test 5 really runs the pipeline. It asserts that the log gains a new "execution started" entry, then a finished entry, and **no new "Pipeline failed at"**, because Rhombus can log both success and failure for the same run (see D2 and D5).
- API auth: `api.rhombusai.com` **rejects the web session cookie (401)**. It needs a bearer token, which the tests take from `rhombusai.com/api/auth/session`.

### Pipeline rebuild before submission (F11)
Before submission, the original AI-built pipeline disappeared from the Rhombus canvas. There was no warning, and Version Control had no earlier versions to restore (evidence 17–18). The project, schedule, S3 source and runs were unaffected. I rebuilt the pipeline in the same project with the AI Builder, so that the UI tests could be re-run against a real pipeline (evidence 19).

- **All drift results and validation come from the original pipeline (runs 0–18).**
- Even with an explicit prompt specifying DD/MM dates and `$` removal, the rebuilt pipeline repeated the same date-swap and blank-`$`-price bugs. This suggests the bugs come from the AI Builder itself, not from my original prompt.
- The new Data Output node defaulted to "Download Locally". GCS had to be re-added as the destination.
- The chatbot still says GCS is "Not yet supported" as an output, even though the pipeline writes to GCS (same as F1).

## Observations summary

| Drift case | Change | Pipeline stopped? | Chatbot fix worked? | Severity |
|---|---|---|---|---|
| [Drop column](observations/schema-drop-column.md) | `status` removed | No, it carried on and the column silently vanished from GCS | N/A (no error) | HIGH |
| [Rename column](observations/schema-rename-column.md) | `customer_name` → `full_name` | Yes, with a misleading error | Partly: the 1st fix broke the pipeline; the 3rd worked only once I gave it the cause, and it lost trimming | HIGH |
| [Type change](observations/schema-type-change.md) | `unit_price` → `"AUD 89.50"` | No, it carried on; prices correct, currency dropped | N/A | MEDIUM |
| [Add column](observations/schema-add-column.md) | `+ discount_code` | No, handled cleanly | N/A | LOW |
| [All combined](observations/schema-all-combined.md) | All 4 together | Yes (KeyError `status`) | No: 2 fixes, same cached `code_sha` every time | HIGH |
| [Dollars → cents](observations/semantic-dollars-to-cents.md) | prices ×100 | No, Rhombus didn't notice; validation caught it | N/A | HIGH |
| [DD/MM → MM/DD](observations/semantic-mmdd-dates.md) | date convention | No, Rhombus didn't notice; validation caught it | N/A | HIGH |

Before any drift, the **baseline** run already reported success while corrupting the output: prices ×100, emails stripped, IDs altered, 11 dates swapped. The chatbot's fix for that was partial (finding F10).

Other results:

- **Determinism:** a manual run and a scheduled run on the same input produced byte-identical output (md5 `77cdb4e363`). The pipeline is deterministic, but deterministically wrong.
- **Tests:** UI 5/5 and API 3/3 pass ([15](observations/evidence/15-ui-tests-all-pass.png), [16](observations/evidence/16-api-tests-pass.png)).
- **Full run history:** [`observations/run_log.csv`](observations/run_log.csv).

**How the runs were triggered:** Rhombus schedules support a **daily** frequency only. I verified scheduled behaviour end-to-end on the baseline (run 2: a new file landed in GCS and the next run moved forward). The drift cases were triggered **manually** from the Canvas, using the same pipeline and GCS destination, so that each could be tested the same day. Every run's real trigger is recorded in `run_log.csv`. Runs 5–6 are marked invalid, because the drift file had not actually been uploaded to S3. That was my mistake, not a Rhombus issue.

## Top 3 findings

1. **The pipeline reports "success" while it corrupts or drops data.** The baseline run multiplied every price by 100, stripped `@` and `.` from every email, and swapped 11 DD/MM dates, all with 0 warnings. D1 silently dropped a column, S1 inflated revenue 100×, and D3 discarded currency labels. Rhombus has no schema-diff or distribution check, so the only way to catch these is outside validation like `validate.py`.
2. **The AI assistant states wrong diagnoses and fixes with confidence.** It told me GCS isn't a supported destination (it is). Its cleaning report described values that don't exist in the data and claimed "0 failures". It invented a Unicode `＄` cause (the file is pure ASCII). It blamed dtypes for the rename failure. Its D5 fixes claimed to regenerate the code, but the **same `code_sha` ran 3 times**. Its fixes often added new silent regressions (blank `$` prices, lost name trimming).
3. **The logs can't be trusted for monitoring, and pipelines can vanish.** The original pipeline later disappeared from the canvas with no warning and no version history to restore (F11). The same run logs "failed at …" and "completed successfully" in the same second (3 times). Scheduled runs don't appear in Logs at all, so a failed scheduled run could go unnoticed. Error messages hide the cause (D2's "No text columns to convert" means a renamed column).

All findings (F1–F10) are in [`observations/findings_notes.md`](observations/findings_notes.md).

## Usability feedback

The most helpful part was how quickly the AI Builder turned a plain-English cleaning brief into a working 10-node pipeline on the Canvas, and connecting S3 and GCS was smooth. The connection errors named the exact missing permission (`storage.objects.list`), which made them easy to fix. Being able to click "Ask Chatbot" on a failed log line is a good idea, and once I told it the real cause of a failure, it could produce a working fix.

The most frustrating part was not knowing what to trust. The pipeline reports success while it corrupts data. The same run logs both "failed" and "completed successfully". Scheduled runs don't appear in Logs. The chatbot gives confident diagnoses that are wrong (a Unicode `＄` that doesn't exist, a dtype cause for a renamed column) and reports fixes that never apply (the same `code_sha` ran three times). Smaller issues:

- Asking to "clean this data" gave a one-off file rather than a pipeline.
- Schedules are daily only, and "Next run:" shows empty.
- The selected destination is shown only by colour.
- An empty GCS bucket is rejected as a destination.
- Files in the S3 browser can't be clicked to add them to the Canvas.
- The 50 credits ran out quickly while debugging.

What would help most:

- A schema diff and a value-distribution check before each run, with a warning on changes.
- One unambiguous status per run, with scheduled runs shown in Logs and notified on failure.
- Deterministic nodes instead of LLM nodes for simple rules, and a visible cache state for LLM code.
- A date-convention setting.
- Having the chatbot check its fix by re-running the pipeline before it claims success.

## Data validation approach

`validate.py` never trusts the pipeline. It recomputes the expected clean value of every row from the raw S3 input (normalised order_id key, explicit DD/MM parsing, `$` stripping, quantity and email rules). It then joins that to the GCS output and checks:

- the schema and any drift
- row counts and deduplication
- each cleaning rule
- determinism between runs
- semantic shifts, such as the price median against the baseline and dates moved against the baseline

Results are in [`data-validation/validation_results.csv`](data-validation/validation_results.csv) and the chart in `validation_results.png`.
