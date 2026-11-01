# Research: temperature sensitivity of western North Pacific typhoons

This folder holds the term project behind Cyclone Atlas: how potential intensity (PI) and simulated typhoon intensity respond when the atmosphere warms with sea surface temperature (SST) held fixed, and when the sea warms too. The full write-up, in Korean, is [`results_ko.md`](results_ko.md), and progress is shown at [atlas.bsiku.dev/#research](https://atlas.bsiku.dev/#research).

These are coursework records and have not been peer reviewed. They are conditional sensitivities of an axisymmetric idealized model, not forecasts for any future year.

## Main findings

- When the sea and the atmosphere warm together, as they do under global warming, the simulated storm strengthens: +8.5 ± 1.3% at +2 K (95% interval) and +4.2 ± 0.2% per kelvin.
- Warming only the atmosphere by 2 K weakens the storm by 20.9 ± 1.3%. This is a sensitivity experiment that separates causes. It is not a warming scenario and does not show that warming weakens typhoons.
- Noise was measured first by running nine conditions five times each with boundary-layer offsets of ±0.01 and ±0.02 K. The standard deviation of mean intensity ranges from 0.39 to 3.30 m/s by condition. All eight changes above are distinguishable from it, but this noise is internal variability only and excludes physics uncertainty.
- Changing physics settings or grid spacing keeps the sign and changes the size (+5 to +10%, −21 to −26% at T+2). Those settings were run once per condition.
- Mean intensity with relative humidity fixed cannot be told apart from specific humidity fixed (+3.2 ± 4.0 m/s at +2 K).
- Intensity across experiments follows the CAPE of a parcel saturated at the sea surface (r² 0.88) better than the initial air-sea enthalpy difference (r² 0.71). This reading came after seeing the results and was not tested separately.
- Western North Pacific PI rose by 1.5 to 1.8 m/s per decade over 1980–2024, mostly through SST. The atmospheric contribution is negative but significant in only one of the two reanalyses.

## Contents

| Path | Contents |
| --- | --- |
| `step2-wnp-1980-2024/` | Observed-intensity statistics from JMA best tracks and HadISDH |
| `pi/` | PI calculation and analysis with NCEP/NCAR R1, NCEP/DOE R2 and ERSST v5, plus the ENSO check |
| `case_haiyan/` | Typhoon Haiyan (2013) case study |
| `simulation/scripts/` | Sounding generation, case setup, run and analysis scripts |
| `simulation/soundings/` | Input soundings for every experiment |
| `simulation/results/` | Summary tables and figures |

## Reproduce the simulations

The model is the public Rotunno–Emanuel axisymmetric code ([Zenodo 10957526](https://zenodo.org/records/10957526), CC BY 4.0), which is not redistributed here. Unzip it into `simulation/model/`, then compile `hurricane.f` unmodified:

```sh
bash simulation/scripts/build.sh
python simulation/scripts/make_experiments.py
bash simulation/scripts/run_batch.sh 7 <case> [<case> ...]
python simulation/scripts/make_repeats.py
bash simulation/scripts/run_repeats.sh
```

After the runs, write `results/run_summary_all.csv` with `analyze_runs.py`, then run `analyze_repeats.py` before `make_figures.py`.

A 15-day run takes about 10 minutes on one core of a Ryzen 7 7800X3D, and repeating a run reproduces its output exactly. Grid sensitivity runs change `M` and `N` in the main program and in `DIFFUSE`. The double-resolution run also needs `TVRDIF(100)` in subroutine `CAPE` enlarged, because it overflows at 160 levels.

Two choices differ from the shipped inputs:

- `TMIN` is 133 K, the value the user guide describes as never invoked. The shipped first column has 210 K, which clips the stratosphere. With 133 K, the Emanuel and Rotunno (2011) settings give 65.6 m/s against their PI of 67.9 m/s.
- The base state is a neutral sounding for a 28 °C sea, rebuilt with the construction of the bundled `s.in`. The bundled 28 °C sounding drifts strongly in this model, warming the outer 200 hPa level by 9.8 K in 15 days.

## Reproduce the reanalysis analysis

`pi/download_inputs.py` and `pi/download_r2.py` fetch the inputs from NOAA PSL without an account. Then run `pi/compute_pi_wnp.py`, `pi/compute_pi_r2.py`, `pi/analyze_pi.py` and `pi/analyze_enso.py`. netCDF4 cannot create files under a non-ASCII path on Windows. The R1 specific humidity file holds infinite values at 600–300 hPa for 2023-03; those are replaced with that month's 1991–2020 mean.
