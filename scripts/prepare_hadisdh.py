"""Download HadISDH global temperature/humidity and export compact CSV grids."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, num2date


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path.home() / "Bufs/Codex Files/2026-09-28/climate/hadisdh-blend-2024"
DATA_URL = "https://www.metoffice.gov.uk/hadobs/hadisdh/data"
VERSION = "1.5.1.2024f"
FILES = {
    "rh": f"HadISDH.blendRH.{VERSION}_FLATgridHOMBClocalSHIPboth5by5_anoms9120.nc",
    "t": f"HadISDH.blendT.{VERSION}_FLATgridHOMBClocalSHIPboth5by5_anoms9120.nc",
}
LATITUDES = list(range(70, -61, -10))
LONGITUDES = list(range(-180, 180, 10))
MONTHLY_OUTPUT = ROOT / "public/data/hadisdh_global_monthly.csv"
NORMAL_OUTPUT = ROOT / "public/data/hadisdh_global_normals.csv"


def ensure_sources() -> dict[str, Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for key, filename in FILES.items():
        path = RAW_DIR / filename
        if not path.exists() or path.stat().st_size < 1_000_000:
            subprocess.run(["curl", "-fL", "--retry", "3", "--retry-delay", "3", "-o", str(path), f"{DATA_URL}/{filename}"], check=True)
        result[key] = path
    return result


def grid_indices(nc: Dataset) -> tuple[list[int], list[int]]:
    latitudes = np.asarray(nc.variables["latitude"][:])
    longitudes = np.asarray(nc.variables["longitude"][:])
    lat_indices = [int(np.abs(latitudes - lat).argmin()) for lat in LATITUDES]
    lon_indices = [int(np.abs(((longitudes - lon + 180) % 360) - 180).argmin()) for lon in LONGITUDES]
    return lat_indices, lon_indices


def valid_pair(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.isfinite(left) & np.isfinite(right) & (np.abs(left) < 1e20) & (np.abs(right) < 1e20)


def main() -> None:
    source_paths = ensure_sources()
    with Dataset(source_paths["t"]) as temp_nc, Dataset(source_paths["rh"]) as humidity_nc:
        lat_indices, lon_indices = grid_indices(temp_nc)
        times = temp_nc.variables["time"]
        dates = num2date(times[:], units=times.units, calendar=getattr(times, "calendar", "standard"))
        monthly_count = 0
        with MONTHLY_OUTPUT.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["year", "month", "grid_id", "lat", "lon", "temperature_c", "relative_humidity_pct", "temperature_anomaly_c", "humidity_anomaly_pct"])
            for time_index, date in enumerate(dates):
                temp = np.asarray(temp_nc.variables["t_abs"][time_index, :, :])[np.ix_(lat_indices, lon_indices)]
                rh = np.asarray(humidity_nc.variables["rh_abs"][time_index, :, :])[np.ix_(lat_indices, lon_indices)]
                temp_anomaly = np.asarray(temp_nc.variables["t_anoms"][time_index, :, :])[np.ix_(lat_indices, lon_indices)]
                rh_anomaly = np.asarray(humidity_nc.variables["rh_anoms"][time_index, :, :])[np.ix_(lat_indices, lon_indices)]
                valid = valid_pair(temp, rh) & valid_pair(temp_anomaly, rh_anomaly)
                for lat_pos, latitude in enumerate(LATITUDES):
                    for lon_pos, longitude in enumerate(LONGITUDES):
                        if not valid[lat_pos, lon_pos]:
                            continue
                        grid_id = lat_pos * len(LONGITUDES) + lon_pos
                        writer.writerow([date.year, date.month, grid_id, latitude, longitude,
                            f"{temp[lat_pos, lon_pos]:.3f}", f"{rh[lat_pos, lon_pos]:.3f}",
                            f"{temp_anomaly[lat_pos, lon_pos]:.3f}", f"{rh_anomaly[lat_pos, lon_pos]:.3f}"])
                        monthly_count += 1
        normal_count = 0
        with NORMAL_OUTPUT.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["month", "grid_id", "lat", "lon", "temperature_c", "relative_humidity_pct"])
            for month in range(12):
                temp = np.asarray(temp_nc.variables["t_clims"][month, :, :])[np.ix_(lat_indices, lon_indices)]
                rh = np.asarray(humidity_nc.variables["rh_clims"][month, :, :])[np.ix_(lat_indices, lon_indices)]
                valid = valid_pair(temp, rh)
                for lat_pos, latitude in enumerate(LATITUDES):
                    for lon_pos, longitude in enumerate(LONGITUDES):
                        if not valid[lat_pos, lon_pos]:
                            continue
                        grid_id = lat_pos * len(LONGITUDES) + lon_pos
                        writer.writerow([month + 1, grid_id, latitude, longitude, f"{temp[lat_pos, lon_pos]:.3f}", f"{rh[lat_pos, lon_pos]:.3f}"])
                        normal_count += 1
    print(f"Wrote {monthly_count:,} monthly observations and {normal_count:,} normal grid cells")
    print(f"Raw HadISDH NetCDF files retained under {RAW_DIR}")


if __name__ == "__main__":
    main()
