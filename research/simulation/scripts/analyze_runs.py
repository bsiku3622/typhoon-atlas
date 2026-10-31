"""Summarize RE87 runs from time.out and the outer sounding.

Usage: python -I analyze_runs.py <simulation-dir> <output-csv> [<case> ...]
time.out columns: hour, Vmax (lowest-level excluded), Umin, Wmax, Pmin, Rmax, VMAXTH, Vmax at lowest level.
Winds are instantaneous grid-point tangential winds. Means use a window chosen to avoid spin-up.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sim = Path(sys.argv[1])
sys.path.insert(0, str(sim / "scripts"))
import soundings as sd  # noqa: E402

out_csv = Path(sys.argv[2])
selected = sys.argv[3:] or sorted(p.name for p in (sim / "runs").iterdir() if p.is_dir() and not p.name.startswith("_"))
COLUMNS = ["hour", "vmax", "umin", "wmax", "pmin", "rmax", "vmaxth", "vlow"]
WINDOW = (8 * 24, 15 * 24)


def outer_change(case_dir):
    start = sd.read(case_dir / "s.in")
    try:
        end = sd.read(case_dir / "output" / "s.out")
    except (OSError, ValueError, IndexError):
        return {}
    result = {}
    # Compare on pressure; s.out runs from the surface upward and uses the same layout.
    order = np.argsort(end.p)
    for level in (850, 500, 200):
        t_end = float(np.interp(level, end.p[order], end.t[order]))
        t_start = float(np.interp(level, start.p[::-1], start.t[::-1]))
        result[f"env_dt_{level}"] = t_end - t_start
    for level in (850, 700, 500):
        r_end = float(np.interp(level, end.p[order], end.r[order]))
        r_start = float(np.interp(level, start.p[::-1], start.r[::-1]))
        result[f"env_dr_{level}"] = r_end - r_start
    return result


rows = []
for case in selected:
    case_dir = sim / "runs" / case
    path = case_dir / "output" / "time.out"
    if not path.exists():
        continue
    t = pd.DataFrame(np.loadtxt(path), columns=COLUMNS)
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    run_meta = dict(line.split("=", 1) for line in (case_dir / "run_meta.txt").read_text().splitlines()) if (case_dir / "run_meta.txt").exists() else {}
    step = float(t.hour.diff().median())
    span = max(1, int(round(24 / step)))
    smooth = t.vmax.rolling(span, center=True, min_periods=span).mean()
    smooth_p = t.pmin.rolling(span, center=True, min_periods=span).mean()
    window = t[(t.hour > WINDOW[0]) & (t.hour <= WINDOW[1])]
    crossing = t.hour[smooth >= 33.0]
    half = t.hour[smooth >= 0.5 * smooth.max()]
    rows.append({
        "case": case, "note": meta.get("note", ""), "hours": t.hour.max(), "wall_seconds": run_meta.get("wall_seconds"),
        "vmaxth": t.vmaxth.iloc[0],
        "v_peak_inst": t.vmax.max(), "v_peak_24h": smooth.max(), "t_peak_24h_day": t.hour[smooth.idxmax()] / 24 if smooth.notna().any() else np.nan,
        "p_min_24h": smooth_p.min(),
        "v_mean_d8_15": window.vmax.mean(), "v_sd_d8_15": window.vmax.std(), "p_mean_d8_15": window.pmin.mean(), "p_sd_d8_15": window.pmin.std(),
        "rmw_mean_d8_15": window.rmax.mean(), "v_low_d8_15": window.vlow.mean(),
        "t_33ms_day": crossing.iloc[0] / 24 if len(crossing) else np.nan,
        "t_half_peak_day": half.iloc[0] / 24 if len(half) else np.nan,
        "v_day15": t.vmax.iloc[-5:].mean(),
        **outer_change(case_dir),
    })
summary = pd.DataFrame(rows)
summary["ratio_mean_to_vmaxth"] = summary.v_mean_d8_15 / summary.vmaxth
summary.to_csv(out_csv, index=False)
pd.set_option("display.width", 240, "display.max_columns", 40, "display.float_format", lambda v: f"{v:.2f}")
show = ["case", "wall_seconds", "vmaxth", "v_peak_24h", "t_peak_24h_day", "v_mean_d8_15", "v_sd_d8_15", "p_mean_d8_15", "rmw_mean_d8_15", "t_33ms_day", "ratio_mean_to_vmaxth", "env_dt_500", "env_dt_200", "env_dr_700"]
print(summary[[c for c in show if c in summary]].to_string(index=False))
