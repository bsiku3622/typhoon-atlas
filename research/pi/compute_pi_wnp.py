"""Compute monthly potential intensity over the western North Pacific, 1980-2024.

Usage: python -I compute_pi_wnp.py <raw-dir> <output-dir>
Inputs are NCEP/NCAR Reanalysis 1 monthly T, q and SLP plus ERSST v5. Three versions are produced:
  actual   all fields vary
  sst_only SST varies, atmosphere and SLP stay at the 1991-2020 monthly climatology
  atm_only atmosphere and SLP vary, SST stays at the 1991-2020 monthly climatology
tcpyPI defaults follow Gilford (2021): CKCD 0.9, pseudo-free reversible ascent flag 0, dissipative
heating on, V_reduc 0.8. Specific humidity above 300 hPa does not exist in R1 and is set to zero.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import xarray as xr
from tcpyPI import pi

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
PERIOD = ("1980-01-01", "2024-12-31")
LAT, LON = slice(30, 5), slice(120, 180)
PTOP = 50.0


def load():
    air = xr.open_dataset(raw / "air.mon.mean.nc")["air"]
    shum = xr.open_dataset(raw / "shum.mon.mean.nc")["shum"]
    slp = xr.open_dataset(raw / "slp.mon.mean.nc")["slp"]
    sst = xr.open_dataset(raw / "sst.mnmean.nc")["sst"]
    air = air.sel(time=slice(*PERIOD), lat=LAT, lon=LON, level=slice(1000, PTOP)).load()
    shum = shum.sel(time=slice(*PERIOD), lat=LAT, lon=LON).load()
    # The R1 file holds +inf at 600-300 hPa over the whole box for 2023-03. Use that month's 1991-2020 mean.
    bad = ~np.isfinite(shum)
    print(f"non-finite humidity values replaced by climatology: {int(bad.sum())}", flush=True)
    normal = shum.where(~bad).sel(time=slice("1991-01-01", "2020-12-31")).groupby("time.month").mean()
    shum = shum.where(~bad).groupby("time.month").fillna(normal).drop_vars("month", errors="ignore")
    if int((~np.isfinite(shum)).sum()):
        raise SystemExit("humidity still has non-finite values")
    slp =slp.sel(time=slice(*PERIOD), lat=LAT, lon=LON).load()
    sst = sst.sel(time=slice(*PERIOD)).sortby("lat")
    sst = sst.interp(lat=air.lat, lon=air.lon).load()
    meta = {
        "air_units": str(air.attrs.get("units")), "shum_units": str(shum.attrs.get("units")),
        "slp_units": str(slp.attrs.get("units")), "sst_units": str(sst.attrs.get("units")),
        "levels": [float(v) for v in air.level.values], "shum_levels": [float(v) for v in shum.level.values],
        "n_months": int(air.sizes["time"]), "lat": [float(v) for v in air.lat.values], "lon": [float(v) for v in air.lon.values],
    }
    return air, shum, slp, sst, meta


def mixing_ratio(shum, levels):
    """Convert specific humidity (g/kg) to mixing ratio (g/kg) on the temperature levels, zero aloft."""
    q = shum.reindex(level=levels).fillna(0.0).transpose("time", "level", "lat", "lon").values / 1000.0
    return 1000.0 * q / (1.0 - q)


def climatology(values, months):
    base = np.array([np.nanmean(values[(months == m) & BASE_MASK], axis=0) for m in range(1, 13)])
    return base[months - 1]


def run(sst, slp, t, r, levels):
    nt, ny, nx = sst.shape
    vmax = np.full((nt, ny, nx), np.nan)
    pmin = vmax.copy()
    outflow = vmax.copy()
    for it in range(nt):
        for iy in range(ny):
            for ix in range(nx):
                if not np.isfinite(sst[it, iy, ix]):
                    continue
                v, p, flag, to, _ = pi(
                    float(sst[it, iy, ix]), float(slp[it, iy, ix]), levels, t[it, :, iy, ix], r[it, :, iy, ix],
                    CKCD=0.9, ascent_flag=0, diss_flag=1, V_reduc=0.8, ptop=PTOP, miss_handle=1,
                )
                if flag == 1:
                    vmax[it, iy, ix], pmin[it, iy, ix], outflow[it, iy, ix] = v, p, to
    return vmax, pmin, outflow


air, shum, slp, sst, meta = load()
print(json.dumps({k: v for k, v in meta.items() if k not in ("lat", "lon")}), flush=True)
levels = air.level.values.astype(float)
if levels[0] < levels[-1]:
    raise SystemExit("levels must run from the surface upward")
times = air.time.values
months = air["time.month"].values
years = air["time.year"].values
BASE_MASK = (years >= 1991) & (years <= 2020)

t_actual = air.transpose("time", "level", "lat", "lon").values
r_actual = mixing_ratio(shum, levels)
sst_actual = sst.transpose("time", "lat", "lon").values
slp_actual = slp.transpose("time", "lat", "lon").values
t_clim, r_clim = climatology(t_actual, months), climatology(r_actual, months)
sst_clim, slp_clim = climatology(sst_actual, months), climatology(slp_actual, months)
# Keep the ocean mask identical across versions.
sst_clim = np.where(np.isfinite(sst_actual), sst_clim, np.nan)

versions = {
    "actual": (sst_actual, slp_actual, t_actual, r_actual),
    "sst_only": (sst_actual, slp_clim, t_clim, r_clim),
    "atm_only": (sst_clim, slp_actual, t_actual, r_actual),
}
data = {}
for name, args in versions.items():
    start = time.time()
    v, p, to = run(*args, levels)
    data[f"pi_{name}"] = (("time", "lat", "lon"), v)
    data[f"pmin_{name}"] = (("time", "lat", "lon"), p)
    data[f"outflow_{name}"] = (("time", "lat", "lon"), to)
    print(f"{name}: valid {np.isfinite(v).sum()} of {np.isfinite(args[0]).sum()} ocean profiles, {time.time() - start:.0f}s", flush=True)

data["sst"] = (("time", "lat", "lon"), sst_actual)
data["t1000"] = (("time", "lat", "lon"), t_actual[:, 0])
for level in (850, 500, 200):
    data[f"t{level}"] = (("time", "lat", "lon"), t_actual[:, int(np.argmin(np.abs(levels - level)))])
data["r1000"] = (("time", "lat", "lon"), r_actual[:, 0])
ds = xr.Dataset(data, coords={"time": times, "lat": air.lat.values, "lon": air.lon.values})
ds.attrs.update({"source": "NCEP/NCAR Reanalysis 1 and ERSST v5 through NOAA PSL", "pi": "tcpyPI 1.4.1, CKCD 0.9, ascent 0, diss 1, V_reduc 0.8"})
# netCDF4 cannot create files under a non-ASCII path on Windows, so write beside the raw data first.
scratch = raw.parent / "pi_wnp_monthly.nc"
ds.to_netcdf(scratch)
shutil.copyfile(scratch, out / "pi_wnp_monthly.nc")
(out / "pi_inputs_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("saved", out / "pi_wnp_monthly.nc", flush=True)
