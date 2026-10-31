"""Build result tables and figures for the temperature experiments.

Usage: python -I make_figures.py <simulation-dir> <plot-style-dir>
Reads runs/*/output and results/run_summary.csv, results/energy_summary.csv, and writes to results/.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sim, style = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(style))
import plot_style as ps  # noqa: E402

ps.setup()
results = sim / "results"
summary = pd.read_csv(results / "run_summary.csv").set_index("case")
energy = pd.read_csv(results / "energy_summary.csv").set_index("case")
DTS = [-2, -1, 0, 1, 2]
TAG = {-2: "m2", -1: "m1", 1: "p1", 2: "p2"}
NOISE = ["t0_n1", "t0_n2", "t0_n3", "t0_n4"]
LABEL = {-2: "T–2", -1: "T–1", 0: "T0", 1: "T+1", 2: "T+2"}


def name(prefix, dt, sst):
    if dt == 0:
        return "er_t0" if prefix.startswith("er") else "t0"
    return f"{prefix}_{TAG[dt]}_{sst}"


def series(case):
    t = np.loadtxt(sim / "runs" / case / "output" / "time.out")
    step = np.median(np.diff(t[:, 0]))
    span = max(1, int(round(24 / step)))
    kernel = np.ones(span) / span
    return t[:, 0] / 24, np.convolve(t[:, 1], kernel, mode="same")


# Reference statistics from the base case and its perturbed repeats.
members = ["t0"] + NOISE
reference = summary.loc[members]
noise = {
    "v_mean": reference.v_mean_d8_15.mean(), "v_mean_sd": reference.v_mean_d8_15.std(),
    "v_peak": reference.v_peak_24h.mean(), "v_peak_sd": reference.v_peak_24h.std(),
    "vmaxth": reference.vmaxth.mean(), "p_mean": reference.p_mean_d8_15.mean(), "p_mean_sd": reference.p_mean_d8_15.std(),
}
pd.Series(noise).to_csv(results / "noise_reference.csv", header=["value"])


def change(case, column, base):
    return 100.0 * (summary.loc[case, column] / base - 1.0)


rows = []
for prefix, sst, design in (("ad", "sstfix", "습윤단열·RH 고정·SST 고정"), ("ad", "sstup", "습윤단열·RH 고정·SST 상승"), ("q", "sstfix", "습윤단열·비습 고정·SST 고정")):
    for dt in DTS:
        case = name(prefix, dt, sst)
        row = summary.loc[case]
        rows.append({
            "design": design, "dT": dt, "case": case, "v_mean": row.v_mean_d8_15, "v_peak": row.v_peak_24h, "p_mean": row.p_mean_d8_15, "vmaxth": row.vmaxth,
            "rmw": row.rmw_mean_d8_15, "t_33ms_day": row.t_33ms_day, "t_peak_day": row.t_peak_24h_day,
            "v_mean_change_pct": change(case, "v_mean_d8_15", noise["v_mean"]), "v_peak_change_pct": change(case, "v_peak_24h", noise["v_peak"]),
            "vmaxth_change_pct": change(case, "vmaxth", noise["vmaxth"]), "env_dt_200": row.env_dt_200, "env_dr_700": row.env_dr_700,
        })
table = pd.DataFrame(rows)
table.to_csv(results / "experiment_table.csv", index=False)

# Figure 1: time evolution in the two main sets.
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
for ax, sst, title in zip(axes, ("sstfix", "sstup"), ("SST 고정: 대기만 변화", "SST 상승: 대기와 바다가 함께 변화")):
    runs = [series(m) for m in members]
    grid = runs[0][0]
    band = np.array([r[1][: len(grid)] for r in runs])
    inside = (grid >= 0.5) & (grid <= 14.5)
    ax.fill_between(grid[inside], band.min(axis=0)[inside], band.max(axis=0)[inside], color=ps.NEUTRAL, alpha=0.18, linewidth=0, label="T0 반복 범위")
    for dt in DTS:
        day, wind = series(name("ad", dt, sst))
        valid = (day >= 0.5) & (day <= 14.5)
        ax.plot(day[valid], wind[valid], color=ps.DT_COLORS[dt], label=LABEL[dt], linewidth=1.8 if dt else 1.4)
    ax.axvspan(8, 15, color=ps.GRID, alpha=0.35, linewidth=0, zorder=0)
    ax.set_title(title)
    ax.set_xlabel("모의 시간 (일)")
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 130)
axes[0].set_ylabel("최대 접선풍 (m/s, 24시간 이동평균)")
axes[0].legend(loc="lower right", ncols=2)
ps.save(fig, str(results / "sim_01_time_evolution"))

# Figure 2: response of simulated intensity and potential intensity.
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
band = 200.0 * noise["v_mean_sd"] / noise["v_mean"]
for ax, sst, title in zip(axes, ("sstfix", "sstup"), ("SST 고정", "SST 상승")):
    design = "습윤단열·RH 고정·SST 고정" if sst == "sstfix" else "습윤단열·RH 고정·SST 상승"
    sub = table[table.design == design].sort_values("dT")
    ax.axhspan(-band, band, color=ps.NEUTRAL, alpha=0.18, linewidth=0, label="T0 반복 ±2σ")
    ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
    for column, label, color, marker in (("vmaxth_change_pct", "이론 PI (VMAXTH)", ps.BLUE, "s"), ("v_mean_change_pct", "모의 강도 (8–15일 평균)", ps.ORANGE, "o"), ("v_peak_change_pct", "모의 강도 (최고 24시간)", ps.AQUA, "^")):
        ax.plot(sub.dT, sub[column], color=color, marker=marker, markersize=6, markeredgecolor=ps.SURFACE, markeredgewidth=1, label=label)
    ax.set_title(title)
    ax.set_xticks(DTS, [LABEL[d] for d in DTS])
    ax.set_xlabel("대기 온도 조건")
axes[0].set_ylabel("T0 대비 변화 (%)")
axes[1].legend(loc="upper left")
ps.save(fig, str(results / "sim_02_response"))

# Figure 3: humidity control and vertical structure.
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
ax = axes[0]
for prefix, label, color in (("ad", "상대습도 고정", ps.ORANGE), ("q", "비습 고정", ps.BLUE)):
    values = [change(name(prefix, dt, "sstfix"), "v_mean_d8_15", noise["v_mean"]) for dt in DTS]
    ax.plot(DTS, values, color=color, marker="o", markersize=6, markeredgecolor=ps.SURFACE, label=label)
ax.axhspan(-band, band, color=ps.NEUTRAL, alpha=0.18, linewidth=0)
ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
ax.set_xticks(DTS, [LABEL[d] for d in DTS])
ax.set_title("습도 처리에 따른 모의 강도 (SST 고정)")
ax.set_xlabel("대기 온도 조건")
ax.set_ylabel("T0 대비 변화 (%)")
ax.legend(loc="lower left")
ax = axes[1]
for prefix, label, color in (("ad", "습윤단열 편차", ps.ORANGE), ("un", "균일 이동", ps.BLUE)):
    for sst, style_name, suffix in (("sstfix", "-", "SST 고정"), ("sstup", "--", "SST 상승")):
        dts = [-2, 0, 2]
        values = [change(name(prefix, dt, sst), "v_mean_d8_15", noise["v_mean"]) for dt in dts]
        ax.plot(dts, values, color=color, linestyle=style_name, marker="o", markersize=6, markeredgecolor=ps.SURFACE, label=f"{label}, {suffix}")
ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
ax.set_xticks([-2, 0, 2], [LABEL[d] for d in (-2, 0, 2)])
ax.set_title("연직 구조에 따른 모의 강도")
ax.set_xlabel("대기 온도 조건")
ax.legend(loc="lower right", fontsize=8)
ps.save(fig, str(results / "sim_03_humidity_shape"))

# Figure 4: mechanism.
fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
initial = pd.read_csv(results / "initial_disequilibrium.csv").set_index("case")
energy = energy.join(initial[["init_dk_kj"]])
panels = (("init_dk_kj", "초기 환경의 엔탈피 차 (kJ/kg)"), ("core_dk_kj", "성숙기 눈벽의 엔탈피 차 (kJ/kg)"), ("efficiency", "성숙기 열효율 (Ts–To)/To"))
for ax, (column, label) in zip(axes, panels):
    for sst, title, color in (("sstfix", "SST 고정", ps.ORANGE), ("sstup", "SST 상승", ps.BLUE)):
        values = [energy.loc[members, column].mean() if dt == 0 else energy.loc[name("ad", dt, sst), column] for dt in DTS]
        ax.plot(DTS, values, color=color, marker="o", markersize=6, markeredgecolor=ps.SURFACE, label=title)
    ax.errorbar([0], [energy.loc[members, column].mean()], yerr=[2 * energy.loc[members, column].std()], color=ps.INK2, capsize=3, linewidth=1, zorder=1, label="T0 반복 ±2σ")
    ax.set_xticks(DTS, [LABEL[d] for d in DTS])
    ax.set_title(label, fontsize=10)
axes[0].legend(loc="best")
ps.save(fig, str(results / "sim_04_energy"))

# Figure 5: storm structure, mean of the day 8, 10 and 12 output.
cases = [("ad_m2_sstfix", "T–2, SST 고정"), ("t0", "T0"), ("ad_p2_sstfix", "T+2, SST 고정"), ("ad_p2_sstup", "T+2, SST 상승")]
fig, axes = plt.subplots(1, 4, figsize=(12, 3.5), sharey=True, sharex=True)
for ax, (case, title) in zip(axes, cases):
    output = sim / "runs" / case / "output"
    r = np.loadtxt(output / "rgraph.out").ravel()
    z = np.loadtxt(output / "zgraph.out").ravel()
    wind = np.mean([np.loadtxt(output / f"vcon{n}.out") for n in ("04", "05", "06")], axis=0)
    nz = min(len(z), wind.shape[0])
    nr = min(len(r), wind.shape[1])
    mesh = ax.contourf(r[:nr], z[:nz], wind[:nz, :nr], levels=np.arange(-10, 121, 10), cmap="Blues", extend="both")
    ax.contour(r[:nr], z[:nz], wind[:nz, :nr], levels=[0], colors=ps.INK2, linewidths=0.7)
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 20)
    ax.set_title(title)
    ax.set_xlabel("반경 (km)")
    ax.grid(False)
axes[0].set_ylabel("고도 (km)")
fig.colorbar(mesh, ax=axes, label="접선풍 (m/s)", pad=0.01, fraction=0.025)
ps.save(fig, str(results / "sim_05_structure"))

# Figure 6: which environmental quantity explains simulated intensity.
mechanism = pd.read_csv(results / "mechanism_test.csv").set_index("case")
groups = (("ad_", "sstfix", "상대습도 고정, SST 고정", ps.ORANGE, "o"), ("ad_", "sstup", "상대습도 고정, SST 상승", ps.BLUE, "s"), ("q_", "sstfix", "비습 고정, SST 고정", ps.AQUA, "^"))
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, column, xlabel in zip(axes, ("init_dk", "cape_sat"), ("초기 환경의 해면–대기 엔탈피 차 (kJ/kg)", "해수면 포화 공기의 CAPE (J/kg)")):
    for prefix, suffix, label, color, marker in groups:
        sub = mechanism[mechanism.index.str.startswith(prefix) & mechanism.index.str.endswith(suffix)]
        ax.scatter(sub[column], sub.v_peak, s=62, color=color, marker=marker, edgecolor=ps.SURFACE, linewidth=1, label=label, zorder=3)
    ax.scatter([mechanism.loc["t0", column]], [mechanism.loc["t0", "v_peak"]], s=80, color=ps.INK, marker="D", edgecolor=ps.SURFACE, linewidth=1, label="T0", zorder=4)
    fit = np.polyfit(mechanism[column], mechanism.v_peak, 1)
    xs = np.array([mechanism[column].min(), mechanism[column].max()])
    ax.plot(xs, np.polyval(fit, xs), color=ps.NEUTRAL, linewidth=1, zorder=2)
    r2 = np.corrcoef(mechanism[column], mechanism.v_peak)[0, 1] ** 2
    ax.set_title(f"결정계수 r² = {r2:.2f} (실험 {len(mechanism)}개)")
    ax.set_xlabel(xlabel)
axes[0].set_ylabel("최고 모의 강도 (m/s, 24시간 평균)")
axes[1].legend(loc="lower right")
ps.save(fig, str(results / "sim_06_mechanism"))

print(table.drop(columns=["case", "t_peak_day"]).round(2).to_string(index=False))
print(noise)
