# Schema drift: all four changes combined

| Severity | Run(s) | Pipeline stopped? | Chatbot fix worked? |
|---|---|---|---|
| HIGH | 13, 14, 15 | Yes | No: 2 fixes, neither applied |

## What I changed
Dropped `status`, renamed `customer_name`, changed `unit_price` to text, and added `discount_code`, all at once. File: `datasets/schema_all_combined.csv`.

## What I expected
Given the earlier cases, the pipeline should drop `status` silently and handle the rest. The chatbot had also promised the node was "resilient to the upstream rename and any future equivalent change".

## What happened
**Run 13 stopped** with a KeyError on `status`. The run 10 fix had hard-coded `status`. Two chatbot fixes (runs 14 and 15) both failed with the identical error. Nothing new reached GCS. I stopped after 3 attempts.

## What the logs said
The error is specific but raw. It's a Python KeyError with the generated code dumped into the log, and it again sits next to "completed successfully":
```
12:15:54 AM  Pipeline execution started.
12:15:57 AM  Pipeline execution completed successfully.
12:15:57 AM  ✖ Pipeline failed at standardise_casing: LLM execution failed (code_sha=2fdb126297dd): 'status' --- Generated code --- import pandas as…
```

## What the chatbot said, and whether the fix worked
**The diagnosis was correct** (`status` accessed without a guard), **but the fixes never took effect.** The chatbot said its fix "changes the code_sha and forces the LLM runtime to regenerate fresh code". All three failures show the **same `code_sha=2fdb126297dd`** (12:15:57, 12:19:07, 12:21:34), so stale cached code ran every time while the chatbot reported success.

## Schedule afterwards
The daily schedule stayed **Active** and unchanged; Rhombus did not pause it, mark it unhealthy, or warn on the Schedule tab (confirmed by UI test 4 after all drift runs). Scheduled runs don't appear in Logs (F9), so a failed scheduled run would only be noticed by checking GCS. The next scheduled run simply processes whatever file is in S3.

## How to reproduce
1. Upload `datasets/schema_all_combined.csv` to `s3://speranza-rhombus-source/input/`, replacing the current source file (same file name). Check the header in S3 to confirm the replacement (runs 5–6 were invalid because I skipped this step).
2. In Rhombus, open project `S3-to-GCS-cleaning-pipeline` → Canvas → Run (▶). Open **Logs**.
3. Download `orders_cleaned.csv` from `gs://speranza-rhombus-output/` and save it into `data-validation/outputs/`.
4. Run `python data-validation/validate.py` and read the rows for this case.

## Evidence
- Log text and chatbot quote: T5–T6 in [evidence_log_excerpts.md](evidence_log_excerpts.md)
- [run_log.csv](run_log.csv) runs 13–15
- Full run history: [run_log.csv](run_log.csv)
