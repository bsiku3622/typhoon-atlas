"""Download NOAA PSL pressure-level normals used for air-mass context."""

from __future__ import annotations

import csv
import subprocess
import time
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path.home() / "Bufs/Codex Files/2026-09-28/climate/ncep-ncar-airmass"
DATA_URL = "https://psl.noaa.gov/thredds/fileServer/Datasets/ncep.reanalysis/Monthlies/pressure"
FIELDS = {
    "temperature_850_c": ("air.mon.ltm.1991-2020.nc", "air", 850, 9_709_277),
    "relative_humidity_850_pct": ("rhum.mon.ltm.1991-2020.nc", "rhum", 850, 4_976_284),
    "geopotential_height_500_m": ("hgt.mon.ltm.1991-2020.nc", "hgt", 500, 8_874_993),
    "u_wind_850_ms": ("uwnd.mon.ltm.1991-2020.nc", "uwnd", 850, 10_927_383),
    "v_wind_850_ms": ("vwnd.mon.ltm.1991-2020.nc", "vwnd", 850, 11_405_646),
}
LATITUDES = list(range(70, -61, -10))
LONGITUDES = list(range(0, 360, 10))
OUTPUT = ROOT / "public/data/ncep_global_airmass_normals.csv"


def download(filename: str, size: int) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / filename
    if path.exists() and path.stat().st_size == size:
        return path
    partial = path.with_suffix(path.suffix + ".partial")
    start = partial.stat().st_size if partial.exists() else 0
    if start >= size:
        partial.replace(path)
        return path
    subprocess.run([
        "curl", "--http1.1", "-fLsS", "--retry-all-errors", "--retry", "5",
        "--retry-delay", "45", "--retry-max-time", "300", "-C", "-",
        "-o", str(partial), f"{DATA_URL}/{filename}",
    ], check=True)
    if partial.stat().st_size != size:
        raise RuntimeError(f"Incomplete NOAA download for {filename}: {partial.stat().st_size} bytes")
    partial.replace(path)
    time.sleep(15)
    return path


def main() -> None:
    datasets: dict[str, Dataset] = {}
    try:
        for key, (filename, _, _, size) in FIELDS.items():
            path = download(filename, size)
            datasets[key] = Dataset(path)
            print(f"Loaded {filename}", flush=True)

        reference = next(iter(datasets.values()))
        latitudes = np.asarray(reference.variables["lat"][:])
        longitudes = np.asarray(reference.variables["lon"][:])
        lat_indices = [int(np.abs(latitudes - lat).argmin()) for lat in LATITUDES]
        lon_indices = [int(np.abs(((longitudes - lon + 180) % 360) - 180).argmin()) for lon in LONGITUDES]
        fields: dict[str, list[np.ndarray]] = {}
        for key, (_, variable_name, pressure_level, _) in FIELDS.items():
            dataset = datasets[key]
            levels = np.asarray(dataset.variables["level"][:])
            level_index = int(np.abs(levels - pressure_level).argmin())
            variable = dataset.variables[variable_name]
            fields[key] = []
            for month in range(12):
                source = np.asarray(variable[month, level_index, :, :], dtype=float)
                fields[key].append(source[np.ix_(lat_indices, lon_indices)])
        with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["month", "grid_id", "lat", "lon", *FIELDS.keys()])
            count = 0
            for month in range(12):
                for lat_index, latitude in enumerate(LATITUDES):
                    for lon_index, longitude in enumerate(LONGITUDES):
                        values = [fields[key][month][lat_index, lon_index] for key in FIELDS]
                        if not all(np.isfinite(value) and abs(value) < 1e20 for value in values):
                            continue
                        grid_id = lat_index * len(LONGITUDES) + lon_index
                        writer.writerow([month + 1, grid_id, latitude, longitude, *(f"{value:.3f}" for value in values)])
                        count += 1
        print(f"Wrote {count:,} NCEP pressure-level normal records")
        print(f"Raw NOAA files retained under {RAW_DIR}")
    finally:
        for dataset in datasets.values():
            dataset.close()


if __name__ == "__main__":
    main()
