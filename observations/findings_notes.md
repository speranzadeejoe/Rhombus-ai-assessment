# Findings Notes – Rhombus AI Assessment (running log)

**Status (2026-10-05):** all parts complete.

Evidence screenshots live in `/observations/evidence/`, numbered in order.

| # | Evidence | Summary |
|---|---|---|
| 01 | 01-s3-file-uploaded.png | Baseline CSV in S3 `input/` |
| 02 | 02-gcs-bucket-created.png | GCS output bucket created |
| 03 | 03-rhombus-s3-connected.png | S3 source connected in Rhombus |
| 04A–04F | 04A…04F-ai-builder-cleaning-report.png (+ .md text) | AI Builder cleaning report (6 parts); 04 also shows empty Canvas |
| 05 | 05-10-node-canvas.png | 10-node pipeline built on Canvas |
| 06 | 06-gcs-output-file.png | orders_cleaned.csv landed in GCS bucket |
| 07 | 07-destination-provider-list.png | Destination providers: S3, Azure, GCS, Snowflake (disproves chatbot, F1) |
| 08 | 08-schedule-settings.png | Daily schedule created |
| 09A | 09A-schedule-next-run-23h.png | Schedule advanced to next day after run |
| 09B | 09B-gcs-scheduled-output.png | New cleaned file in GCS from scheduled run (baseline) |
| T1 | evidence_log_excerpts.md | Chatbot diagnosis + 3 node patches (text) |
| T2 | evidence_log_excerpts.md | 2nd fix attempt (text) |
| T3 | evidence_log_excerpts.md | Drop-column logs (text) |
| 10 | 10-rename-column-logs.png | Rename: failed + 'completed successfully' |
| T4 | evidence_log_excerpts.md | Rename logs + chatbot dtype diagnosis (text) |
| 11 | 11-rename-fix-failed-logs.png | Chatbot fix produced new config error |
| 12 | 12-rename-fix2-logs.png | Rename fix #2: pipeline completes |
| 13 | 13-type-change-logs.png | Type change: success, no warning |
| 14 | 14-add-column-logs.png | Add column: success, no warning |
| 15 | 15-ui-tests-all-pass.png | Playwright UI tests 5/5 pass |
| 16 | 16-api-tests-pass.png | API tests 3/3 pass (2 negative) |


---

## F1 – Chatbot confidently hallucinated a product limitation (HIGH)
- **What:** Asked twice (different wording), the in-app chatbot said GCS is NOT supported as an output destination; listed outputs as Rhombus storage, S3, **PostgreSQL**, and suggested an S3→GCS workaround.
- **Reality (UI):** Output node → "Select Destination Provider" shows **Amazon S3, Azure Blob Storage, Google Cloud Storage, Snowflake**. GCS *is* supported; PostgreSQL not listed; Azure & Snowflake omitted by chatbot.
- **Consistency:** Wrong answer was *consistent* across both phrasings — consistency ≠ correctness.
- **Impact:** A user trusting the assistant would build an unnecessary workaround or abandon the requirement.
- **Evidence:** chatbot answers (2 phrasings) + 07-destination-provider-list.png.

## F2 – AI Builder cleaning report contains false / hallucinated claims (HIGH)
- **What:** Report is polished and confident, but checked against known ground truth:
  - Claims "zero invalid dates / 0 failures" — baseline has **5 blank dates**.
  - City table lists raw values `bris`, `mel`, `MELB`, `PERTH`, `syd` — **none exist** in the data.
  - Examples `arjun martin` and `SHIPPED` — **don't exist** in the data.
  - Quantity: reports 9 missing + 6 negative, but **omits 2 non-numeric ("two") rows**.
- **Correct parts:** 12 duplicates, 200 rows, 22+11 emails, 5 blank prices.
- **Why it matters:** users would trust a report that misstates what happened — an LLM-observability issue.
- **Verified against output file:** see F3–F5 below — report's "0 failures" claim is false.
- **Evidence:** 04A–04F screenshots + 04-ai-builder-cleaning-report.md

## F3 – Silent data corruption: YYYY/M/D dates get day & month swapped (HIGH)
- **What:** Raw dates in `YYYY/M/D` form where day ≤ 12 were parsed as `YYYY/D/M`.
  - ORD-1171 `2026/1/10` → **2026-10-01** (should be 2026-01-10) — also a future date
  - ORD-1142 `2026/6/5` → **2026-05-06** (should be 2026-06-05)
  - ORD-1187 `2026/5/12` → **2026-12-05** (should be 2026-05-12) — future date
- No warning, no flag; report claimed "all converted, 0 failures".
- Note: all 30 `DD/MM/YYYY` dates (incl. 12 ambiguous) were converted correctly.
- **Evidence:** orders_cleaned_run0.csv vs orders_baseline.csv (verification script; to be formalised in /data-validation/)

## F4 – Non-numeric quantity silently blanked, not flagged (MEDIUM)
- ORD-1193 and ORD-1119 had quantity `two` → output quantity is empty and `quantity_flag` is empty.
- Prompt explicitly asked to flag/remove "not a number" rows. Report omitted these rows entirely.

## F5 – Minor spec deviations (LOW)
- Quantity output as float (`4.0`) instead of integer as instructed.
- 5 blank dates left blank with no flag.

## F6 – Download link in AI report didn't work (LOW, usability)
- `artifact://` download link in the report failed; file had to be retrieved via Workspace.

## F7 – AI Builder "clean this data" produced a one-off result, not a pipeline (MEDIUM, usability)
- Cleaning prompt produced orders_cleaned.csv in Workspace + a report saying "Everything ran cleanly", but the Canvas stayed **empty** — nothing reusable or schedulable was built.
- Had to explicitly ask for a Canvas pipeline. A user expecting a scheduled ETL would not realise nothing was built.
- **Evidence:** 04 (screenshot shows empty Canvas alongside the "ran cleanly" report)

## F8 – Half the pipeline is LLM nodes, even for deterministic rules (MEDIUM – determinism risk)
- Canvas pipeline (10 nodes) built by AI Builder: 5 are **LLM** nodes — standardise_cities, parse_dates, clean_unit_price, clean_quantity, flag_emails.
- Tasks like stripping `$` or casting to int are rule-based; using an LLM makes output potentially non-deterministic and slower.
- Likely root cause of F3 (date day/month swap).
- **To test:** run same input 3× and diff outputs (determinism / dashboard consistency panel).
- **Evidence:** 05_10-node Canvas.png + AI Builder node table.
- Also: AI Builder said output writes to S3 need an S3 destination configured in project settings first.

## F9 – Scheduled runs are invisible in Logs (MEDIUM – observability)
- Daily schedule set for 03:50. At run time, **no entry appeared in Logs** (only manual runs show there).
- Run DID happen: a new cleaned file appeared in the GCS bucket at the scheduled time, and 'next run' advanced to +23h.
- Only way to confirm a scheduled run was checking the destination bucket manually — a failed scheduled run could go unnoticed.
- Also: schedule frequency options / time zone not clearly shown.
- **Evidence:** 08-schedule-settings.png, 09A-schedule-next-run-23h.png, 09B-gcs-scheduled-output.png.

## F10 – Canvas pipeline reports success but corrupts the baseline output (CRITICAL)
- Scheduled baseline (run 2) and manual run 1 are **byte-identical** (md5 77cdb4e363) → deterministic, but both badly wrong vs ground truth:
  - **unit_price ×100** on all 195 prices (349.00 → 34900.0) — decimal point stripped.
  - **All 179 valid emails destroyed** (`@` and `.` stripped) → every one flagged INVALID_EMAIL.
  - **6 negative quantities turned positive**; NEGATIVE_QUANTITY flag never raised.
  - **order_id hyphen stripped** on every row (ORD-1047 → ORD1047) — breaks joins to source.
  - **11 DD/MM/YYYY dates parsed as MM/DD** (08/04/2026 → 2026-08-04; should be 2026-04-08).
  - **1 duplicate survived** (ORD1025 twice) → 201 rows instead of 200.
  - Blank dates now marked `INVALID_DATE` (improvement over chat version).
- Likely root cause: `trim_whitespace` (Text Cleanup) node strips punctuation from **all columns**.
- Pipeline status: success, 0 warnings, 0 errors.
- **Same prompt, different logic:** chat-built clean (run 0) vs Canvas pipeline disagree — chat got prices/emails/DD-MM right but YYYY/M/D wrong; pipeline the reverse on dates.
- **Chatbot diagnosis (evidence T1):**
  - Bug 1 (text_cleanup on all columns strips `@ . -`): ✅ correct. Fix: scope to customer_name, city, product, status.
  - Bug 2 (auto-converted Timestamps parsed month-first): plausible. Fix: re-parse strings, dayfirst=True fallback.
  - Bug 3 (ORD-1025 dup "differed in whitespace/casing"): ❌ **wrong** — the two rows are byte-identical in source. Real cause: ORD-1025 is the only one of 12 dup pairs with a blank field (order_date) → NaN≠NaN, so all-column dedup misses it. Fix (dedup on order_id only) likely works for the wrong reason, and risks silently dropping distinct rows that share an ID.
- **Fix verification (run 3, md5 abe69d9dde, 200 rows):**
  - ✅ Emails intact (167/167), flags correct (22 missing, 11 invalid).
  - ✅ order_id hyphens kept; prices no longer ×100; duplicate removed (200 rows).
  - ✅ 6 negative quantities now flagged NEGATIVE_QUANTITY (value blanked, not kept).
  - ✅ `two` now flagged (as MISSING_QUANTITY rather than INVALID).
  - ❌ **Bug 2 NOT fixed:** the same 11 DD/MM/YYYY dates still parsed as MM/DD — chatbot claimed it was fixed.
  - ❌ **New regression:** 6 `$`-prefixed prices (e.g. ORD-1001 `$79.00`) now **blank** — worked before the fix.
- **2nd fix attempt (evidence T2):**
  - Dates: claims `parse_dates` was in cached code mode so the prompt patch had no effect; now pinned to deterministic string-split code. (Plausible — verify on rerun.)
  - `$` prices: claims the 6 rows used a Unicode full-width dollar `＄` (U+FF04). ❌ **Fabricated** — all 6 are ASCII `$` (0x24) and the file has **0 non-ASCII characters**. Fix (`re.sub(r'[^\d.]','')`) may still work.
  - Pattern: assistant confidently invents root causes; fixes sometimes work despite wrong diagnosis.
- **2nd fix result (run 4):** output **byte-identical** to run 3 (md5 abe69d9dde). Neither the date fix nor the price fix took effect, despite "Both patches compiled and saved successfully".
- **Verdict:** chatbot fix = PARTIAL. Diagnosis 1 right, 2 right-sounding but fix ineffective, 3 wrong reason. Fix introduced a new silent data-loss bug.
- **Evidence:** orders_cleaned_run1_manual.csv, orders_cleaned_run2_scheduled.csv vs orders_baseline.csv.

## Determinism result
- Run 1 (manual) vs run 2 (scheduled), same input → **identical output** (md5 77cdb4e363). Deterministic — but deterministically wrong.

## D1 – Schema drift: drop column `status` (HIGH)
- Input: status column removed (212 rows).
- Result: pipeline **carried on**, "completed successfully", 0 warnings, 0 errors (11:37:23–11:37:29).
- GCS output: 200 rows, **`status` column silently missing**; all other values identical to baseline.
- `standardise_casing` node (configured for status) did not fail or warn.
- Downstream consumers expecting `status` would break with no upstream signal.
- Chatbot not needed (no error to diagnose) — note: silent success is the problem.
- **Evidence:** T3 (log excerpt), orders_cleaned_run7_drop_column.csv.

## D2 – Schema drift: rename customer_name → full_name (HIGH)
- Pipeline **stopped**: "Pipeline failed at standardise_casing: No text columns to convert" (11:45:29).
- **Contradictory logs:** same second also shows "Pipeline execution completed successfully".
- **Misleading error:** `status` (a text column) still exists; the real cause is a missing `customer_name`. Message doesn't name the missing column.
- **Chatbot diagnosis (T4): wrong.** Blamed dtype/"mixed-type content from Athena/S3"; never mentioned the renamed column — the only change. Fix: replaced standard node with an LLM node that casts `customer_name` + `status` to string (still references the now-missing `customer_name`; adds another non-deterministic node). **Fix result (run 9): FAILED** — new error "LLM transform requires a non-empty prompt when code is not provided"; chatbot created an empty/misconfigured LLM node. Logs again show "completed successfully" at the same second (11:54:28). Evidence: 11-rename-fix-failed-logs.png.
- **3rd attempt (told the real cause):** pipeline completes (run 10). `full_name` kept and title-cased, other columns identical to baseline — BUT **13 names keep leading/trailing spaces** (e.g. "  Ethan Patel "): trimming silently lost. Verdict: chatbot can fix when given the cause, cannot diagnose alone; fix still introduced a silent regression. Evidence: 12-rename-fix2-logs.png, orders_cleaned_run10_rename_fixed.csv.
- GCS output from failed run: pending check.
- **Evidence:** 10-rename-column-logs.png, T4.

## D3 – Schema drift: unit_price number → text "AUD 89.50" (MEDIUM)
- Pipeline **carried on**, success, no warning.
- All 195 prices parsed to the correct numeric value — `clean_unit_price` (`re.sub(r'[^\d.]','')`) strips any non-digit text.
- **Currency label silently discarded:** a feed switching to "USD 89.50" or "89.50 EUR" would be merged into the same column as AUD with no flag — type change handled, but *meaning* change is invisible.
- Row count 200; other columns unchanged vs previous run.
- Evidence: 13 (logs), orders_cleaned_run11_type_change.csv.

## D4 – Schema drift: add column `discount_code` (LOW)
- Pipeline **carried on**, success, no warning.
- New column passed through **unchanged, in its original position**; all other columns identical to the previous run.
- Handled cleanly. Only gap: no notice that the schema changed — a new column (possibly sensitive or needing cleaning) flows to the destination unreviewed.
- Evidence: 14 (logs), orders_cleaned_run12_add_column.csv.

## D5 – Schema drift: all four changes combined (HIGH)
- Pipeline **stopped**: "Pipeline failed at standardise_casing: LLM execution failed (code_sha=2fdb126297dd): 'status' --- Generated code --- import pandas as…" (12:15:57).
- Cause: `status` dropped; chatbot's rename fix hardcoded `status`.
- **Contradicts chatbot's promise** (run 10 fix): "resilient to the upstream rename and any future equivalent change".
- Error is a raw KeyError + dumped generated code — specific but not user-friendly.
- **3rd occurrence** of failure + "Pipeline execution completed successfully" logged in the same second → systemic log contradiction.
- **Chatbot diagnosis: correct** (unguarded `status` access). **Fix failed twice** (runs 14, 15) despite promising the node was resilient to future column changes. Attempts stopped at agreed limit.
- **Same `code_sha=2fdb126297dd` in all 3 failures** (12:15:57, 12:19:07, 12:21:34). Chatbot claimed its fix "changes the code_sha and forces the LLM runtime to regenerate fresh code" — it did not; stale cached code ran every time. Hard evidence the claimed fix never took effect.
- Credits after D5: 3/50.
- Evidence: T5–T6 in evidence_log_excerpts.md (log text with code_sha).

## S1 – Semantic drift: dollars → cents (HIGH)
- Structure identical; unit_price values ×100 (349.00 → 34900).
- Pipeline **success**, no warning, no flag. **Rhombus did not notice.**
- Output: every price 100× baseline (laptop $1,299 → 129,900; mean price ×100). Only column that differs from baseline is unit_price.
- Revenue/aggregates downstream would be inflated 100× silently.
- Detection needs a data-validation check (e.g. price range / distribution vs baseline) — to implement in /data-validation/.
- Evidence: orders_cleaned_run17_semantic_cents.csv.

## S2 – Semantic drift: DD/MM → MM/DD dates (HIGH – reveals hidden assumption)
- Source switched all slash dates to US MM/DD/YYYY (same column, same type).
- Pipeline **success**, no warning. Output dates: **0 wrong** (vs **11 wrong** in the DD/MM baseline).
- Meaning: the date parser silently assumes **month-first**. It is "correct" only when the feed happens to be MM/DD; the original Australian DD/MM feed is the one that gets corrupted (F3/F10).
- Rhombus cannot tell which convention a feed uses and never warns about ambiguous dates (day ≤ 12) — the same input string yields a different real date depending on an unstated assumption.
- Only order_date changed vs baseline (11 rows) — exactly the ambiguous ones.
- Evidence: orders_cleaned_run18_semantic_dates.csv.

## Test method note (for README)
- Schedule supports daily frequency only → scheduled behaviour verified on the baseline (run 2; run 5 was a scheduled drift attempt but invalid because the drift file was not uploaded); other drift cases triggered manually from Canvas with the same pipeline + GCS destination. Record trigger honestly in run_log.

## Usability notes (for README feedback)
- GCS connection: permission error was clear and specific (`storage.objects.list`) — good.
- GCS connection refuses an empty bucket ("No files found") — awkward for a bucket meant as a destination.
- Connected S3 file browser: file rows aren't clickable; unclear how to add a file to the Canvas (had to attach via AI Builder `+`).
- Setup friction (not Rhombus): Google Cloud blocks service-account key creation by default (org policy `iam.disableServiceAccountKeyCreation`) — had to override.

## Not findings (checked & ruled out)
- Drop-column run showing old data (runs 5–6) — S3 still contained the original baseline (header had `status`); drift file hadn't been uploaded. Rhombus processed the correct file.
- S3 "Folder / path is empty" error — correct: file hadn't actually uploaded into `input/`.

## Credits
- AI Builder credits: 40/50 before cleaning prompt → 34/50 after cleaning + one download-help question → 29/50 after building the Canvas pipeline.
- Download help from chatbot was vague: pointed to "Artifacts / Files panel" and `rhombus_output/`; file was actually under Workspace → Download.

## Parts 6–7 results (2026-10-05)
- UI tests (Playwright): 5/5 pass in about 57s. Evidence: 15-ui-tests-all-pass.png
- API tests: 3/3 pass (1 positive, 2 negative). Evidence: 16-api-tests-pass.png
- API auth note: api.rhombusai.com rejects the web-session cookie (401) and needs a bearer token taken from rhombusai.com/api/auth/session.
- Usability (a11y): the selected destination in Data Output is shown only by colour (no radio or aria-selected), so screen readers and tests can't tell which one is selected.
- Usability: the Schedule card shows an empty "Next run:" while the schedule is active.
- Evidence index updated: 01–14 as in the folder, 15 = UI pass, 16 = API pass. The planned 15–17 captures were dropped; text excerpts T5–T6 cover them.
