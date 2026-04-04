"""
experiment.py - Before/after statistical experiment report
Usage: python experiment.py
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def run_experiment(df):
    before = df[df["phase"] == "before"]["latency_ms"].dropna()
    after  = df[df["phase"] == "after"]["latency_ms"].dropna()

    def pcts(s):
        return {p: np.percentile(s, p) for p in [50, 75, 90, 95, 99, 99.9]}

    u_stat, p_value = stats.mannwhitneyu(before, after, alternative="two-sided")

    def delta(b, a):
        return 100 * (b - a) / b if b else 0

    b_pcts = pcts(before); a_pcts = pcts(after)
    return {
        "before": {"n": len(before), "mean": before.mean(), "std": before.std(),
                   "pcts": b_pcts, "spike_rate": df[df["phase"]=="before"]["is_spike"].mean()*100},
        "after":  {"n": len(after),  "mean": after.mean(),  "std": after.std(),
                   "pcts": a_pcts, "spike_rate": df[df["phase"]=="after"]["is_spike"].mean()*100},
        "delta_p95_pct":        delta(b_pcts[95], a_pcts[95]),
        "delta_p99_pct":        delta(b_pcts[99], a_pcts[99]),
        "delta_mean_pct":       delta(before.mean(), after.mean()),
        "delta_spike_rate_pct": delta(df[df["phase"]=="before"]["is_spike"].mean(),
                                      df[df["phase"]=="after"]["is_spike"].mean()),
        "u_stat": u_stat, "p_value": p_value,
        "statistically_significant": p_value < 0.05,
    }


def render_report(r):
    b, a = r["before"], r["after"]
    sig = f"Yes (p = {r['p_value']:.4f})" if r["statistically_significant"] else f"No (p = {r['p_value']:.4f})"

    def fmt(val):
        return f"{abs(val):.1f}% {'improvement' if val > 0 else 'regression'}"

    lines = [
        "# Market Latency Profiler — Experiment Report", "",
        "## Latency Comparison", "",
        "| Metric | Before | After | Change |",
        "|--------|--------|-------|--------|",
        f"| Mean   | {b['mean']:.2f} ms | {a['mean']:.2f} ms | {fmt(r['delta_mean_pct'])} |",
        f"| p50    | {b['pcts'][50]:.2f} ms | {a['pcts'][50]:.2f} ms | — |",
        f"| p95    | {b['pcts'][95]:.2f} ms | {a['pcts'][95]:.2f} ms | {fmt(r['delta_p95_pct'])} |",
        f"| p99    | {b['pcts'][99]:.2f} ms | {a['pcts'][99]:.2f} ms | {fmt(r['delta_p99_pct'])} |",
        f"| Spikes | {b['spike_rate']:.2f}% | {a['spike_rate']:.2f}% | {fmt(r['delta_spike_rate_pct'])} |",
        "", "## Statistical Significance",
        f"- Mann-Whitney U: `{r['u_stat']:.0f}`",
        f"- p-value: `{r['p_value']:.6f}`",
        f"- Significant at α=0.05: **{sig}**", "",
        "## Key Findings", "",
    ]

    if abs(r["delta_p95_pct"]) > 1:
        d = "decreased" if r["delta_p95_pct"] > 0 else "increased"
        lines.append(f"- p95 latency **{d} by {abs(r['delta_p95_pct']):.1f}%** ({b['pcts'][95]:.2f} ms → {a['pcts'][95]:.2f} ms).")
    if abs(r["delta_p99_pct"]) > 1:
        d = "decreased" if r["delta_p99_pct"] > 0 else "increased"
        lines.append(f"- Tail latency (p99) **{d} by {abs(r['delta_p99_pct']):.1f}%**.")
    lines.append(f"- Result is **{'statistically significant' if r['statistically_significant'] else 'NOT statistically significant'}**.")
    lines += ["", "---", "*github.com/AdityaVenkata/market-latency-profiler*"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  type=str, default="data/analyzed.csv")
    parser.add_argument("--output", type=str, default="outputs/experiment_report.md")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    result = run_experiment(df)
    report = render_report(result)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report)
    print(f"\n[experiment] Saved → {out}")


if __name__ == "__main__":
    main()
