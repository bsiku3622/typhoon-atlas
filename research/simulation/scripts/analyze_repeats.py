"""Measure noise condition by condition and decide which changes can be told apart from it.

Usage: python -I analyze_repeats.py <simulation-dir> <plot-style-dir>
Every repeated condition has five members: the original run and four with tiny boundary-layer offsets.
A change is "distinguishable" when the Welch 95% confidence interval of the difference from T0 excludes
zero. This measures internal variability only, not model or physics uncertainty.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sim, style = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(sim / "scripts"))
sys.path.insert(0, str(style))
import plot_style as ps  # noqa: E402

ps.setup()
results = sim / "results"
METRICS = {"v_mean_d8_15": "v_mean", "v_peak_24h": "v_peak", "p_mean_d8_15": "p_mean", "t_33ms_day": "t_33", "rmw_mean_d8_15": "rmw"}
CONDITIONS = {
    "t0": ("T0", 0, "기준"),
    "ad_m2_sstup": ("SST 상승", -2, "상대습도 고정"), "ad_m1_sstup": ("SST 상승", -1, "상대습도 고정"),
    "ad_p1_sstup": ("SST 상승", 1, "상대습도 고정"), "ad_p2_sstup": ("SST 상승", 2, "상대습도 고정"),
    "ad_p1_sstfix": ("SST 고정", 1, "상대습도 고정"), "ad_p2_sstfix": ("SST 고정", 2, "상대습도 고정"),
    "q_p1_sstfix": ("SST 고정", 1, "비습 고정"), "q_p2_sstfix": ("SST 고정", 2, "비습 고정"),
}
run = pd.read_csv(results / "run_summary_all.csv").set_index("case")


def members(case):
    return [case] + [f"{case}_n{i}" for i in range(1, 5)]


def welch(a, b):
    a, b = np.asarray(a), np.asarray(b)
    se2a, se2b = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(se2a + se2b)
    dof = (se2a + se2b) ** 2 / (se2a ** 2 / (len(a) - 1) + se2b ** 2 / (len(b) - 1)) if se > 0 else np.nan
    margin = stats.t.ppf(0.975, dof) * se
    return a.mean() - b.mean(), margin


rows = []
base = {col: run.loc[members("t0"), col].values for col in METRICS}
for case, (sst, dt, humidity) in CONDITIONS.items():
    frame = run.loc[members(case)]
    row = {"case": case, "sst": sst, "dT": dt, "humidity": humidity, "n": len(frame), "vmaxth": frame.vmaxth.mean()}
    for col, short in METRICS.items():
        values = frame[col].values
        row[f"{short}_mean"] = values.mean()
        row[f"{short}_sd"] = values.std(ddof=1)
        if case != "t0":
            diff, margin = welch(values, base[col])
            row[f"{short}_diff"] = diff
            row[f"{short}_ci"] = margin
            row[f"{short}_pct"] = 100 * diff / base[col].mean()
            row[f"{short}_pct_ci"] = 100 * margin / base[col].mean()
            row[f"{short}_distinct"] = abs(diff) > margin
    rows.append(row)
table = pd.DataFrame(rows)
table.to_csv(results / "repeat_statistics.csv", index=False)

# Humidity treatment: relative humidity minus specific humidity, condition by condition.
humidity_rows = []
for dt, a, b in ((1, "ad_p1_sstfix", "q_p1_sstfix"), (2, "ad_p2_sstfix", "q_p2_sstfix")):
    for col, short in METRICS.items():
        diff, margin = welch(run.loc[members(a), col].values, run.loc[members(b), col].values)
        humidity_rows.append({"dT": dt, "metric": short, "rh_minus_q": diff, "ci": margin, "distinct": abs(diff) > margin})
humidity = pd.DataFrame(humidity_rows)
humidity.to_csv(results / "repeat_humidity_comparison.csv", index=False)

# Sensitivity of the warming-like set from all members, with a confidence interval on the slope.
slope_rows = []
for col, short in METRICS.items():
    x, y = [], []
    for case, dt in (("ad_m2_sstup", -2), ("ad_m1_sstup", -1), ("t0", 0), ("ad_p1_sstup", 1), ("ad_p2_sstup", 2)):
        for value in run.loc[members(case), col].values:
            x.append(dt)
            y.append(value)
    fit = stats.linregress(x, y)
    margin = stats.t.ppf(0.975, len(x) - 2) * fit.stderr
    slope_rows.append({"metric": short, "slope_per_k": fit.slope, "ci": margin, "pct_per_k": 100 * fit.slope / base[col].mean(), "pct_ci": 100 * margin / base[col].mean(), "n": len(x)})
slopes = pd.DataFrame(slope_rows)
slopes.to_csv(results / "repeat_slopes.csv", index=False)

# Figure: the warming-like set first, then the sensitivity experiment.
single = pd.read_csv(results / "run_summary.csv").set_index("case")
ref_v, ref_p, ref_pi = base["v_mean_d8_15"].mean(), base["v_peak_24h"].mean(), table[table.case == "t0"].vmaxth.iloc[0]
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
order = (("SST 상승", "바다와 대기가 함께 변화 (온난화에 가까운 조건)"), ("SST 고정", "대기만 변화 (원인을 나눈 민감도 실험)"))
for ax, (sst, title) in zip(axes, order):
    sub = table[(table.sst == sst) & (table.humidity == "상대습도 고정")].sort_values("dT")
    xs = [0] + list(sub.dT)
    ys = [0.0] + list(sub.v_mean_pct)
    es = [100 * 2 * base["v_mean_d8_15"].std(ddof=1) / np.sqrt(5) / ref_v] + list(sub.v_mean_pct_ci)
    pi = [0.0] + list(100 * (sub.vmaxth / ref_pi - 1))
    peak = [0.0] + list(sub.v_peak_pct)
    if sst == "SST 고정":
        for dt, case in ((-2, "ad_m2_sstfix"), (-1, "ad_m1_sstfix")):
            ax.scatter([dt], [100 * (single.loc[case, "v_peak_24h"] / ref_p - 1)], s=60, facecolor="none", edgecolor=ps.AQUA, linewidth=1.4, zorder=3)
            ax.scatter([dt], [100 * (single.loc[case, "vmaxth"] / ref_pi - 1)], s=60, facecolor="none", edgecolor=ps.BLUE, marker="s", linewidth=1.4, zorder=3)
    arrangement = np.argsort(xs)
    xs, ys, es, pi, peak = (np.array(v)[arrangement] for v in (xs, ys, es, pi, peak))
    ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
    ax.plot(xs, pi, color=ps.BLUE, marker="s", markersize=6, markeredgecolor=ps.SURFACE, label="이론 PI (모델 내장)")
    ax.plot(xs, peak, color=ps.AQUA, marker="^", markersize=6, markeredgecolor=ps.SURFACE, label="모의 강도 (최고 24시간)")
    ax.errorbar(xs, ys, yerr=es, color=ps.ORANGE, marker="o", markersize=6, markeredgecolor=ps.SURFACE, capsize=4, label="모의 강도 (8–15일 평균, 95% 구간)")
    ax.set_title(title, fontsize=10.5)
    ax.set_xticks([-2, -1, 0, 1, 2], ["–2 K", "–1 K", "기준", "+1 K", "+2 K"])
    ax.set_xlabel("온도 편차")
axes[0].set_ylabel("기준 대비 변화 (%)")
axes[0].legend(loc="upper left", fontsize=8.5)
ps.save(fig, str(results / "sim_02_response"))

pd.set_option("display.width", 240, "display.max_columns", 40, "display.float_format", lambda v: f"{v:.2f}")
print(table[["case", "n", "vmaxth", "v_mean_mean", "v_mean_sd", "v_mean_pct", "v_mean_pct_ci", "v_mean_distinct", "v_peak_mean", "v_peak_sd", "v_peak_pct", "v_peak_distinct", "p_mean_mean", "p_mean_sd", "t_33_mean", "rmw_mean"]].to_string(index=False))
print(humidity.round(2).to_string(index=False))
print(slopes.round(3).to_string(index=False))
