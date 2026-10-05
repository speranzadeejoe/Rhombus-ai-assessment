# Schema drift: `unit_price` number → text `"AUD 89.50"`

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| MEDIUM | 11 | No, it carried on | Not needed |

## What I changed
Every `unit_price` became text with a currency prefix, for example `89.50` → `AUD 89.50`. File: `datasets/schema_type_change.csv`.

## What I expected
Either the prices are parsed and the currency is kept or flagged, or a warning that the column type changed.

## What happened
The pipeline succeeded. **All 195 prices were parsed to the correct numbers**, because `clean_unit_price` strips every non-digit character. The **currency label was silently discarded.** Side effect: the 6 `$` prices that had been blank since run 3 came out correct, because the input no longer had `$`.

## What the logs said
Success only, with no mention of the type change.

## What the chatbot said, and whether the fix worked
Not used, because there was no error.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/schema_type_change.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- [13-type-change-logs.png](evidence/13-type-change-logs.png)
- Validation run11: `prices numeric+correct` PASS
- Full run history: [run_log.csv](run_log.csv)
