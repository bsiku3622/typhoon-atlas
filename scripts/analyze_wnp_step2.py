"""Reproduce the 1980–2024 WNP observed-intensity exploratory analysis.

This script does not estimate potential intensity or attribute changes to warming.
Inputs remain unchanged. Run with the task analysis Python environment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parents[1]
RAW = Path.home() / "Bufs/Codex Files/2026-09-28"
YEARS = np.arange(1980, 2025)
BOX = {"latitude": [5, 30], "longitude": [120, 180]}
CORE = ["count_ts", "mean_peak_kt", "share64_pct"]
LABELS = {
    "count_ts": "Tropical storms and typhoons (count)",
    "mean_peak_kt": "Mean storm peak wind (kt)",
    "share64_pct": "Typhoon share among TS+ systems (%)",
    "share85_pct": "Share reaching 85 kt (%)",
    "max_peak_kt": "Annual maximum observed wind (kt)",
    "count64": "Systems reaching 64 kt (count)",
    "mean_min_pressure_hpa": "Mean minimum pressure (hPa)",
    "temperature_complete_c": "Air-temperature anomaly (deg C)",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def storm_data(source: Path, output: Path):
    columns = ["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "NATURE", "LAT", "LON",
               "TRACK_TYPE", "TOKYO_GRADE", "TOKYO_WIND", "TOKYO_PRES", "USA_WIND", "USA_STATUS"]
    original = pd.read_csv(source, skiprows=[1], usecols=columns, skipinitialspace=True,
                           na_values=[" "], low_memory=False)
    rows = original.loc[original.SEASON.between(1980, 2024) & original.BASIN.eq("WP")].copy()
    type_counts = rows.TRACK_TYPE.value_counts().to_dict()
    rows = rows.loc[rows.TRACK_TYPE.eq("main")].copy()
    rows["time"] = pd.to_datetime(rows.ISO_TIME, errors="raise")
    duplicate_count = int(rows.duplicated(["SID", "time"]).sum())
    if duplicate_count:
        raise ValueError(f"Resolve {duplicate_count} main-track duplicate records before analysis")
    # JMA grades 3/4/5 are tropical storm/severe tropical storm/typhoon; 9 is TS+.
    tropical = rows.loc[rows.TOKYO_GRADE.isin([3, 4, 5, 9]) & rows.TOKYO_WIND.gt(0)].copy()
    tropical = tropical.sort_values(["SID", "time"])
    groups = tropical.groupby("SID", sort=True)
    peaks = tropical.loc[groups.TOKYO_WIND.idxmax()].set_index("SID")
    storms = groups.agg(year=("SEASON", "first"), name=("NAME", "first"),
                        peak_wind_kt=("TOKYO_WIND", "max"), min_pressure_hpa=("TOKYO_PRES", "min"),
                        n_jma_tropical_records=("TOKYO_WIND", "count"))
    storms["peak_time"] = peaks.time
    storms["peak_month"] = peaks.time.dt.month
    storms["peak_lat"] = peaks.LAT
    storms["peak_lon"] = peaks.LON
    storms["usa_peak_on_jma_tropical_records_kt"] = groups.USA_WIND.max()
    population = storms.loc[storms.peak_wind_kt.ge(34)].copy()
    population.to_csv(output / "storm_summary_jma.csv", index=True, float_format="%.8g")

    summaries = []
    for season, months in [("annual", list(range(1, 13))), ("jun_nov", list(range(6, 12)))]:
        for year in YEARS:
            s = population.loc[population.year.eq(year) & population.peak_month.isin(months)]
            n = len(s)
            summaries.append({
                "year": int(year), "season": season, "count_ts": n,
                "count64": int(s.peak_wind_kt.ge(64).sum()),
                "count85": int(s.peak_wind_kt.ge(85).sum()),
                "share64_pct": 100 * s.peak_wind_kt.ge(64).mean() if n else np.nan,
                "share85_pct": 100 * s.peak_wind_kt.ge(85).mean() if n else np.nan,
                "mean_peak_kt": s.peak_wind_kt.mean(), "max_peak_kt": s.peak_wind_kt.max(),
                "mean_min_pressure_hpa": s.min_pressure_hpa.mean(),
                "mean_peak_lat": s.peak_lat.mean(),
            })
    quality = {"raw_wp_records": int(sum(type_counts.values())), "track_types": type_counts,
               "main_wp_records": len(rows), "main_wp_sids": int(rows.SID.nunique()),
               "jma_tropical_records": len(tropical), "jma_tsplus_sids": len(population),
               "main_sids_without_valid_jma_tropical_wind": int(rows.SID.nunique()-len(storms)),
               "jma_grade_counts_main": {str(k): int(v) for k, v in rows.TOKYO_GRADE.value_counts().items()},
               "duplicate_sid_times": duplicate_count,
               "wind_definition": "TOKYO_WIND, JMA 10-minute sustained wind, knots",
               "population": "main-track WP systems with JMA tropical-grade peak >=34 kt",
               "peak_definition": "max JMA wind while in WP and JMA grade 3,4,5,9; earliest time in a tie",
               "season_definition": "peak-month assigned; annual 1–12, Jun–Nov 6–11"}
    return pd.DataFrame(summaries), population, tropical, quality


def climate_data(source: Path, output: Path):
    with netCDF4.Dataset(source) as nc:
        time = nc.variables["time"]
        dates = netCDF4.num2date(time[:], time.units, calendar=getattr(time, "calendar", "standard"))
        keep = np.array([1980 <= d.year <= 2024 for d in dates])
        year = np.array([d.year for d in dates])[keep]
        month = np.array([d.month for d in dates])[keep]
        lat = np.array(nc.variables["latitude"][:])
        lon = np.array(nc.variables["longitude"][:])
        anomaly = np.ma.filled(nc.variables["t_anoms"][keep], np.nan)
    li = np.flatnonzero((lat >= BOX["latitude"][0]) & (lat <= BOX["latitude"][1]))
    lj = np.flatnonzero((lon >= BOX["longitude"][0]) & (lon <= BOX["longitude"][1]))
    a = anomaly[:, li][:, :, lj]
    weights = np.broadcast_to(np.cos(np.deg2rad(lat[li]))[:, None], a.shape[1:])
    availability = np.isfinite(a).mean(axis=0)
    masks = {"complete": availability == 1, "coverage80": availability >= .8,
             "available": np.ones(a.shape[1:], dtype=bool)}
    cells = [{"lat": float(lat[i]), "lon": float(lon[j]), "observed_month_fraction": availability[ii, jj],
              "complete_mask": bool(masks["complete"][ii, jj]), "coverage80_mask": bool(masks["coverage80"][ii, jj])}
             for ii, i in enumerate(li) for jj, j in enumerate(lj)]
    pd.DataFrame(cells).to_csv(output / "climate_grid_coverage.csv", index=False)
    monthly = pd.DataFrame({"year": year, "month": month})
    for label, mask in masks.items():
        w = weights * mask
        if not w.sum():
            raise ValueError(f"No temperature cells in {label} mask")
        observed = np.isfinite(a) & mask
        observed_weight = (observed * weights).sum(axis=(1, 2))
        coverage = observed_weight / w.sum()
        mean = np.nansum(a * w, axis=(1, 2)) / np.where(observed_weight > 0, observed_weight, np.nan)
        if label != "available":
            mean[coverage < .8] = np.nan
        monthly[f"temperature_{label}_c"] = mean
        monthly[f"coverage_{label}"] = coverage
    monthly.to_csv(output / "regional_temperature_monthly.csv", index=False, float_format="%.9g")
    annual = []
    for label, months in [("annual", list(range(1, 13))), ("jun_nov", list(range(6, 12)))]:
        for y in YEARS:
            selected = monthly.loc[monthly.year.eq(y) & monthly.month.isin(months)]
            result = {"year": int(y), "season": label}
            for mask in masks:
                values = selected[f"temperature_{mask}_c"]
                result[f"temperature_{mask}_c"] = values.mean() if values.notna().sum() == len(months) else np.nan
                result[f"temperature_{mask}_months"] = int(values.notna().sum())
            annual.append(result)
    quality = {"box": BOX, "source": "HadISDH.blendT 1.5.1.2024f, 5-degree grid",
               "variable": "near-surface air-temperature anomaly relative to 1991–2020; NOT SST",
               "domain_cells": int(availability.size), "complete_cells": int(masks["complete"].sum()),
               "coverage80_cells": int(masks["coverage80"].sum()),
               "mean_observed_cell_fraction": float(np.isfinite(a).mean()),
               "complete_mask_extent": {"lat": [min(c["lat"] for c in cells if c["complete_mask"]),
                                                  max(c["lat"] for c in cells if c["complete_mask"])],
                                         "lon": [min(c["lon"] for c in cells if c["complete_mask"]),
                                                  max(c["lon"] for c in cells if c["complete_mask"])]},
               "primary_mask": "same cells observed in all 540 months; no interpolation",
               "aggregation": "cos(latitude) monthly weighted anomalies, equal-month annual/season means",
               "warning": "blend includes land/marine air; sparse fixed stations are not a full ocean-basin mean"}
    return pd.DataFrame(annual), quality


def ols(y, x):
    return sm.OLS(np.asarray(y, dtype=float), np.asarray(x, dtype=float)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 3, "use_correction": True}, use_t=True)


def correlation(x, y):
    return float(stats.pearsonr(x, y).statistic)


def relation(frame, predictor, metric, start, lag=3):
    d = frame.loc[frame.year.ge(start), ["year", predictor, metric]].dropna()
    y = d[metric].to_numpy()
    x = d[predictor].to_numpy()
    t = d.year.to_numpy()-d.year.mean()
    t_design = np.column_stack([np.ones(len(d)), t])
    xr = x - t_design @ np.linalg.lstsq(t_design, x, rcond=None)[0]
    yr = y - t_design @ np.linalg.lstsq(t_design, y, rcond=None)[0]
    model = sm.OLS(y, np.column_stack([np.ones(len(d)), x-x.mean(), t])).fit(
        cov_type="HAC", cov_kwds={"maxlags": lag, "use_correction": True}, use_t=True)
    raw_model = ols(y, sm.add_constant(x))
    return {"season": d.attrs.get("season", ""), "predictor": predictor, "metric": metric,
            "start": start, "end": int(d.year.max()), "n_years": len(d), "hac_lags": lag,
            "pearson_r": correlation(x, y), "spearman_rho": float(stats.spearmanr(x, y).statistic),
            "partial_r_year": correlation(xr, yr),
            "temperature_beta_per_c": float(model.params[1]),
            "temperature_ci_low": float(model.conf_int()[1, 0]),
            "temperature_ci_high": float(model.conf_int()[1, 1]),
            "temperature_p_hac": float(model.pvalues[1]),
            "unadjusted_beta_per_c": float(raw_model.params[1]),
            "unadjusted_p_hac": float(raw_model.pvalues[1]),
            "temperature_year_r": correlation(x, t),
            "residual_lag1": correlation(model.resid[:-1], model.resid[1:])}


def analyze(frame, output: Path):
    trend_rows, relationship_rows = [], []
    metrics = CORE + ["share85_pct", "max_peak_kt", "count64", "mean_min_pressure_hpa"]
    for season, seasonal in frame.groupby("season"):
        for metric in metrics + ["temperature_complete_c", "temperature_coverage80_c"]:
            d = seasonal[["year", metric]].dropna()
            model = ols(d[metric], sm.add_constant((d.year-d.year.mean()) / 10))
            trend_rows.append({"season": season, "metric": metric, "n_years": len(d),
                               "slope_per_decade": model.params.iloc[1] if hasattr(model.params, "iloc") else model.params[1],
                               "ci_low": model.conf_int()[1, 0], "ci_high": model.conf_int()[1, 1],
                               "p_hac": model.pvalues[1]})
        for predictor in ["temperature_complete_c", "temperature_coverage80_c", "temperature_available_c"]:
            for metric in metrics:
                for start in [1980, 1990, 2000]:
                    r = relation(seasonal, predictor, metric, start)
                    r["season"] = season
                    relationship_rows.append(r)
        # Lag sensitivity on the primary design, with the same three endpoints.
        for lag in [1, 5]:
            for metric in CORE:
                r = relation(seasonal, "temperature_complete_c", metric, 1980, lag)
                r["season"] = season
                relationship_rows.append(r)
    trends = pd.DataFrame(trend_rows)
    trends["q_bh_all_trends"] = multipletests(trends.p_hac, method="fdr_bh")[1]
    relations = pd.DataFrame(relationship_rows)
    relations["q_bh_all_exploratory"] = multipletests(relations.temperature_p_hac, method="fdr_bh")[1]
    relations["q_bh_primary3"] = np.nan
    primary = relations.season.eq("annual") & relations.predictor.eq("temperature_complete_c") & relations.start.eq(1980) & relations.hac_lags.eq(3) & relations.metric.isin(CORE)
    relations.loc[primary, "q_bh_primary3"] = multipletests(relations.loc[primary, "temperature_p_hac"], method="fdr_bh")[1]
    trends.to_csv(output / "time_trends.csv", index=False, float_format="%.9g")
    relations.to_csv(output / "temperature_associations.csv", index=False, float_format="%.9g")
    return trends, relations


def make_figures(frame, trends, relations, output: Path):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .2, "axes.axisbelow": True,
                         "savefig.facecolor": "white"})
    d = frame.loc[frame.season.eq("annual")].sort_values("year")
    colors = {"temperature_complete_c": "#334155", "count_ts": "#2563eb", "mean_peak_kt": "#b45309", "share64_pct": "#0f766e"}
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True, layout="constrained")
    for ax, metric in zip(axes, ["temperature_complete_c"] + CORE):
        ax.plot(d.year, d[metric], marker="o", markersize=2.8, linewidth=1, color=colors[metric])
        fit = sm.OLS(d[metric], sm.add_constant((d.year-d.year.mean())/10)).fit()
        ax.plot(d.year, fit.fittedvalues, linewidth=1, linestyle="--", color="#222222")
        tr = trends.loc[trends.season.eq("annual") & trends.metric.eq(metric)].iloc[0]
        unit = "deg C" if metric.startswith("temperature") else "percentage points" if metric.endswith("pct") else "kt" if metric.endswith("kt") else "storms"
        ax.set_title(f"{LABELS[metric]} | trend {tr.slope_per_decade:+.2f} {unit}/decade, HAC p={tr.p_hac:.3g}", loc="left", fontsize=10)
    axes[-1].set_xlabel("Year")
    fig.suptitle("Western North Pacific: observed cyclone intensity and regional air temperature, 1980–2024", fontsize=12)
    fig.savefig(output / "01_time_series.png", dpi=180)
    fig.savefig(output / "01_time_series.pdf")
    plt.close(fig)

    coverage = pd.read_csv(output / "climate_grid_coverage.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), layout="constrained")
    image = axes[0].scatter(coverage.lon, coverage.lat, c=coverage.observed_month_fraction,
                            cmap="Blues", vmin=0, vmax=1, marker="s", s=300)
    complete = coverage.loc[coverage.complete_mask]
    axes[0].scatter(complete.lon, complete.lat, facecolors="none", edgecolors="#b45309", s=80, linewidths=1.5)
    axes[0].set(xlim=(120, 180), ylim=(5, 30), xlabel="Longitude (degrees E)", ylabel="Latitude (degrees N)")
    axes[0].set_title("Observed fraction of 540 months; rings = complete cells", fontsize=10)
    fig.colorbar(image, ax=axes[0], label="Observed-month fraction", shrink=.7)
    for col, label in [("temperature_complete_c", "14 complete cells"),
                       ("temperature_coverage80_c", "32 high-coverage cells"),
                       ("temperature_available_c", "All available cells")]:
        axes[1].plot(d.year, d[col], linewidth=1, label=label)
    axes[1].set(xlabel="Year", ylabel="Air-temperature anomaly (deg C)")
    axes[1].set_title("Annual index sensitivity to spatial sampling", fontsize=10)
    axes[1].legend(fontsize=8, frameon=False)
    fig.suptitle("HadISDH coverage limitation: the complete-cell index samples the western part of the box", fontsize=11)
    fig.savefig(output / "03_coverage_sensitivity.png", dpi=180)
    fig.savefig(output / "03_coverage_sensitivity.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout="constrained")
    year_design = sm.add_constant(d.year-d.year.mean())
    xr = sm.OLS(d.temperature_complete_c, year_design).fit().resid
    primary = relations.loc[relations.season.eq("annual") & relations.start.eq(1980) & relations.hac_lags.eq(3) & relations.predictor.eq("temperature_complete_c")]
    for col, metric in enumerate(CORE):
        r = primary.loc[primary.metric.eq(metric)].iloc[0]
        yr = sm.OLS(d[metric], year_design).fit().resid
        for row, (x, y) in enumerate([(d.temperature_complete_c, d[metric]), (xr, yr)]):
            ax = axes[row, col]
            dots = ax.scatter(x, y, c=d.year, cmap="viridis", s=26, alpha=.85, edgecolors="white", linewidths=.4)
            beta = np.polyfit(x, y, 1)
            xline = np.linspace(x.min(), x.max(), 100)
            ax.plot(xline, np.polyval(beta, xline), color="#333333", linewidth=1, linestyle="--")
            ax.set_xlabel("Air-temperature anomaly (deg C)" if row == 0 else "Year-detrended temperature residual (deg C)")
            ax.set_ylabel(LABELS[metric] if row == 0 else f"Residual: {LABELS[metric]}")
            ax.set_title(f"Pearson r={r.pearson_r:+.2f}" if row == 0 else f"Partial r={r.partial_r_year:+.2f}; adjusted HAC p={r.temperature_p_hac:.3g}")
    fig.colorbar(dots, ax=axes, label="Year", shrink=.7, pad=.025)
    fig.suptitle("Raw associations and associations after removing a linear year trend", fontsize=13)
    fig.savefig(output / "02_temperature_relationships.png", dpi=180)
    fig.savefig(output / "02_temperature_relationships.pdf")
    plt.close(fig)


def agency_sensitivity(storms, annual, output: Path):
    common = storms.dropna(subset=["usa_peak_on_jma_tropical_records_kt"]).copy()
    common = common.loc[common.usa_peak_on_jma_tropical_records_kt.gt(0)]
    means = common.groupby("year").agg(
        n_common=("peak_wind_kt", "size"),
        jma_mean_peak_10min_kt=("peak_wind_kt", "mean"),
        usa_mean_peak_1min_kt=("usa_peak_on_jma_tropical_records_kt", "mean"))
    means.to_csv(output / "agency_common_sample_annual.csv", float_format="%.9g")
    rows = []
    climate = annual.loc[annual.season.eq("annual"), ["year", "temperature_complete_c"]]
    merged = means.reset_index().merge(climate, on="year", validate="one_to_one")
    for metric in ["jma_mean_peak_10min_kt", "usa_mean_peak_1min_kt"]:
        result = relation(merged, "temperature_complete_c", metric, 1980)
        model = ols(merged[metric], sm.add_constant((merged.year-merged.year.mean())/10))
        result.update({"slope_per_decade": float(model.params[1]), "trend_ci_low": float(model.conf_int()[1, 0]),
                       "trend_ci_high": float(model.conf_int()[1, 1]), "trend_p_hac": float(model.pvalues[1])})
        rows.append(result)
    pd.DataFrame(rows).to_csv(output / "agency_sensitivity.csv", index=False, float_format="%.9g")
    return {"n_common_storms": len(common), "definition": "same JMA TS+ systems and JMA tropical-grade observation times; no wind-duration conversion", "results": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ibtracs", type=Path, default=RAW / "ibtracs/ibtracs.since1980.list.v04r01.csv")
    parser.add_argument("--temperature", type=Path, default=RAW / "climate/hadisdh-blend-2024/HadISDH.blendT.1.5.1.2024f_FLATgridHOMBClocalSHIPboth5by5_anoms9120.nc")
    parser.add_argument("--output", type=Path, default=ROOT / "research/step2-wnp-1980-2024")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    storm_annual, storms, records, storm_quality = storm_data(args.ibtracs, args.output)
    print(f"JMA TS+ systems: {len(storms)}", flush=True)
    climate_annual, climate_quality = climate_data(args.temperature, args.output)
    annual = storm_annual.merge(climate_annual, on=["year", "season"], how="left", validate="one_to_one")
    if not annual.temperature_complete_c.notna().all():
        raise ValueError("Primary fixed-mask temperature series must contain all 90 year/season values")
    if not (annual.count64 <= annual.count_ts).all():
        raise ValueError("Typhoon counts cannot exceed the TS+ population")
    if annual.loc[annual.season.eq("annual"), "count_ts"].sum() != len(storms):
        raise ValueError("Annual cyclone totals do not reconcile to unique systems")
    # Independent row-wise count for the first and last years reconciles group aggregation.
    for year in [1980, 2024]:
        expected = records.loc[records.SEASON.eq(year) & records.TOKYO_WIND.ge(34), "SID"].nunique()
        actual = int(annual.loc[annual.year.eq(year) & annual.season.eq("annual"), "count_ts"].iloc[0])
        assert expected == actual, (year, expected, actual)
    official_checks = []
    for year, metric, expected in [(1980, "count_ts", 24), (2023, "count_ts", 17),
                                   (2024, "count_ts", 26), (2024, "count64", 13)]:
        actual = int(annual.loc[annual.year.eq(year) & annual.season.eq("annual"), metric].iloc[0])
        official_checks.append({"year": year, "metric": metric, "expected": expected,
                                "actual": actual, "matches": actual == expected})
        if actual != expected:
            raise ValueError(f"Review JMA reference mismatch: {year} {metric}: {actual} vs {expected}")
    annual.to_csv(args.output / "annual_analysis.csv", index=False, float_format="%.9g")
    trends, relations = analyze(annual, args.output)
    make_figures(annual, trends, relations, args.output)
    agency = agency_sensitivity(storms, annual, args.output)
    manifest = {"period": [1980, 2024], "storm_quality": storm_quality, "climate_quality": climate_quality,
                "official_count_checks": {"checks": official_checks,
                                          "sources": ["https://www.data.jma.go.jp/typhoon/statistics/generation/generation.html",
                                                      "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/AnnualReport/2024/Text/Text2024.pdf"]},
                "inputs": [{"path": str(p), "size_bytes": p.stat().st_size, "sha256": sha256(p)} for p in [args.ibtracs, args.temperature]],
                "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "statsmodels", "matplotlib", "netCDF4"]},
                "agency_sensitivity": agency,
                "inference": {"regression": "OLS; HAC Newey–West covariance; Bartlett default, lags=3, finite-sample correction, Student-t intervals",
                              "primary": "annual complete fixed-cell temperature; three core endpoints",
                              "primary_endpoints": CORE,
                              "adjustment": "linear year term; exploratory association, not causal attribution",
                              "multiplicity": "BH across 3 primary temperature coefficients; all exploratory coefficients also adjusted together",
                              "sensitivity": "June–November peak-month subset, 1990/2000 starts, coverage80/available masks, HAC lags 1 and 5",
                              "not_done": ["potential intensity", "SST or vertical temperature effects", "ENSO/shear control", "observation homogenization"]}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"quality": manifest["storm_quality"], "climate": climate_quality}, indent=2), flush=True)
    print("PRIMARY ANNUAL TRENDS", flush=True)
    print(trends.loc[trends.season.eq("annual")].to_string(index=False), flush=True)
    print("PRIMARY TEMPERATURE ASSOCIATIONS", flush=True)
    print(relations.loc[relations.q_bh_primary3.notna()].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
