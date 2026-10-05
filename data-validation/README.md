# Data validation

Compares each Rhombus pipeline output (from GCS) with the input that produced it (from S3).
Ground truth is recomputed from the raw input, so nothing the pipeline or chatbot reports is trusted.

## Run

```bash
pip install pandas
python data-validation/validate.py                 # all cases
python data-validation/validate.py --case run17    # one case
python data-validation/validate.py --input datasets/X.csv --output path/to/gcs_output.csv
```

In Google Colab: upload the repo folder, then `!python data-validation/validate.py`.

Exit code is `1` if any check fails. Results are also written to `validation_results.csv`
(one row per case × check; used by the dashboard). `sample_output.txt` is a saved run.

## Checks

| Check | What it verifies |
|---|---|
| schema: columns / new columns / source drift | expected columns present; new or missing source columns flagged |
| row count, dedupe, ids preserved, rows matched | 212 in → 200 unique out; no dup ids; ids unaltered |
| names, cities, status | trimmed + Title Case; cities mapped to 5 canonical names |
| dates correct / ambiguous | ISO output equals true date for the feed's convention; ambiguous dd≤12 inputs warned |
| prices numeric+correct | numeric, `$`/text stripped, value equals true value |
| quantity flags, email flags, emails unaltered, order_id format | flags raised where required; valid values not mangled |
| semantic: price scale | median price vs baseline output (catches dollars→cents) |
| semantic: dates moved | dates changed vs baseline for the same orders (catches DD/MM↔MM/DD) |
| determinism | byte-identical output for identical input + pipeline (run01 vs run02) |

## Cases

`outputs/runNN_*.csv` are the GCS outputs; inputs are in `/datasets/`. See the `RUNS` table in `validate.py`.
