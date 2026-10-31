"""Air-sea enthalpy disequilibrium of each initial environment, free of any storm feedback.

Usage: python -I initial_disequilibrium.py <simulation-dir> <output-csv> <case> [<case> ...]
Disequilibrium is the saturation moist static energy at the sea surface minus moist static energy at the
lowest model level (z = 156 m), the definition in Done et al. (2022, Table 3). The level's values follow
the model's initialization: theta and mixing ratio interpolated in the file's height coordinate, with
pressure from hydrostatic balance starting at the ambient surface pressure of 1013 hPa.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sim = Path(sys.argv[1])
sys.path.insert(0, str(sim / "scripts"))
import soundings as sd  # noqa: E402

out, cases = Path(sys.argv[2]), sys.argv[3:]
CP, LV, G, RD, KAPPA, PS, Z1 = 1005.7, 2.501e6, 9.81, 287.04, 0.286, 1013.0, 156.25


def lowest_level(s):
    t = s.t + 273.15
    q = s.r / 1000.0
    z = [0.0]
    for i in range(1, len(s.p)):
        tv = 0.5 * (t[i - 1] * (1 + 0.61 * q[i - 1]) + t[i] * (1 + 0.61 * q[i]))
        z.append(z[-1] + RD * tv / (G * 0.5 * (s.p[i - 1] + s.p[i])) * (s.p[i - 1] - s.p[i]))
    z = np.array(z)
    theta = np.interp(Z1, z, t * (1000.0 / s.p) ** KAPPA)
    r1 = np.interp(Z1, z, q)
    exner = (PS / 1000.0) ** KAPPA - G * Z1 / (CP * theta * (1 + 0.61 * r1))
    return theta * exner, r1, 1000.0 * exner ** (1 / KAPPA)


rows = []
for case in cases:
    s = sd.read(sim / "runs" / case / "s.in")
    t1, r1, p1 = lowest_level(s)
    e = float(sd.es(np.array(s.sst)))
    qs = 0.622 * e / (PS - e)
    sensible = CP * (s.sst + 273.15 - t1) - G * Z1
    latent = LV * (qs - r1)
    rows.append({"case": case, "sst_c": s.sst, "t1_c": t1 - 273.15, "r1_gkg": r1 * 1000, "p1_hpa": p1,
                 "init_sensible_kj": sensible / 1000, "init_latent_kj": latent / 1000, "init_dk_kj": (sensible + latent) / 1000})
table = pd.DataFrame(rows)
table.to_csv(out, index=False)
print(table.round(2).to_string(index=False))
