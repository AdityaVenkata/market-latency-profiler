"""
visualizer.py - Generates 4 charts from analyzed data
Usage: python visualizer.py
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

DARK="#1A1A2E"; ACCENT="#E84545"; BLUE="#4A90D9"; GREEN="#27AE60"
ORANGE="#E67E22"; GRID="#2E2E4E"; TEXT="#CCCCDD"; LIGHT_BG="#14142A"

plt.rcParams.update({
    "figure.facecolor": DARK, "axes.facecolor": LIGHT_BG,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT, "axes.titlecolor": TEXT,
    "xtick.color": TEXT, "ytick.color": TEXT, "grid.color": GRID,
    "grid.linestyle": "--", "grid.alpha": 0.5, "text.color": TEXT,
    "legend.facecolor": DARK, "legend.edgecolor": GRID, "legend.labelcolor": TEXT,
})


def _save(fig, path, name):
    out = path / name
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=DARK)
    print(f"[visualizer] Saved → {out}")
    plt.close(fig)


def plot_timeline(df, out):
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.suptitle("Inter-Message Latency Timeline", fontsize=14, fontweight="bold")
    x = np.arange(len(df))
    spikes = df[df["is_spike"]]
    ax.plot(x, df["latency_ms"], color=BLUE, linewidth=0.6, alpha=0.7, label="Latency (ms)")
    ax.plot(df.index[df["is_spike"]], spikes["latency_ms"], "o", color=ACCENT,
            markersize=4, label=f"Spike (z>3σ)  n={len(spikes):,}", zorder=5)
    ax.plot(x, df["rolling_mean_ms"], color=ORANGE, linewidth=1.2, alpha=0.9, label="Rolling mean")
    split = df[df["phase"] == "after"].index.min()
    if pd.notna(split):
        ax.axvline(split, color=TEXT, linewidth=1.2, linestyle=":", alpha=0.6)
        ax.text(split + len(df)*0.01, ax.get_ylim()[1]*0.92,
                "← before  |  after →", color=TEXT, fontsize=8, alpha=0.7)
    ax.set_xlabel("Message index"); ax.set_ylabel("Latency (ms)")
    ax.set_ylim(bottom=0); ax.legend(loc="upper right", fontsize=9); ax.grid(True)
    fig.tight_layout(); _save(fig, out, "01_latency_timeline.png")


def plot_histogram(df, out):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Latency Distribution (Log Scale)", fontsize=14, fontweight="bold")
    lat = df["latency_ms"].dropna()
    bins = np.logspace(np.log10(max(lat.min(), 0.01)), np.log10(lat.max()), 80)
    ax.hist(lat, bins=bins, color=BLUE, alpha=0.8, edgecolor=DARK, linewidth=0.3)
    for label, (p, color) in {"p50": (50, GREEN), "p95": (95, ORANGE), "p99": (99, ACCENT)}.items():
        val = np.percentile(lat, p)
        ax.axvline(val, color=color, linewidth=1.5, linestyle="--")
        ax.text(val*1.06, ax.get_ylim()[1]*0.8, f"{label}\n{val:.1f}ms", color=color, fontsize=8, va="top")
    ax.set_xscale("log"); ax.set_xlabel("Latency (ms, log scale)"); ax.set_ylabel("Message count")
    ax.grid(True, which="both"); ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    fig.tight_layout(); _save(fig, out, "02_latency_distribution.png")


def plot_rolling_p95(df, out, window=100):
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.suptitle(f"Rolling p95 Latency (window={window})", fontsize=14, fontweight="bold")
    rp95 = df["latency_ms"].rolling(window=window, min_periods=10).quantile(0.95)
    before = df["phase"] == "before"; after = df["phase"] == "after"
    ax.fill_between(df.index[before], rp95[before], alpha=0.3, color=BLUE)
    ax.fill_between(df.index[after],  rp95[after],  alpha=0.3, color=GREEN)
    ax.plot(df.index[before], rp95[before], color=BLUE,  linewidth=1.5, label="Before")
    ax.plot(df.index[after],  rp95[after],  color=GREEN, linewidth=1.5, label="After")
    split = df[df["phase"] == "after"].index.min()
    if pd.notna(split):
        ax.axvline(split, color=TEXT, linewidth=1.2, linestyle=":", alpha=0.6)
    ax.set_xlabel("Message index"); ax.set_ylabel("p95 Latency (ms)")
    ax.set_ylim(bottom=0); ax.legend(fontsize=10); ax.grid(True)
    fig.tight_layout(); _save(fig, out, "03_rolling_p95.png")


def plot_cdf_comparison(df, out):
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Before vs After — Latency CDF", fontsize=14, fontweight="bold")
    for phase, color, label in [("before", BLUE, "Before"), ("after", GREEN, "After")]:
        subset = df[df["phase"] == phase]["latency_ms"].dropna().sort_values()
        if subset.empty: continue
        cdf = np.arange(1, len(subset)+1) / len(subset)
        ax.plot(subset.values, cdf, color=color, linewidth=2, label=label)
        p95 = np.percentile(subset, 95)
        ax.axvline(p95, color=color, linewidth=1, linestyle="--", alpha=0.6)
        ax.text(p95*1.04, 0.65 if phase=="before" else 0.55,
                f"p95={p95:.1f}ms", color=color, fontsize=8)
    before_lat = df[df["phase"]=="before"]["latency_ms"].dropna()
    after_lat  = df[df["phase"]=="after"]["latency_ms"].dropna()
    if not before_lat.empty and not after_lat.empty:
        p95_b = np.percentile(before_lat, 95); p95_a = np.percentile(after_lat, 95)
        delta = 100*(p95_b - p95_a)/p95_b
        direction = "▼ improvement" if delta > 0 else "▲ regression"
        ax.text(0.98, 0.08, f"p95 {direction}: {abs(delta):.1f}%",
                transform=ax.transAxes, ha="right", fontsize=10,
                color=GREEN if delta > 0 else ACCENT,
                bbox=dict(facecolor=DARK, edgecolor=GRID, boxstyle="round,pad=0.4"))
    ax.set_xlabel("Latency (ms)"); ax.set_ylabel("Cumulative probability")
    ax.set_xlim(left=0); ax.legend(fontsize=11); ax.grid(True)
    fig.tight_layout(); _save(fig, out, "04_cdf_comparison.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/analyzed.csv")
    parser.add_argument("--output", type=str, default="outputs/")
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    print(f"[visualizer] Loaded {len(df):,} rows, generating 4 charts...\n")
    plot_timeline(df, out); plot_histogram(df, out)
    plot_rolling_p95(df, out); plot_cdf_comparison(df, out)
    print("\n[visualizer] All charts saved.")


if __name__ == "__main__":
    main()
