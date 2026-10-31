"""Test whether ENSO explains the negative year-to-year link between box-mean PI and observed intensity.

Usage: python -I analyze_enso.py <sst.mnmean.nc> <pi-dir> <step2-dir>
Nino3.4 is the Jun-Nov mean ERSST anomaly over 5S-5N, 170-120W relative to 1991-2020.
Peak-position statistics show whether strong seasons simply form and peak in a different place.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xarray as xr

sst_path, pi_dir, step2 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sst = xr.open_dataset(sst_path)["sst"].sel(time=slice("1980-01-01", "2024-12-31")).sortby("lat")
box = sst.sel(lat=slice(-5, 5), lon=slice(190, 240))
weights = np.cos(np.deg2rad(box.lat))
series = box.weighted(weights).mean(("lat", "lon")).load()
clim = series.sel(time=slice("1991-01-01", "2020-12-31")).groupby("time.month").mean()
anomaly = series.groupby("time.month") - clim
jn = anomaly.sel(time=anomaly["time.month"].isin(range(6, 12))).groupby("time.year").mean().to_pandas()
nino = jn.rename("nino34").reset_index()

annual = pd.read_csv(pi_dir / "pi_annual.csv")
annual = annual[annual.season == "jun_nov"]
observed = pd.read_csv(step2 / "annual_analysis.csv")
observed = observed[observed.season == "jun_nov"]
data = annual.merge(observed, on=["year", "season"]).merge(nino, on="year")

storms = pd.read_csv(step2 / "storm_summary_jma.csv", parse_dates=["peak_time"])
storms = storms[storms.peak_month.between(6, 11)]
storms["records"] = storms.n_jma_tropical_records
by_year = storms.groupby("year").agg(peak_lon=("peak_lon", "mean"), peak_lat=("peak_lat", "mean"), mean_records=("records", "mean")).reset_index()
data = data.merge(by_year, on="year")
data.to_csv(pi_dir / "enso_annual.csv", index=False)


def residual(y, controls):
    x = sm.add_constant(np.column_stack(controls))
    return y - x @ np.linalg.lstsq(x, y, rcond=None)[0]


def partial(x, y, *controls):
    return float(np.corrcoef(residual(data[x].values, controls), residual(data[y].values, controls))[0, 1])


def hac_p(y, xs, index=1):
    fit = sm.OLS(data[y].values, sm.add_constant(np.column_stack(xs))).fit().get_robustcov_results("HAC", maxlags=3, use_correction=True, use_t=True)
    return float(fit.params[index]), float(fit.pvalues[index])


year = data["year"].values.astype(float)
nino_values = data["nino34"].values
rows = []
for x, y in [("pi_actual", "mean_peak_kt"), ("pi_actual", "share64_pct"), ("nino34", "mean_peak_kt"), ("nino34", "pi_actual"),
             ("nino34", "mean_records"), ("nino34", "peak_lon"), ("mean_records", "mean_peak_kt"), ("peak_lon", "mean_peak_kt")]:
    beta, p = hac_p(y, [data[x].values, year])
    rows.append({"x": x, "y": y, "controls": "year", "partial_r": partial(x, y, year), "beta": beta, "p_hac": p})
for x, y in [("pi_actual", "mean_peak_kt"), ("pi_actual", "share64_pct")]:
    beta, p = hac_p(y, [data[x].values, year, nino_values])
    rows.append({"x": x, "y": y, "controls": "year+nino34", "partial_r": partial(x, y, year, nino_values), "beta": beta, "p_hac": p})
result = pd.DataFrame(rows)
result.to_csv(pi_dir / "enso_associations.csv", index=False)
pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:.3f}")
print(result.to_string(index=False))
