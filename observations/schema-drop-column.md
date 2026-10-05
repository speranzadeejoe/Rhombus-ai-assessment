# Schema drift: drop column `status`

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| HIGH | 7 | No, it carried on | Not needed (no error was raised) |

## What I changed
Removed the `status` column. Every other column and all 212 rows are unchanged. File: `datasets/schema_drop_column.csv`.

## What I expected
The pipeline should stop, or at least warn, because `standardise_casing` is configured to title-case `status`.

## What happened
The pipeline reported **completed successfully**, with 0 warnings and 0 errors. The GCS output has 200 rows and **no `status` column**. All other values match the baseline, so the column vanished without anyone being told.

## What the logs said
Logs show only success, so they don't explain anything:
```
11:37:23 PM  Pipeline execution started.
11:37:29 PM  Pipeline execution completed successfully.
11:37:29 PM  Applied 8 transformations: Remove Duplicates ... | Text Cleanup ...
```
(Panel: 4 success · 0 warnings · 0 errors.)

## What the chatbot said, and whether the fix worked
There was no error to give it. The silent success is the problem.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/schema_drop_column.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- Log text: T3 in [evidence_log_excerpts.md](evidence_log_excerpts.md)
- Output: `data-validation/outputs/run07_schema_drop_column.csv`
- Validation: `schema: source drift` WARN (`status` absent, no warning from the pipeline)
- Full run history: [run_log.csv](run_log.csv)
