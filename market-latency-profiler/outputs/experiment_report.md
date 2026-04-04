# Market Latency Profiler — Experiment Report

## Latency Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Mean   | 51.43 ms | 51.56 ms | 0.2% regression |
| p50    | 46.86 ms | 48.90 ms | — |
| p95    | 66.70 ms | 58.20 ms | 12.7% improvement |
| p99    | 794.95 ms | 753.75 ms | 5.2% improvement |
| Spikes | 2.86% | 2.69% | 6.0% improvement |

## Statistical Significance
- Mann-Whitney U: `625528`
- p-value: `0.010656`
- Significant at α=0.05: **Yes (p = 0.0107)**

## Key Findings

- p95 latency **decreased by 12.7%** (66.70 ms → 58.20 ms).
- Tail latency (p99) **decreased by 5.2%**.
- Result is **statistically significant**.

---
*github.com/AdityaVenkata/market-latency-profiler*