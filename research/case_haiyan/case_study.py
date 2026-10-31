"""Case study of Typhoon Haiyan (2013): track, intensity and the potential intensity it experienced.

Usage: python -I case_study.py <ibtracs_asia.csv> <pi_wnp_monthly.nc> <output-dir>
Selection rule: among the storms the project discussed (Haiyan, Mangkhut, Hagibis), Haiyan has the
largest JMA peak wind. PI comes from monthly means, so it describes the seasonal environment rather
than the air and sea immediately around the storm. JMA winds are 10-minute means in knots.
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
import plot_style as ps  # noqa: E402

SID = "2013306N07162"
track_path, pi_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
ps.setup()

cols = ["SID", "NAME", "ISO_TIME", "LAT", "LON", "TOKYO_WIND", "TOKYO_PRES", "TOKYO_GRADE", "USA_WIND", "NATURE", "TRACK_TYPE", "DIST2LAND", "BASIN"]
raw = pd.read_csv(track_path, usecols=cols, keep_default_na=False, dtype=str, low_memory=False)
track = raw[(raw.SID == SID) & (raw.TRACK_TYPE == "main") & (raw.BASIN == "WP")].copy()
for c in ("LAT", "LON", "TOKYO_WIND", "TOKYO_PRES", "TOKYO_GRADE", "USA_WIND", "DIST2LAND"):
    track[c] = pd.to_numeric(track[c], errors="coerce")
track["time"] = pd.to_datetime(track.ISO_TIME)
track = track.sort_values("time").reset_index(drop=True)

ds = xr.open_dataset(pi_path).load()
month = pd.Timestamp(2013, 11, 1)
pi_month = ds["pi_actual"].sel(time=month)
base = ds["pi_actual"].sel(time=(ds["time.month"] == 11) & (ds["time.year"] >= 1991) & (ds["time.year"] <= 2020)).mean("time")
sst_month = ds["sst"].sel(time=month)
sst_base = ds["sst"].sel(time=(ds["time.month"] == 11) & (ds["time.year"] >= 1991) & (ds["time.year"] <= 2020)).mean("time")

inside = track.LAT.between(5, 30) & track.LON.between(120, 180)
for name, field in (("pi_ms", pi_month), ("pi_normal_ms", base), ("sst_c", sst_month), ("sst_normal_c", sst_base)):
    track[name] = [
        float(field.sel(lat=lat, lon=lon, method="nearest", tolerance=2.5)) if ok else np.nan
        for lat, lon, ok in zip(track.LAT, track.LON, inside)
    ]
track["wind_ms"] = track.TOKYO_WIND * 0.51444
track["ratio"] = track.wind_ms / track.pi_ms
track["intensification_ms_per_24h"] = track.set_index("time")["wind_ms"].diff(8).values
track.to_csv(out / "haiyan_track.csv", index=False)

jma = track.dropna(subset=["TOKYO_WIND"])
peak = jma.loc[jma.TOKYO_WIND.idxmax()]
rate = jma.dropna(subset=["intensification_ms_per_24h"]).loc[jma.dropna(subset=["intensification_ms_per_24h"]).intensification_ms_per_24h.idxmax()]
summary = {
    "jma_records": int(len(jma)), "first_jma_time": str(jma.time.iloc[0]), "last_jma_time": str(jma.time.iloc[-1]),
    "peak_time": str(peak.time), "peak_lat": float(peak.LAT), "peak_lon": float(peak.LON),
    "peak_wind_kt": float(peak.TOKYO_WIND), "peak_wind_ms": float(peak.wind_ms), "min_pressure_hpa": float(jma.TOKYO_PRES.min()),
    "usa_peak_kt": float(track.USA_WIND.max()),
    "pi_at_peak_ms": float(peak.pi_ms), "pi_normal_at_peak_ms": float(peak.pi_normal_ms), "ratio_at_peak": float(peak.ratio),
    "sst_at_peak_c": float(peak.sst_c), "sst_normal_at_peak_c": float(peak.sst_normal_c),
    "max_24h_intensification_ms": float(rate.intensification_ms_per_24h), "max_24h_time": str(rate.time),
    "box_pi_2013_11": float(pi_month.weighted(np.cos(np.deg2rad(pi_month.lat))).mean()),
}
pd.Series(summary).to_csv(out / "haiyan_summary.csv", header=["value"])

fig, ax = plt.subplots(figsize=(8.2, 4.2))
mesh = ax.pcolormesh(pi_month.lon, pi_month.lat, pi_month, cmap="Blues", shading="nearest", vmin=40, vmax=85)
fig.colorbar(mesh, ax=ax, label="2013년 11월 월평균 PI (m/s)", pad=0.02)
ax.plot(track.LON, track.LAT, color=ps.INK2, linewidth=1.0, zorder=2)
strong = jma[jma.TOKYO_WIND >= 64]
ax.scatter(strong.LON, strong.LAT, s=14, color=ps.ORANGE, zorder=3, linewidth=0, label="JMA 64 kt 이상")
ax.scatter([peak.LON], [peak.LAT], s=70, marker="*", color=ps.INK, zorder=4, linewidth=0, label=f"최대 강도 {peak.TOKYO_WIND:.0f} kt")
ax.set_xlim(118, 170)
ax.set_ylim(4, 26)
ax.set_title("태풍 하이옌(2013)의 경로와 월평균 최대잠재강도")
ax.set_xlabel("경도 (°E)")
ax.set_ylabel("위도 (°N)")
ax.grid(False)
ax.legend(loc="upper right", frameon=True, facecolor=ps.SURFACE, edgecolor="none")
ps.save(fig, str(out / "haiyan_01_track_pi"))

series = track[track.time <= pd.Timestamp("2013-11-11")]
fig, ax = plt.subplots(figsize=(8.2, 3.6))
ax.plot(series.time, series.pi_ms, color=ps.BLUE, label="이동 경로의 월평균 PI")
ax.plot(series.time, series.wind_ms, color=ps.ORANGE, label="JMA 10분 평균 최대 풍속")
ax.set_ylabel("풍속 (m/s)")
ax.set_ylim(0, 90)
ax.set_title("하이옌의 실제 강도와 잠재 강도")
ax.legend(loc="upper left", ncols=2)
ax.xaxis.set_major_locator(mdates.DayLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
ax.set_xlabel("2013년 날짜 (UTC)")
ps.save(fig, str(out / "haiyan_02_intensity_pi"))

for key, value in summary.items():
    print(f"{key}: {value}")
daily = jma.set_index("time").resample("24h").first()[["LAT", "LON", "TOKYO_WIND", "TOKYO_PRES", "pi_ms", "ratio", "sst_c"]]
print(daily.round(2).to_string())
