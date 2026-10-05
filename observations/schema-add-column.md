# Schema drift: add column `discount_code`

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| LOW | 12 | No, it carried on | Not needed |

## What I changed
Added a new `discount_code` column. File: `datasets/schema_add_column.csv`.

## What I expected
The new column passes through, ideally with a notice that the schema changed.

## What happened
The pipeline succeeded. `discount_code` passed through **unchanged, in its original position**. All other columns match the previous run. This case was handled cleanly.

## What the logs said
Success only. Nothing says the schema grew, so a new (possibly sensitive) column reaches GCS unreviewed.

## What the chatbot said, and whether the fix worked
Not used.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/schema_add_column.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- [14-add-column-logs.png](evidence/14-add-column-logs.png)
- Validation run12: `schema: new columns` WARN
- Full run history: [run_log.csv](run_log.csv)
