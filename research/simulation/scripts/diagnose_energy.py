"""Diagnose air-sea energy exchange and outflow temperature from RE87 output fields.

Usage: python -I diagnose_energy.py <simulation-dir> <output-csv> <case> [<case> ...]
Uses one-day means saved every two days; files 04 to 06 (days 8, 10, 12) are averaged after the storm has matured.

Layout: tconNN, pconNN and qconNN have one row per radius on the full grid. vconNN and uconNN have one
row per height on the plotting grid. The enthalpy flux per unit density follows the model form
C_k |V| (k_s* - k_a), with C_k = min(CE + CD1 |V|, CKCAP), split into sensible and latent parts.
k_a is moist static energy at the lowest model level, the definition used by Done et al. (2022).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sim = Path(sys.argv[1])
sys.path.insert(0, str(sim / "scripts"))
import soundings as sd  # noqa: E402

out_csv = Path(sys.argv[2])
cases = sys.argv[3:]
CP, LV, G = 1005.7, 2.501e6, 9.81
NUMBERS = ("04", "05", "06")


def params(case_dir):
    values = {}
    for row in (case_dir / "hurr.in").read_text(encoding="latin-1").splitlines():
        parts = row.split()
        if len(parts) >= 3:
            values[parts[2]] = parts[0]
    return values


def field(output, name, number):
    return np.loadtxt(output / f"{name}{number}.out")


def rsat_sea(sst_c, p_hpa):
    e = sd.es(np.asarray(sst_c, dtype=float))
    return 0.622 * e / (p_hpa - e)


rows = []
for case in cases:
    case_dir = sim / "runs" / case
    output = case_dir / "output"
    p = params(case_dir)
    sst_c = sd.read(case_dir / "s.in").sst
    ce, cd1, ckcap, vcap = float(p["CE"]) * 1e-3, float(p["CD1"]) * 1e-5, float(p["CKCAP"]) * 1e-3, float(p["VCAP"])
    pdep = p["PDEP"].lower() == "y"
    r_km = np.loadtxt(output / "rgraph.out").ravel()
    z_km = np.loadtxt(output / "zgraph.out").ravel()
    records = []
    for number in NUMBERS:
        if not (output / f"vcon{number}.out").exists():
            continue
        v = field(output, "vcon", number)
        u = field(output, "ucon", number)
        t_full = field(output, "tcon", number)
        p_full = field(output, "pcon", number)
        q_full = field(output, "qcon", number)
        nr = len(r_km)
        t1, p1, q1 = t_full[:nr, 0], p_full[:nr, 0], q_full[:nr, 0] / 1000.0
        speed = np.sqrt(v[0, :nr] ** 2 + u[0, :nr] ** 2)
        ps = p1 if pdep else np.full(nr, float(p_full[-1, 0]))
        qs = rsat_sea(sst_c, ps)
        ck = np.minimum(ce + cd1 * speed, ckcap)
        # Dry static energy difference, so the lowest level's height is not counted as a sensible heat source.
        # zgraph.out starts at 0; the lowest prognostic level sits half a grid step above the surface.
        sensible = CP * (sst_c + 273.15 - t1) - G * 0.5 * (z_km[1] - z_km[0]) * 1000.0
        latent = LV * (qs - q1)
        flux_factor = ck * np.minimum(speed, vcap)
        rmw_index = int(np.argmax(v[0, :nr]))
        core = (r_km >= r_km[rmw_index] - 15) & (r_km <= r_km[rmw_index] + 15)
        outer = (r_km >= 400) & (r_km <= 800)
        inner = r_km <= 300
        ring = r_km[inner]
        total_s = np.trapezoid(flux_factor[inner] * sensible[inner] * ring, ring)
        total_l = np.trapezoid(flux_factor[inner] * latent[inner] * ring, ring)
        # Outflow temperature: temperature at the level of strongest mean radial outflow, 100 to 300 km.
        band = (r_km >= 100) & (r_km <= 300)
        profile = u[:, band].mean(axis=1)
        level = int(np.argmax(profile))
        t_out = float(t_full[:nr, level][band].mean())
        records.append({
            "core_dk_kj": float((sensible[core] + latent[core]).mean()) / 1000.0, "core_sensible_kj": float(sensible[core].mean()) / 1000.0,
            "core_latent_kj": float(latent[core].mean()) / 1000.0, "core_speed": float(speed[core].mean()),
            "outer_dk_kj": float((sensible[outer] + latent[outer]).mean()) / 1000.0, "outer_sensible_kj": float(sensible[outer].mean()) / 1000.0,
            "outer_latent_kj": float(latent[outer].mean()) / 1000.0, "outer_sst_minus_t": float((sst_c + 273.15 - t1[outer]).mean()),
            "outer_rh": float((q1[outer] / rsat_sea(t1[outer] - 273.15, p1[outer])).mean()),
            # Same quantity as the model's sensible flux term (L464, L1482), away from the storm.
            "outer_tsurf_minus_theta": float((((sst_c + 273.0) * (1000.0 / float(p["PDS"])) ** 0.286) - t1[outer] * (1000.0 / p1[outer]) ** 0.286).mean()),
            "flux_sensible_integral": float(total_s), "flux_latent_integral": float(total_l),
            "rmw_km": float(r_km[rmw_index]), "outflow_height_km": float(z_km[level]) if level < len(z_km) else np.nan,
            "outflow_t_k": t_out, "efficiency": (sst_c + 273.15 - t_out) / t_out,
        })
    mean = pd.DataFrame(records).mean(numeric_only=True).to_dict()
    mean["sensible_share"] = mean["flux_sensible_integral"] / (mean["flux_sensible_integral"] + mean["flux_latent_integral"])
    rows.append({"case": case, "sst_c": sst_c, **mean})

table = pd.DataFrame(rows)
table.to_csv(out_csv, index=False)
pd.set_option("display.width", 250, "display.max_columns", 30, "display.float_format", lambda v: f"{v:.3g}")
print(table.drop(columns=["flux_sensible_integral", "flux_latent_integral"]).to_string(index=False))
