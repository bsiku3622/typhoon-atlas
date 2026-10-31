"""Repeat the potential intensity decomposition with NCEP/DOE Reanalysis 2 as a sensitivity check.

Usage: python -I compute_pi_r2.py <raw_r2-dir> <sst.mnmean.nc> <output-dir>
Same box, period, SST source, PI settings and climatology as compute_pi_wnp.py. R2 provides relative
humidity rather than specific humidity, so mixing ratio is derived from T, RH and pressure.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xarray as xr
from tcpyPI import pi

raw, sst_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PERIOD = ("1980-01-01", "2024-12-31")
LAT, LON = slice(30, 5), slice(120, 180)
PTOP = 50.0

air = xr.open_dataset(raw / "air.mon.mean.nc")["air"]
rhum = xr.open_dataset(raw / "rhum.mon.mean.nc")["rhum"]
mslp = xr.open_dataset(raw / "mslp.mon.mean.nc")["mslp"]
sst = xr.open_dataset(sst_path)["sst"]
meta = {"air_units": str(air.attrs.get("units")), "rhum_units": str(rhum.attrs.get("units")), "mslp_units": str(mslp.attrs.get("units"))}
air = air.squeeze(drop=True).sel(time=slice(*PERIOD), lat=LAT, lon=LON, level=slice(1000, PTOP)).load()
rhum = rhum.squeeze(drop=True).sel(time=slice(*PERIOD), lat=LAT, lon=LON).load()
mslp = mslp.squeeze(drop=True).sel(time=slice(*PERIOD), lat=LAT, lon=LON).load()
sst = sst.sel(time=slice(*PERIOD)).sortby("lat").interp(lat=air.lat, lon=air.lon).load()
print(json.dumps(meta), dict(air.sizes), "rhum levels", rhum.level.values.tolist(), flush=True)
if int((~np.isfinite(air)).sum()) or int((~np.isfinite(mslp)).sum()):
    raise SystemExit("non-finite air or sea-level pressure values")
bad = ~np.isfinite(rhum)
print("non-finite humidity values:", int(bad.sum()), flush=True)
if int(bad.sum()):
    normal = rhum.where(~bad).sel(time=slice("1991-01-01", "2020-12-31")).groupby("time.month").mean()
    rhum = rhum.where(~bad).groupby("time.month").fillna(normal).drop_vars("month", errors="ignore")

levels = air.level.values.astype(float)
t = air.transpose("time", "level", "lat", "lon").values.astype(float)
if np.nanmax(t) > 100:
    t = t - 273.15
slp = mslp.transpose("time", "lat", "lon").values.astype(float)
if np.nanmax(slp) > 2000:
    slp = slp / 100.0
rh = rhum.reindex(level=levels).fillna(0.0).transpose("time", "level", "lat", "lon").values.astype(float) / 100.0
e = np.minimum(rh * 6.112 * np.exp(17.67 * t / (t + 243.5)), 0.5 * levels[None, :, None, None])
r = 622.0 * e / (levels[None, :, None, None] - e)
s = sst.transpose("time", "lat", "lon").values.astype(float)
months = air["time.month"].values
years = air["time.year"].values
base = (years >= 1991) & (years <= 2020)


def climatology(values):
    table = np.array([np.nanmean(values[(months == m) & base], axis=0) for m in range(1, 13)])
    return table[months - 1]


t_c, r_c, slp_c = climatology(t), climatology(r), climatology(slp)
s_c = np.where(np.isfinite(s), climatology(s), np.nan)


def run(ss, pp, tt, rr):
    nt, ny, nx = ss.shape
    v = np.full((nt, ny, nx), np.nan)
    for it in range(nt):
        for iy in range(ny):
            for ix in range(nx):
                if np.isfinite(ss[it, iy, ix]):
                    value, _, flag, _, _ = pi(float(ss[it, iy, ix]), float(pp[it, iy, ix]), levels, tt[it, :, iy, ix], rr[it, :, iy, ix],
                                              CKCD=0.9, ascent_flag=0, diss_flag=1, V_reduc=0.8, ptop=PTOP, miss_handle=1)
                    if flag == 1:
                        v[it, iy, ix] = value
    return v


start = time.time()
fields = {"pi_actual": run(s, slp, t, r), "pi_sst_only": run(s, slp_c, t_c, r_c), "pi_atm_only": run(s_c, slp, t, r)}
print(f"PI done in {time.time() - start:.0f}s, valid {int(np.isfinite(fields['pi_actual']).sum())}", flush=True)
fields["sst"] = s
for level in (1000, 850, 500, 200):
    fields[f"t{level}"] = t[:, int(np.argmin(np.abs(levels - level)))]
ds = xr.Dataset({k: (("time", "lat", "lon"), v) for k, v in fields.items()}, coords={"time": air.time.values, "lat": air.lat.values, "lon": air.lon.values})
scratch = raw.parent / "pi_wnp_monthly_r2.nc"
ds.to_netcdf(scratch)
shutil.copyfile(scratch, out / "pi_wnp_monthly_r2.nc")

r1 = pd.read_csv(out / "pi_trends.csv")
weights = np.cos(np.deg2rad(ds.lat))
sel = ds.sel(time=ds["time.month"].isin(range(6, 12)))
rows = []
for name in fields:
    series = sel[name].weighted(weights).mean(("lat", "lon")).groupby("time.year").mean()
    fit = sm.OLS(series.values, sm.add_constant(series.year.values.astype(float))).fit().get_robustcov_results("HAC", maxlags=3, use_correction=True, use_t=True)
    lo, hi = fit.conf_int()[1]
    previous = r1[(r1.season == "jun_nov") & (r1.metric == name)]
    rows.append({"metric": name, "r2_slope_per_decade": fit.params[1] * 10, "r2_ci_low": lo * 10, "r2_ci_high": hi * 10, "r2_p": fit.pvalues[1],
                 "r1_slope_per_decade": float(previous.slope_per_decade.iloc[0]) if len(previous) else np.nan})
table = pd.DataFrame(rows)
table.to_csv(out / "pi_trends_r1_r2.csv", index=False)
pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:.3f}")
print(table.to_string(index=False))
