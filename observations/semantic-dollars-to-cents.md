# Semantic drift: dollars → cents

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| HIGH | 17 | No, it carried on | Not applicable (Rhombus didn't notice) |

## What I changed
Every `unit_price` was multiplied by 100 (349.00 → 34900). The structure is identical. File: `datasets/semantic_dollars_to_cents.csv`.

## What I expected
A warning about a large shift in the value distribution. Without one, my validation should catch it.

## What happened
The pipeline succeeded. **Every output price is 100× the baseline**: the laptop goes from $1,299 to $129,900. `unit_price` is the only column that differs. Revenue would be inflated 100× downstream.

## What the logs said
Success only. No flag on the prices.

## What the chatbot said, and whether the fix worked
Not used, because Rhombus gave no signal that anything was wrong.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/semantic_dollars_to_cents.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- Validation run17: `semantic: price scale` **FAIL** (median 8950 vs baseline 89.5, ×100). **My validation caught it; Rhombus did not.**
- Output: `data-validation/outputs/run17_semantic_dollars_to_cents.csv`
- Full run history: [run_log.csv](run_log.csv)
