# Semantic drift: DD/MM → MM/DD dates

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| HIGH | 18 | No, it carried on | Not applicable |

## What I changed
Switched every slash date from Australian DD/MM/YYYY to US MM/DD/YYYY. The column and type are the same. File: `datasets/semantic_mmdd_dates.csv`.

## What I expected
A warning about ambiguous or changed date conventions. Dates should come out the same as the baseline.

## What happened
The pipeline succeeded. Output dates have **0 errors**, against **11 wrong** in the DD/MM baseline. The parser always assumes **month-first**, so it is right only when the feed happens to be MM/DD. The original DD/MM feed is the one that gets silently corrupted (finding F10). The 11 rows that changed against the baseline are exactly the ambiguous dates (day ≤ 12).

## What the logs said
Success only, both for this run and for the corrupted baseline.

## What the chatbot said, and whether the fix worked
Not used.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/semantic_mmdd_dates.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- Validation run18: `dates correct` PASS and `semantic: dates moved` WARN (11). Baseline run16: `dates correct` FAIL (11 swapped). **My validation caught it; Rhombus did not.**
- Output: `data-validation/outputs/run18_semantic_mmdd_dates.csv`
- Full run history: [run_log.csv](run_log.csv)
