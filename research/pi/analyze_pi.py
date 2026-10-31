"""Long-term potential intensity analysis for the western North Pacific, 1980-2024.

Usage: python -I analyze_pi.py <pi_wnp_monthly.nc> <step2-dir> <output-dir>
Box means are cos(latitude) weighted over 5-30N, 120-180E. Trends and coefficients use OLS with
Newey-West HAC errors (lag 3, small-sample correction, Student-t), matching the observed-intensity
analysis so the two can be read together. Partial correlation removes a linear year trend from both.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plot_style as ps  # noqa: E402

source, step2, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
ps.setup()
ds = xr.open_dataset(source).load()
weights = np.cos(np.deg2rad(ds.lat))
FIELDS = ["pi_actual", "pi_sst_only", "pi_atm_only", "outflow_actual", "sst", "t1000", "t850", "t500", "t200", "r1000"]
SEASONS = {"annual": list(range(1, 13)), "jun_nov": list(range(6, 12))}


def box_mean(field):
    return field.weighted(weights).mean(("lat", "lon"))


rows = []
for season, months in SEASONS.items():
    sel = ds.sel(time=ds["time.month"].isin(months))
    means = {f: box_mean(sel[f]).groupby("time.year").mean().to_pandas() for f in FIELDS}
    frame = pd.DataFrame(means)
    frame.insert(0, "season", season)
    frame.index.name = "year"
    rows.append(frame.reset_index())
annual = pd.concat(rows, ignore_index=True)
annual.to_csv(out / "pi_annual.csv", index=False)


def hac(y, x):
    return sm.OLS(y, sm.add_constant(x)).fit().get_robustcov_results("HAC", maxlags=3, use_correction=True, use_t=True)


def trend(frame, column):
    fit = hac(frame[column].values, frame["year"].values.astype(float))
    lo, hi = fit.conf_int()[1]
    return {"slope_per_decade": fit.params[1] * 10, "ci_low": lo * 10, "ci_high": hi * 10, "p_hac": fit.pvalues[1]}


def association(frame, x, y):
    data = frame[[x, y, "year"]].dropna()
    years = data["year"].values.astype(float)
    xv, yv = data[x].values, data[y].values

    def detrend(v):
        d = sm.add_constant(years)
        return v - d @ np.linalg.lstsq(d, v, rcond=None)[0]

    fit = hac(yv, np.column_stack([xv, years]))
    lo, hi = fit.conf_int()[1]
    return {
        "n_years": len(data), "pearson_r": np.corrcoef(xv, yv)[0, 1], "partial_r_year": np.corrcoef(detrend(xv), detrend(yv))[0, 1],
        "beta_per_unit": fit.params[1], "ci_low": lo, "ci_high": hi, "p_hac": fit.pvalues[1], "year_r": np.corrcoef(xv, years)[0, 1],
    }


trend_rows = []
for season in SEASONS:
    frame = annual[annual.season == season]
    for column in FIELDS:
        trend_rows.append({"season": season, "metric": column, **trend(frame, column)})
trends = pd.DataFrame(trend_rows)
trends.to_csv(out / "pi_trends.csv", index=False)

observed = pd.read_csv(step2 / "annual_analysis.csv")
merged = annual.merge(observed, on=["year", "season"], how="left")
pairs = [
    ("temperature_complete_c", "pi_actual"), ("temperature_coverage80_c", "pi_actual"), ("temperature_available_c", "pi_actual"),
    ("sst", "pi_actual"), ("t1000", "pi_actual"), ("t500", "pi_actual"), ("t200", "pi_actual"),
    ("pi_actual", "mean_peak_kt"), ("pi_actual", "share64_pct"), ("pi_actual", "count_ts"), ("pi_actual", "max_peak_kt"),
    ("temperature_complete_c", "mean_peak_kt"),
]
assoc_rows = []
for season in SEASONS:
    frame = merged[merged.season == season]
    for x, y in pairs:
        assoc_rows.append({"season": season, "x": x, "y": y, **association(frame, x, y)})
assoc = pd.DataFrame(assoc_rows)
assoc.to_csv(out / "pi_associations.csv", index=False)

# Observed storm peak against potential intensity at the same month and nearest grid point.
storms = pd.read_csv(step2 / "storm_summary_jma.csv", parse_dates=["peak_time"])
in_box = storms[(storms.peak_lat.between(5, 30)) & (storms.peak_lon.between(120, 180))].copy()
values = []
for row in in_box.itertuples():
    month = pd.Timestamp(row.peak_time.year, row.peak_time.month, 1)
    point = ds["pi_actual"].sel(time=month).sel(lat=row.peak_lat, lon=row.peak_lon, method="nearest", tolerance=2.5)
    values.append(float(point))
in_box["pi_at_peak_ms"] = values
in_box["peak_wind_ms"] = in_box.peak_wind_kt * 0.51444
in_box["ratio"] = in_box.peak_wind_ms / in_box.pi_at_peak_ms
in_box.to_csv(out / "storm_pi.csv", index=False)
valid = in_box.dropna(subset=["pi_at_peak_ms"])
storm_summary = {
    "storms_total": len(storms), "peak_in_box": len(in_box), "with_pi": len(valid),
    "median_ratio": valid.ratio.median(), "p90_ratio": valid.ratio.quantile(0.9), "share_above_pi": (valid.ratio > 1).mean(),
    "corr_peak_pi": np.corrcoef(valid.peak_wind_ms, valid.pi_at_peak_ms)[0, 1],
}
pd.Series(storm_summary).to_csv(out / "storm_pi_summary.csv", header=["value"])

# Figure 1: anomalies of the three PI versions in the typhoon season.
season = annual[annual.season == "jun_nov"].reset_index(drop=True)
base = (season.year >= 1991) & (season.year <= 2020)
fig, ax = plt.subplots(figsize=(8.2, 3.8))
for column, label, color in (("pi_actual", "실제 환경", ps.BLUE), ("pi_sst_only", "SST만 변화", ps.ORANGE), ("pi_atm_only", "대기만 변화", ps.AQUA)):
    anomaly = season[column] - season.loc[base, column].mean()
    ax.plot(season.year, anomaly, color=color, label=label)
    ax.annotate(label, (season.year.iloc[-1], anomaly.iloc[-1]), xytext=(5, 0), textcoords="offset points", va="center", color=ps.INK2, fontsize=9)
ax.axhline(0, color=ps.NEUTRAL, linewidth=0.8)
ax.set_title("서북태평양 최대잠재강도 편차 (6–11월, 1991–2020 평균 대비)")
ax.set_ylabel("PI 편차 (m/s)")
ax.set_xlabel("연도")
ax.set_xlim(1980, 2030)
ax.legend(loc="upper left", ncols=3)
ps.save(fig, str(out / "pi_01_timeseries"))

# Figure 2: climatological PI map with storm peak positions.
clim = ds["pi_actual"].sel(time=ds["time.month"].isin(SEASONS["jun_nov"])).mean("time")
fig, ax = plt.subplots(figsize=(8.2, 3.9))
mesh = ax.pcolormesh(clim.lon, clim.lat, clim, cmap="Blues", shading="nearest")
fig.colorbar(mesh, ax=ax, label="PI (m/s)", pad=0.02)
strong = valid[valid.peak_wind_kt >= 64]
ax.scatter(strong.peak_lon, strong.peak_lat, s=8, facecolor="none", edgecolor=ps.ORANGE, linewidth=0.6, label="태풍급(64 kt 이상) 최대 강도 위치")
ax.set_title("6–11월 평균 최대잠재강도와 관측 태풍의 최대 강도 위치 (1980–2024)")
ax.set_xlabel("경도 (°E)")
ax.set_ylabel("위도 (°N)")
ax.grid(False)
ax.legend(loc="lower right", frameon=True, facecolor=ps.SURFACE, edgecolor="none")
ps.save(fig, str(out / "pi_02_map"))

# Figure 3: observed peak wind against PI, storm by storm.
fig, ax = plt.subplots(figsize=(4.6, 4.2))
ax.scatter(valid.pi_at_peak_ms, valid.peak_wind_ms, s=9, color=ps.BLUE, alpha=0.45, linewidth=0)
limit = [20, 95]
ax.plot(limit, limit, color=ps.NEUTRAL, linewidth=0.9)
ax.annotate("실제 강도 = PI", (88, 88), xytext=(-6, 4), textcoords="offset points", ha="right", color=ps.INK2, fontsize=9)
ax.set_xlim(*limit)
ax.set_ylim(*limit)
ax.set_xlabel("최대 강도 위치의 월평균 PI (m/s)")
ax.set_ylabel("JMA 10분 평균 최대 풍속 (m/s)")
ax.set_title("태풍별 실제 최대 강도와 PI")
ps.save(fig, str(out / "pi_03_storm_vs_pi"))

pd.set_option("display.width", 220, "display.max_columns", 30, "display.float_format", lambda v: f"{v:.4g}")
print("== Trends per decade")
print(trends.to_string(index=False))
print("== Associations")
print(assoc.drop(columns=["year_r"]).to_string(index=False))
print("== Storm vs PI")
print(storm_summary)
print("== Jun-Nov means")
print(season[["pi_actual", "pi_sst_only", "pi_atm_only", "outflow_actual", "sst"]].describe().loc[["mean", "std", "min", "max"]])
