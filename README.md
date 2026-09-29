# Cyclone Atlas

A Paper UI viewer for global tropical cyclone tracks, climate context, and broad air-mass conditions since 1980.

## Data sources and selection

### Tropical cyclones — NOAA IBTrACS v04r01

- Source: [NOAA NCEI International Best Track Archive for Climate Stewardship (IBTrACS)](https://www.ncei.noaa.gov/products/international-best-track-archive)
- Downloaded source: global CSV since 1980, saved in the user's dated Codex data folder.
- App extract: `public/data/ibtracs_global_since1980.csv` (10 fields retained: SID, season, basin, name, timestamp, nature, latitude, longitude, WMO wind, and WMO pressure).
- Current extract: 309,724 track observations and 4,991 unique SIDs in seasons 1980–2026.
- Selection reason: one global best-track archive allows basin-to-basin comparisons with stable storm IDs and common field names.
- The archive includes tropical depressions and other tracked systems, not only named tropical cyclones. The 2026 season is partial and recent tracks may change. Wind uses `WMO_WIND` in knots; reporting agencies use different averaging periods, which are not normalized here.

### Near-surface temperature and humidity — Met Office HadISDH.blend

- Source: [Met Office HadISDH](https://www.metoffice.gov.uk/hadobs/hadisdh/), `blend` release 1.5.1.2024f.
- Downloaded fields: 2 m air temperature and relative humidity, actual monthly values, monthly anomalies, and 1991–2020 monthly climatologies. Raw NetCDF files are retained under `~/Bufs/Codex Files/2026-09-28/climate/hadisdh-blend-2024/`.
- App extracts: `public/data/hadisdh_global_monthly.csv` (1973–2024) and `public/data/hadisdh_global_normals.csv` (1991–2020 monthly normals).
- Source resolution is 5° x 5°. The viewer samples every other source cell for a 10° display grid. It does not interpolate missing cells.
- Selection reason: HadISDH provides observed, quality-controlled, homogenized temperature and humidity on a shared global grid, with a fixed reference period and uncertainty fields. The 2024 release is the latest complete version; the 2025 release is provisional and its producer warns of reduced spatial coverage.
- The displayed global trend uses area-weighted monthly anomaly averages across observed cells. Coverage is uneven and should be considered when interpreting a global mean.

### Upper-air context for air-mass analysis — NOAA NCEP/NCAR Reanalysis 1

- Source: the pressure-level monthly long-term means in the same [NOAA PSL archive](https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html).
- Downloaded fields: 850 hPa temperature and relative humidity, 850 hPa u/v wind, and 500 hPa geopotential height; 1991–2020 monthly climatology. Raw NetCDF files are retained under `~/Bufs/Codex Files/2026-09-28/climate/ncep-ncar-airmass/`.
- App extract: `public/data/ncep_global_airmass_normals.csv`, sampled on the same 10° global grid.
- Selection reason: temperature and moisture describe air-mass thermodynamic conditions, while winds and 500 hPa height add circulation context. These fields support inspection of the seasonal background environment.
- The map's four-category “air-mass conditions” layer is a simple exploratory classification from the signs of local 2 m temperature and humidity anomalies (warm/moist, warm/dry, cool/moist, cool/dry). It is not a formal air-mass-origin or trajectory classification. The 850/500 hPa fields are shown as climatological context, not a time-varying air-mass tracking product.

## Rebuild data extracts

The source files are downloaded and the analysis-ready CSVs are generated with:

```sh
python3 -m pip install -r scripts/requirements-data.txt
python3 scripts/prepare_ibtracs_global.py
python3 scripts/prepare_hadisdh.py
python3 scripts/download_ncep_airmass.py
```

The cyclone source CSV is expected at `~/Bufs/Codex Files/2026-09-28/ibtracs/ibtracs.since1980.list.v04r01.csv`. The climate script downloads raw NetCDF files to the dated `Bufs` folder and writes compact global-grid CSVs under `public/data/`.

## Run

```sh
pnpm install
pnpm dev
```

Use the basin selector to compare the seven IBTrACS basins. Filter storms by year or name, select a track, adjust the wind threshold, or explore global monthly temperature, humidity, and upper-air conditions.

## Build

```sh
pnpm build
```
