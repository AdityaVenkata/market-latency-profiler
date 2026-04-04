"""
analyzer.py - Latency computation + rolling z-score spike detection
Usage: python analyzer.py
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def load_feed(path):
    df = pd.read_csv(path)
    df["arrival_ts"] = pd.to_numeric(df["arrival_ts"], errors="coerce")
    df = df.dropna(subset=["arrival_ts"]).reset_index(drop=True)
    df["arrival_dt"] = pd.to_datetime(df["arrival_ts"], unit="s", utc=True)
    return df


def compute_latency(df):
    df = df.copy().sort_values("arrival_ts").reset_index(drop=True)
    df["latency_ms"] = df["arrival_ts"].diff() * 1000
    df = df[df["latency_ms"] > 0].reset_index(drop=True)
    return df


def compute_percentiles(s):
    return {f"p{p}": np.percentile(s, p) for p in [50, 75, 90, 95, 99, 99.9]}


def detect_spikes(df, window=50, threshold=3.0):
    df = df.copy()
    roll = df["latency_ms"].rolling(window=window, min_periods=10)
    rolling_mean = roll.mean()
    rolling_std = roll.std().replace(0, np.nan)
    df["rolling_mean_ms"] = rolling_mean
    df["rolling_std_ms"] = rolling_std
    df["z_score"] = (df["latency_ms"] - rolling_mean) / rolling_std
    df["is_spike"] = df["z_score"].abs() > threshold
    return df


def label_phase(df, split_frac=0.5):
    df = df.copy()
    split_idx = int(len(df) * split_frac)
    df["phase"] = "after"
    df.loc[:split_idx, "phase"] = "before"
    return df


def full_analysis(path, window=50, threshold=3.0):
    df = load_feed(path)
    df = compute_latency(df)
    df = detect_spikes(df, window=window, threshold=threshold)
    df = label_phase(df)
    return df


def print_report(df):
    total = len(df)
    spikes = df["is_spike"].sum()
    print("\n" + "=" * 58)
    print("  MARKET LATENCY PROFILER — ANALYSIS REPORT")
    print("=" * 58)
    print(f"  Messages analyzed : {total:,}")
    print(f"  Anomalous spikes  : {spikes:,}  ({100*spikes/total:.2f}%)\n")

    for phase in ["before", "after", "all"]:
        subset = df if phase == "all" else df[df["phase"] == phase]
        if subset.empty:
            continue
        p = compute_percentiles(subset["latency_ms"])
        print(f"  ── {phase.upper().center(10)} ──────────────────────────────")
        print(f"  Samples : {len(subset):,}")
        print(f"  Mean    : {subset['latency_ms'].mean():.2f} ms   Std: {subset['latency_ms'].std():.2f} ms")
        print(f"  p50     : {p['p50']:.2f} ms")
        print(f"  p95     : {p['p95']:.2f} ms")
        print(f"  p99     : {p['p99']:.2f} ms\n")

    before = df[df["phase"] == "before"]["latency_ms"]
    after  = df[df["phase"] == "after"]["latency_ms"]
    if not before.empty and not after.empty:
        p95_b = np.percentile(before, 95)
        p95_a = np.percentile(after, 95)
        delta = 100 * (p95_b - p95_a) / p95_b
        direction = "improvement" if delta > 0 else "regression"
        print(f"  p95 {direction}: {abs(delta):.1f}%  ({p95_b:.2f} ms → {p95_a:.2f} ms)")
    print("=" * 58)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/raw_feed.csv")
    parser.add_argument("--window", type=int, default=50)
    parser.add_argument("--threshold", type=float, default=3.0)
    args = parser.parse_args()

    df = full_analysis(args.input, window=args.window, threshold=args.threshold)
    print_report(df)
    out = Path("data/analyzed.csv")
    df.to_csv(out, index=False)
    print(f"\n[analyzer] Saved → {out}")


if __name__ == "__main__":
    main()
