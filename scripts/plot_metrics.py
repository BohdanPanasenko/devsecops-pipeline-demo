#!/usr/bin/env python3

import csv
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

STAGES = [
    ("lint_test_sec", "Lint & Test"),
    ("terraform_sec", "Terraform"),
    ("gitleaks_sec", "Gitleaks"),
    ("codeql_sec", "CodeQL"),
    ("trivy_sec", "Trivy"),
    ("checkov_sec", "Checkov"),
    ("zap_sec", "ZAP"),
]

INK, MUTED, GRID = "#22252a", "#6b7280", "#e5e7eb"
C_DURATION = "#0072B2"   
C_VULN = "#D55E00"       
C_FIXED = "#009E73"     

def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_axisbelow(True)


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "metrics.csv"
    out = sys.argv[2] if len(sys.argv) > 2 else "metrics.png"

    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    if not rows:
        raise SystemExit("metrics.csv has no data rows")
    n = len(rows)

    avg = [sum(int(r[key]) for r in rows) / n for key, _ in STAGES]
    labels = [lab for _, lab in STAGES]

    vuln = max(rows, key=lambda r: int(r["findings_total"]))
    fixed = min(rows, key=lambda r: int(r["findings_total"]))
    sev_keys, sev_labels = ["high", "medium", "low"], ["High", "Medium", "Low"]
    vuln_v = [int(vuln[s]) for s in sev_keys]
    fixed_v = [int(fixed[s]) for s in sev_keys]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))

    order = sorted(range(len(avg)), key=lambda i: avg[i])
    y = [labels[i] for i in order]
    x = [avg[i] for i in order]
    bars = ax1.barh(y, x, color=C_DURATION, height=0.62)
    pad = max(x) * 0.012
    for b, val in zip(bars, x):
        ax1.text(b.get_width() + pad, b.get_y() + b.get_height() / 2,
                 f"{val:.0f}s", va="center", color=INK, fontsize=9)
    ax1.set_title("Where the pipeline spends time\n(avg duration per stage)",
                  color=INK, fontsize=11, loc="left")
    ax1.set_xlabel("seconds", color=MUTED, fontsize=9)
    ax1.set_xlim(0, max(x) * 1.15)
    ax1.grid(axis="x", color=GRID, linewidth=0.8)
    _style(ax1)

    pos = list(range(len(sev_labels)))
    w = 0.38
    b1 = ax2.bar([p - w / 2 for p in pos], vuln_v, w,
                 label=f"Vulnerable ({vuln['findings_total']} total)", color=C_VULN)
    b2 = ax2.bar([p + w / 2 for p in pos], fixed_v, w,
                 label=f"Remediated ({fixed['findings_total']} total)", color=C_FIXED)
    for bars_ in (b1, b2):
        for b in bars_:
            ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.4,
                     str(int(b.get_height())), ha="center", color=INK, fontsize=9)
    ax2.set_xticks(pos)
    ax2.set_xticklabels(sev_labels)
    ax2.set_ylabel("open findings", color=MUTED, fontsize=9)
    ax2.set_ylim(0, max(vuln_v + fixed_v) * 1.4)
    ax2.set_title("Findings by severity\n(before vs after remediation)",
                  color=INK, fontsize=11, loc="left")
    ax2.grid(axis="y", color=GRID, linewidth=0.8)
    ax2.legend(frameon=False, fontsize=9, loc="upper right")
    _style(ax2)

    fig.suptitle("DevSecOps pipeline — speed vs. security", color=INK,
                 fontsize=13, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Wrote {out} ({n} run(s); vulnerable={vuln['findings_total']}, "
          f"remediated={fixed['findings_total']} findings)")


if __name__ == "__main__":
    main()
