"""Compare candidate temperature perturbations before running the model.

Usage: python design_check.py <model-dir> <output-csv>
For each candidate it reports potential intensity from tcpyPI, parcel CAPE of the lowest level, the
maximum RH and the sea-air temperature gap. A surface parcel that is far more buoyant than the base
state means the sounding is conditionally unstable, which the RE87 guide discourages.
"""
import csv
import sys
from pathlib import Path

import numpy as np
from tcpyPI import cape, pi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soundings as sd  # noqa: E402

model = Path(sys.argv[1])
out = Path(sys.argv[2])
s24, s28, s32 = (sd.read(model / f"sounding_sst_{n}.in") for n in (24, 28, 32))
PS = 1013.0


def evaluate(s):
    keep = s.p >= 50.0
    p, t, r = s.p[keep], s.t[keep], s.r[keep]
    vmax, pmin, ifl, to, otl = pi(s.sst, PS, p, t, r, CKCD=1.0, ascent_flag=0, diss_flag=1, V_reduc=1.0, ptop=50, miss_handle=1)
    capea, _, _, flag = cape(t[0] + 273.15, r[0] / 1000.0, p[0], t + 273.15, r / 1000.0, p, ascent_flag=0, ptop=50, miss_handle=1)
    # Saturated parcel at sea temperature and surface pressure, the upper bound behind PI.
    rs = float(sd.rsat(np.array([PS]), np.array([s.sst]))[0])
    capes, _, _, _ = cape(s.sst + 273.15, rs / 1000.0, PS, t + 273.15, r / 1000.0, p, ascent_flag=0, ptop=50, miss_handle=1)
    rel = sd.rh(s)
    trop = s.p >= 100.0
    return dict(
        vmax_ms=float(vmax), pmin_hpa=float(pmin), ifl=int(ifl), outflow_k=float(to),
        cape_env=float(capea), cape_sat=float(capes), max_rh=float(rel[trop].max()),
        rh_1000=float(rel[0]), rh_700=float(np.interp(700, s.p[::-1], rel[::-1])),
        rh_500=float(np.interp(500, s.p[::-1], rel[::-1])), r_1000=float(s.r[0]),
        t_500=float(np.interp(500, s.p[::-1], s.t[::-1])), t_200=float(np.interp(200, s.p[::-1], s.t[::-1])),
    )


rows = []
for dt in (-2, -1, 0, 1, 2):
    uni_rh = sd.uniform_shift(s28, dt, "rh")
    uni_q = sd.uniform_shift(s28, dt, "q")
    fam = sd.family_state(s24, s28, s32, dt)
    top = sd.topheavy_shift(s28, s24, s28, s32, dt)
    cases = {
        "topheavy_RH_SSTfixed": sd.replace(top, sst=28.0),
        "topheavy_RH_SSTraised": sd.replace(top, sst=28.0 + dt),
        "uniform_RH_SSTfixed": sd.replace(uni_rh, sst=28.0),
        "uniform_RH_SSTraised": sd.replace(uni_rh, sst=28.0 + dt),
        "uniform_q_SSTfixed": sd.replace(uni_q, sst=28.0),
        "family_SSTfixed": sd.replace(fam, sst=28.0),
        "family_SSTraised": sd.replace(fam, sst=28.0 + dt),
    }
    for name, s in cases.items():
        rows.append({"design": name, "dT": dt, **evaluate(s)})

with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"{'design':24s} dT   Vmax  Pmin  ifl  To    CAPEenv CAPEsat maxRH  RH1000 RH700 RH500  r1000")
for r in rows:
    print(
        f"{r['design']:24s} {r['dT']:+d} {r['vmax_ms']:6.1f} {r['pmin_hpa']:6.1f} {r['ifl']:2d} {r['outflow_k']:6.1f} "
        f"{r['cape_env']:7.0f} {r['cape_sat']:7.0f} {r['max_rh']:5.2f} {r['rh_1000']:6.2f} {r['rh_700']:5.2f} {r['rh_500']:5.2f} {r['r_1000']:6.2f}"
    )
