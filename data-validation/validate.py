#!/usr/bin/env python3
"""
Data validation for the Rhombus AI S3 -> GCS cleaning pipeline.

Compares each pipeline output (downloaded from GCS) with the input file that
produced it (the S3 source) and checks:

  1. Schema        - expected columns present / unexpected columns flagged
  2. Row counts    - output rows == unique order_ids in input
  3. Cleaning rules- dedupe, names, cities, dates, prices, quantity & email flags
  4. Determinism   - runs with identical input produce byte-identical output
  5. Semantic drift- price scale vs baseline, date-order ambiguity

Ground truth is computed independently from the raw input, so the checks do
not trust anything the pipeline (or its AI assistant) claims.

Usage:
    python data-validation/validate.py                 # run all cases in RUNS
    python data-validation/validate.py --case run17    # one case
    python data-validation/validate.py --input X.csv --output Y.csv   # ad hoc

Exit code is 1 if any check FAILs (useful in CI).
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets"
OUTPUTS = Path(__file__).resolve().parent / "outputs"

BASE_COLS = ["order_id", "customer_name", "email", "city", "order_date",
             "product", "quantity", "unit_price", "status"]
FLAG_COLS = ["quantity_flag", "email_flag"]
CITIES = {"Adelaide", "Sydney", "Melbourne", "Brisbane", "Perth"}
STATUSES = {"Pending", "Shipped", "Delivered", "Cancelled"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# case id -> (input file in /datasets, output file in /data-validation/outputs, description)
RUNS = {
    "run01": ("orders_baseline.csv", "run01_baseline_manual.csv", "Baseline, manual run (original pipeline)"),
    "run02": ("orders_baseline.csv", "run02_baseline_scheduled.csv", "Baseline, scheduled run (original pipeline)"),
    "run04": ("orders_baseline.csv", "run04_baseline_after_fix.csv", "Baseline after chatbot fixes"),
    "run16": ("orders_baseline.csv", "run16_baseline_restored.csv", "Baseline reference for drift tests"),
    "run07": ("schema_drop_column.csv", "run07_schema_drop_column.csv", "Schema: drop `status`"),
    "run10": ("schema_rename_column.csv", "run10_schema_rename_column.csv", "Schema: rename customer_name -> full_name"),
    "run11": ("schema_type_change.csv", "run11_schema_type_change.csv", "Schema: unit_price -> 'AUD 89.50' text"),
    "run12": ("schema_add_column.csv", "run12_schema_add_column.csv", "Schema: add `discount_code`"),
    "run17": ("semantic_dollars_to_cents.csv", "run17_semantic_dollars_to_cents.csv", "Semantic: dollars -> cents"),
    "run18": ("semantic_mmdd_dates.csv", "run18_semantic_mmdd_dates.csv", "Semantic: DD/MM -> MM/DD dates"),
}
BASELINE_CASE = "run16"
# Which convention each input file uses for slash dates (ground truth we control).
DATE_ORDER = {"semantic_mmdd_dates.csv": "MDY"}
# Which input files store prices in cents (ground truth we control).
PRICE_DIVISOR = {"semantic_dollars_to_cents.csv": 100}

CITY_MAP = {"syd": "Sydney", "melb": "Melbourne", "mel": "Melbourne", "bris": "Brisbane"}


# ---------------------------------------------------------------- helpers
def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:10]


def name_col(df):
    for c in ("customer_name", "full_name"):
        if c in df.columns:
            return c
    return None


def true_date(raw, order="DMY"):
    """Expected ISO date for a raw input string (None = invalid/blank)."""
    s = raw.strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        a, b, y = m.groups()
        d, mo = (a, b) if order == "DMY" else (b, a)
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def true_price(raw, divisor=1):
    s = re.sub(r"[^\d.]", "", raw)
    return round(float(s) / divisor, 2) if s else None


def true_city(raw):
    c = raw.strip()
    return CITY_MAP.get(c.lower(), c.title())


def to_num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Report:
    def __init__(self, case, desc):
        self.case, self.desc, self.rows = case, desc, []

    def add(self, check, ok, detail, level="FAIL"):
        status = "PASS" if ok else level
        self.rows.append({"case": self.case, "check": check, "status": status, "detail": detail})

    def print(self):
        print(f"\n=== {self.case}: {self.desc} ===")
        for r in self.rows:
            print(f"  [{r['status']:4}] {r['check']:<22} {r['detail']}")


# ---------------------------------------------------------------- checks
def key(x):
    return x.str.replace(r"[^0-9A-Za-z]", "", regex=True)


def validate(case, in_file, out_file, desc="", baseline_out=None):
    rep = Report(case, desc)
    src, out = read(in_file), read(out_file)
    fname = Path(in_file).name
    order = DATE_ORDER.get(fname, "DMY")
    divisor = PRICE_DIVISOR.get(fname, 1)

    # 1. Schema
    expected = [c if c != "customer_name" or "customer_name" in src.columns else "full_name" for c in BASE_COLS]
    expected = [c for c in expected if c in src.columns] + FLAG_COLS
    missing = [c for c in expected if c not in out.columns]
    extra = [c for c in out.columns if c not in expected]
    dropped_by_source = [c for c in BASE_COLS if c not in src.columns and c != "customer_name"]
    rep.add("schema: columns", not missing, f"missing={missing or 'none'}")
    if extra:
        rep.add("schema: new columns", False, f"passed through unreviewed: {extra}", "WARN")
    if dropped_by_source:
        rep.add("schema: source drift", False, f"columns absent from source: {dropped_by_source} (pipeline gave no warning)", "WARN")

    # 2. Row counts
    uniq = src["order_id"].nunique()
    rep.add("row count", len(out) == uniq, f"in={len(src)} unique={uniq} out={len(out)}")
    rep.add("dedupe: order_id", not out["order_id"].duplicated().any(),
            f"duplicate ids in output={out['order_id'].duplicated().sum()}")
    lost = set(key(src["order_id"])) - set(key(out["order_id"]))
    rep.add("ids preserved", not lost, f"lost ids={sorted(lost)[:5] or 'none'}")

    # Join on a normalised key so a corrupted id (e.g. hyphen stripped) can't hide other errors.
    s2 = src.drop_duplicates("order_id").assign(_k=lambda d: key(d["order_id"]))
    o2 = out.assign(_k=lambda d: key(d["order_id"]))
    m = s2.merge(o2, on="_k", suffixes=("_in", "_out")).rename(columns={"order_id_in": "order_id"})
    rep.add("rows matched to input", len(m) == uniq, f"matched={len(m)} of {uniq}")

    # 3. Cleaning rules
    nc = name_col(out)
    if nc:
        bad = out[out[nc] != out[nc].str.strip().str.title()]
        rep.add("names trimmed+title", bad.empty, f"bad={len(bad)} e.g. {bad[nc].head(2).tolist()}")
    if "city" in out.columns:
        bad = m[m["city_out"] != m["city_in"].map(true_city)]
        rep.add("cities standardised", bad.empty and set(out["city"]) <= CITIES, f"bad={len(bad)}")
    if "status" in out.columns and "status" in src.columns:
        bad = out[~out["status"].isin(STATUSES)]
        rep.add("status title case", bad.empty, f"bad={len(bad)}")

    # dates
    exp = m["order_date_in"].map(lambda s: true_date(s, order))
    got = m["order_date_out"].where(m["order_date_out"] != "INVALID_DATE", None)
    wrong = m[(exp.fillna("NONE") != got.fillna("NONE"))]
    swapped = wrong[wrong.apply(lambda r: true_date(r["order_date_in"], "MDY" if order == "DMY" else "DMY") == r["order_date_out"], axis=1)]
    rep.add("dates correct", wrong.empty,
            f"wrong={len(wrong)} (day/month swapped={len(swapped)}) e.g. {wrong[['order_id','order_date_in','order_date_out']].head(2).values.tolist()}")
    ambiguous = m["order_date_in"].str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}") & \
        m["order_date_in"].str.split("/").map(lambda p: len(p) == 3 and int(p[0]) <= 12 and int(p[1]) <= 12)
    if ambiguous.sum():
        rep.add("dates: ambiguous", False, f"{int(ambiguous.sum())} input dates valid as both DD/MM and MM/DD", "WARN")

    # prices
    exp_p = m["unit_price_in"].map(lambda v: true_price(v, divisor))
    got_p = m["unit_price_out"].map(to_num)
    both = exp_p.notna()
    wrong_p = m[both & ((got_p - exp_p).abs().fillna(1) > 0.01)]
    rep.add("prices numeric+correct", wrong_p.empty,
            f"wrong/blank={len(wrong_p)} of {int(both.sum())} e.g. {wrong_p[['order_id','unit_price_in','unit_price_out']].head(2).values.tolist()}")

    # quantity flags
    q = m["quantity_in"].str.strip()
    need_neg = q.str.match(r"^-\d+$")
    need_miss = (q == "") | ~q.str.match(r"^-?\d+$")
    ok_neg = (m.loc[need_neg, "quantity_flag"] == "NEGATIVE_QUANTITY").all()
    ok_miss = m.loc[need_miss, "quantity_flag"].isin(["MISSING_QUANTITY", "INVALID_QUANTITY"]).all()
    rep.add("quantity flags", ok_neg and ok_miss,
            f"negative={int(need_neg.sum())} flagged_ok={ok_neg}; missing/non-numeric={int(need_miss.sum())} flagged_ok={ok_miss}")

    # email flags + integrity
    e = m["email_in"].str.strip()
    exp_flag = e.map(lambda v: "MISSING_EMAIL" if not v else ("" if EMAIL_RE.match(v) else "INVALID_EMAIL"))
    bad = m[exp_flag != m["email_flag"]]
    rep.add("email flags", bad.empty, f"mismatched={len(bad)}")
    altered = m[(e != "") & (m["email_out"] != e)]
    rep.add("emails unaltered", altered.empty, f"altered={len(altered)} e.g. {altered['email_out'].head(2).tolist()}")
    altered_id = out[~out["order_id"].str.fullmatch(r"ORD-\d{4}")]
    rep.add("order_id format", altered_id.empty, f"bad={len(altered_id)}")

    # 5. Semantic drift vs baseline output
    if baseline_out is not None and Path(out_file).name != Path(baseline_out).name:
        b = read(baseline_out)
        bp = pd.to_numeric(b["unit_price"], errors="coerce").median()
        op = pd.to_numeric(out["unit_price"], errors="coerce").median()
        ratio = op / bp if bp else 1
        rep.add("semantic: price scale", 0.5 < ratio < 2,
                f"median price {op:g} vs baseline {bp:g} (x{ratio:.1f})" + (" -> likely cents/units change" if ratio >= 2 else ""))
        common = b.assign(_k=key(b["order_id"])).merge(out.assign(_k=key(out["order_id"])), on="_k", suffixes=("_b", "_o"))
        if "order_date_o" in common:
            moved = common[common["order_date_b"] != common["order_date_o"]]
            rep.add("semantic: dates moved", moved.empty,
                    f"{len(moved)} dates differ from baseline for same orders", "WARN")
    return rep


def determinism(pairs):
    rows = []
    for a, b in pairs:
        ha, hb = md5(OUTPUTS / RUNS[a][1]), md5(OUTPUTS / RUNS[b][1])
        rows.append({"case": f"{a} vs {b}", "check": "determinism", "status": "PASS" if ha == hb else "WARN",
                     "detail": f"md5 {ha} vs {hb} (same input)"})
    return rows


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", help="run a single case id from RUNS")
    ap.add_argument("--input", help="ad hoc input CSV")
    ap.add_argument("--output", help="ad hoc output CSV")
    ap.add_argument("--results", default=str(Path(__file__).resolve().parent / "validation_results.csv"))
    a = ap.parse_args()

    baseline_out = OUTPUTS / RUNS[BASELINE_CASE][1]
    all_rows = []
    if a.input and a.output:
        rep = validate("adhoc", a.input, a.output, "ad hoc", baseline_out)
        rep.print(); all_rows += rep.rows
    else:
        cases = [a.case] if a.case else list(RUNS)
        for c in cases:
            inp, outp, desc = RUNS[c]
            rep = validate(c, DATASETS / inp, OUTPUTS / outp, desc, baseline_out)
            rep.print(); all_rows += rep.rows
        if not a.case:
            # Only pairs where input AND pipeline version were identical.
            det = determinism([("run01", "run02")])
            print("\n=== Determinism (same input, separate runs) ===")
            for r in det:
                print(f"  [{r['status']:4}] {r['case']:<22} {r['detail']}")
            all_rows += det

    df = pd.DataFrame(all_rows)
    df.to_csv(a.results, index=False)
    summary = df.groupby("case")["status"].value_counts().unstack(fill_value=0)
    print("\n=== Summary ===")
    print(summary.to_string())
    print(f"\nResults written to {Path(a.results).relative_to(ROOT) if Path(a.results).is_relative_to(ROOT) else a.results}")
    sys.exit(1 if (df["status"] == "FAIL").any() else 0)


if __name__ == "__main__":
    main()
