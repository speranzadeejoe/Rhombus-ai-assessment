"""Render validation_results.csv as a case x check status grid (PNG)."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "validation_results.csv")
df = df[~df["case"].str.contains(" vs ")]
labels = {"run01": "Baseline – manual (original)", "run02": "Baseline – scheduled (original)",
          "run04": "Baseline – after chatbot fixes", "run16": "Baseline – drift reference",
          "run07": "Schema: drop column", "run10": "Schema: rename column",
          "run11": "Schema: type change", "run12": "Schema: add column",
          "run17": "Semantic: dollars → cents", "run18": "Semantic: DD/MM → MM/DD"}
cases = [c for c in labels if c in set(df["case"])]
checks = list(dict.fromkeys(df["check"]))
grid = df.pivot_table(index="case", columns="check", values="status", aggfunc="first").reindex(index=cases, columns=checks)

STYLE = {"PASS": ("#0ca30c", "✓"), "WARN": ("#fab219", "!"), "FAIL": ("#d03b3b", "✗")}
fig, ax = plt.subplots(figsize=(15, 6.2), dpi=160)
for i, c in enumerate(cases):
    for j, k in enumerate(checks):
        s = grid.loc[c, k]
        if pd.isna(s):
            ax.add_patch(Rectangle((j + .06, i + .06), .88, .88, facecolor="#f1f0ec", edgecolor="none"))
            ax.text(j + .5, i + .5, "–", ha="center", va="center", color="#8a8a86", fontsize=9)
            continue
        col, glyph = STYLE[s]
        ax.add_patch(Rectangle((j + .06, i + .06), .88, .88, facecolor=col, edgecolor="none"))
        ax.text(j + .5, i + .5, glyph, ha="center", va="center", color="white" if s != "WARN" else "#1a1a19",
                fontsize=11, fontweight="bold")
ax.set_xlim(0, len(checks)); ax.set_ylim(len(cases), 0)
ax.set_xticks([j + .5 for j in range(len(checks))]); ax.set_xticklabels(checks, rotation=40, ha="right", fontsize=8.5, color="#3d3d3a")
ax.set_yticks([i + .5 for i in range(len(cases))]); ax.set_yticklabels([labels[c] for c in cases], fontsize=9.5, color="#1a1a19")
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
counts = df["status"].value_counts()
ax.set_title("Data validation – GCS output vs S3 input, per check", loc="left", fontsize=13, color="#1a1a19", pad=26)
fig.text(0.125, 0.905, f"✓ PASS {counts.get('PASS',0)}    ! WARN {counts.get('WARN',0)}    ✗ FAIL {counts.get('FAIL',0)}    – not applicable",
         fontsize=9.5, color="#3d3d3a")
fig.tight_layout()
fig.savefig(HERE / "validation_results.png", facecolor="white")
print("saved", HERE / "validation_results.png")
