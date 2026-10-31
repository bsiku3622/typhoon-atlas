# Research: temperature sensitivity of western North Pacific typhoons

This folder holds the term project behind Cyclone Atlas: how potential intensity (PI) and simulated typhoon intensity respond when the atmosphere warms with sea surface temperature (SST) held fixed, and when the sea warms too. The full write-up, in Korean, is [`results_ko.md`](results_ko.md), and progress is shown at [atlas.bsiku.dev/#research](https://atlas.bsiku.dev/#research).

These are coursework records and have not been peer reviewed. They are conditional sensitivities of an axisymmetric idealized model, not forecasts for any future year.

## Main findings

- Warming only the atmosphere by 2 K weakens the simulated storm by 21.7%. Warming the sea too strengthens it by about 4.1% per kelvin. Changing physics settings or grid spacing keeps the sign and rough size (−21 to −26%, +5 to +10% at T+2).
- Holding relative humidity or specific humidity fixed makes no detectable difference on the warm side.
- Intensity across experiments follows the CAPE of a parcel saturated at the sea surface (r² 0.87) better than the initial air-sea enthalpy difference (r² 0.69). This reading came after seeing the results and was not tested separately.
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
```

A 15-day run takes about 10 minutes on one core of a Ryzen 7 7800X3D, and repeating a run reproduces its output exactly. Grid sensitivity runs change `M` and `N` in the main program and in `DIFFUSE`. The double-resolution run also needs `TVRDIF(100)` in subroutine `CAPE` enlarged, because it overflows at 160 levels.

Two choices differ from the shipped inputs:

- `TMIN` is 133 K, the value the user guide describes as never invoked. The shipped first column has 210 K, which clips the stratosphere. With 133 K, the Emanuel and Rotunno (2011) settings give 65.6 m/s against their PI of 67.9 m/s.
- The base state is a neutral sounding for a 28 °C sea, rebuilt with the construction of the bundled `s.in`. The bundled 28 °C sounding drifts strongly in this model, warming the outer 200 hPa level by 9.8 K in 15 days.

## Reproduce the reanalysis analysis

`pi/download_inputs.py` and `pi/download_r2.py` fetch the inputs from NOAA PSL without an account. Then run `pi/compute_pi_wnp.py`, `pi/compute_pi_r2.py`, `pi/analyze_pi.py` and `pi/analyze_enso.py`. netCDF4 cannot create files under a non-ASCII path on Windows. The R1 specific humidity file holds infinite values at 600–300 hPa for 2023-03; those are replaced with that month's 1991–2020 mean.
