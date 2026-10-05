# Schema drift: rename `customer_name` → `full_name`

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| HIGH | 8, 9, 10 | Yes | Partly: the 1st fix failed; the 3rd worked only after I gave it the cause, and it lost name trimming |

## What I changed
Renamed the `customer_name` header to `full_name`. The data is unchanged. File: `datasets/schema_rename_column.csv`.

## What I expected
Either the pipeline maps the renamed column, or it stops with an error that names the missing `customer_name`.

## What happened
**Run 8** stopped at `standardise_casing`. Nothing new reached GCS.

**Run 9**, after the chatbot's fix, failed with a new configuration error.

**Run 10**: I told the chatbot the real cause (the renamed column), and its 3rd fix ran. `full_name` was kept and title-cased, **but 13 names kept their leading and trailing spaces** (for example `'  Ethan Patel '`), so trimming was silently lost.

## What the logs said
The error is **misleading**, and the log **contradicts itself**:
```
11:45:27 PM  Pipeline execution started.
11:45:29 PM  Pipeline execution completed successfully.
11:45:29 PM  ✖ Pipeline failed at standardise_casing: No text columns to convert.
```
`status` is still a text column, and the message never mentions the missing `customer_name`. Run 9 logged `LLM transform requires a non-empty prompt when code is not provided`, again next to "completed successfully" (11:54:28).

## What the chatbot said, and whether the fix worked
**The diagnosis was wrong.** It blamed dtype or "mixed-type content from Athena/S3" and never mentioned the renamed column, which was the only change. Its fix turned the node into an LLM node that still referenced `customer_name`, and that node was empty, which caused run 9's error. Once I gave it the cause, the fix worked, but it introduced the trimming regression.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/schema_rename_column.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- [10-rename-column-logs.png](evidence/10-rename-column-logs.png)
- [11-rename-fix-failed-logs.png](evidence/11-rename-fix-failed-logs.png)
- [12-rename-fix2-logs.png](evidence/12-rename-fix2-logs.png)
- Chatbot reply (verbatim): T4 in [evidence_log_excerpts.md](evidence_log_excerpts.md)
- Validation run10: `names trimmed+title` FAIL (bad=13)
- Full run history: [run_log.csv](run_log.csv)
