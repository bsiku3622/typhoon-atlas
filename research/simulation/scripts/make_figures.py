"""Build result tables and figures for the temperature experiments.

Usage: python -I make_figures.py <simulation-dir> <plot-style-dir>
Reads runs/*/output and the summary tables in results/, and writes to results/. Run analyze_repeats.py first:
it draws sim_02 and writes repeat_statistics.csv, which supplies the error bars here.
Repeated conditions show the mean of their five members; the other conditions show their single run.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sim, style = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(style))
sys.path.insert(0, str(sim / "scripts"))
import plot_style as ps  # noqa: E402
from members import load_energy, load_runs, members  # noqa: E402

ps.setup()
results = sim / "results"
summary = load_runs(results)
energy = load_energy(results)
repeat = pd.read_csv(results / "repeat_statistics.csv").set_index("case")
DTS = [-2, -1, 0, 1, 2]
TAG = {-2: "m2", -1: "m1", 1: "p1", 2: "p2"}
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
reference = summary.loc[members("t0")]
noise = {
    "v_mean": reference.v_mean_d8_15.mean(), "v_mean_sd": reference.v_mean_d8_15.std(),
    "v_peak": reference.v_peak_24h.mean(), "v_peak_sd": reference.v_peak_24h.std(),
    "vmaxth": reference.vmaxth.mean(), "p_mean": reference.p_mean_d8_15.mean(), "p_mean_sd": reference.p_mean_d8_15.std(),
}
pd.Series(noise).to_csv(results / "noise_reference.csv", header=["value"])


def mean_of(case, column):
    return summary.loc[members(case), column].mean()


def change(case, column, base):
    return 100.0 * (mean_of(case, column) / base - 1.0)


rows = []
for prefix, sst, design in (("ad", "sstfix", "습윤단열·RH 고정·SST 고정"), ("ad", "sstup", "습윤단열·RH 고정·SST 상승"), ("q", "sstfix", "습윤단열·비습 고정·SST 고정")):
    for dt in DTS:
        case = name(prefix, dt, sst)
        row = summary.loc[members(case)].mean(numeric_only=True)
        rows.append({
            "design": design, "dT": dt, "case": case, "n": len(members(case)), "v_mean": row.v_mean_d8_15, "v_peak": row.v_peak_24h, "p_mean": row.p_mean_d8_15, "vmaxth": row.vmaxth,
            "rmw": row.rmw_mean_d8_15, "t_33ms_day": row.t_33ms_day, "t_peak_day": row.t_peak_24h_day,
            "v_mean_change_pct": change(case, "v_mean_d8_15", noise["v_mean"]), "v_peak_change_pct": change(case, "v_peak_24h", noise["v_peak"]),
            "vmaxth_change_pct": change(case, "vmaxth", noise["vmaxth"]), "env_dt_200": row.env_dt_200, "env_dr_700": row.env_dr_700,
        })
table = pd.DataFrame(rows)
table.to_csv(results / "experiment_table.csv", index=False)

# Figure 1: time evolution in the two main sets.
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
for ax, sst, title in zip(axes, ("sstup", "sstfix"), ("바다와 대기가 함께 변화 (온난화에 가까운 조건)", "대기만 변화 (원인을 나눈 민감도 실험)")):
    for dt in DTS:
        runs = [series(m) for m in members(name("ad", dt, sst))]
        day = runs[0][0]
        winds = np.array([r[1][: len(day)] for r in runs])
        valid = (day >= 0.5) & (day <= 14.5)
        if len(runs) > 1:
            ax.fill_between(day[valid], winds.min(axis=0)[valid], winds.max(axis=0)[valid], color=ps.DT_COLORS[dt], alpha=0.22, linewidth=0)
        ax.plot(day[valid], winds.mean(axis=0)[valid], color=ps.DT_COLORS[dt], label=LABEL[dt], linewidth=1.8 if dt else 1.4, linestyle="-" if len(runs) > 1 else "--")
    ax.axvspan(8, 15, color=ps.GRID, alpha=0.35, linewidth=0, zorder=0)
    ax.set_title(title)
    ax.set_xlabel("모의 시간 (일)")
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 130)
axes[0].set_ylabel("최대 접선풍 (m/s, 24시간 이동평균)")
axes[0].legend(loc="lower right", ncols=2)
axes[1].text(9.2, 8, "실선과 띠: 같은 조건 5회의 평균과 범위\n점선: 반복 없는 단일 실행", fontsize=8, color=ps.INK2)
ps.save(fig, str(results / "sim_01_time_evolution"))

# Figure 3: humidity control and vertical structure.
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
ax = axes[0]
for prefix, label, color in (("ad", "상대습도 고정", ps.ORANGE), ("q", "비습 고정", ps.BLUE)):
    values = [change(name(prefix, dt, "sstfix"), "v_mean_d8_15", noise["v_mean"]) for dt in DTS]
    errors = [repeat.loc[name(prefix, dt, "sstfix"), "v_mean_pct_ci"] if dt > 0 else 0.0 for dt in DTS]
    ax.plot(DTS, values, color=color, linewidth=1.6, zorder=2)
    ax.errorbar(DTS[2:], values[2:], yerr=errors[2:], color=color, fmt="o", markersize=6, markeredgecolor=ps.SURFACE, capsize=4, label=f"{label} (5회, 95% 구간)", zorder=3)
    ax.scatter(DTS[:2], values[:2], s=44, facecolor="none", edgecolor=color, linewidth=1.4, zorder=3)
ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
ax.text(-2, -21.5, "빈 표시: 반복 없는 단일 실행", fontsize=8, color=ps.INK2)
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
        frames = [energy.loc[members(name("ad", dt, sst)), column] for dt in DTS]
        values = [f.mean() for f in frames]
        errors = [2 * f.std() if len(f) > 1 else 0.0 for f in frames]
        ax.errorbar(DTS, values, yerr=errors, color=color, marker="o", markersize=6, markeredgecolor=ps.SURFACE, capsize=3, elinewidth=1, label=title)
    ax.set_xticks(DTS, [LABEL[d] for d in DTS])
    ax.set_title(label, fontsize=10)
axes[0].legend(loc="best", title="세로 막대: 반복 5회 ±2σ", title_fontsize=8)
ps.save(fig, str(results / "sim_04_energy"))

# Figure 5: storm structure of one run per condition, mean of the windows days 7-8, 9-10 and 11-12.
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
        ax.errorbar(sub[column], sub.v_peak, yerr=2 * sub.v_peak_sd, fmt="none", ecolor=color, elinewidth=1, capsize=3, zorder=2)
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
