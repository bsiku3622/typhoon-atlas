"""Compare the model's built-in VMAXTH with tcpyPI on the same soundings.

Usage: python -I compare_pi.py <simulation-dir> <output-csv> <case> [<case> ...]
pyPI receives the file sounding directly. A second call feeds it the profile the model passes to its own
PCMIN: values interpolated to mid-levels of the model's height grid, with z=0 at the first file level.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tcpyPI import pi

sim = Path(sys.argv[1])
sys.path.insert(0, str(sim / "scripts"))
import soundings as sd  # noqa: E402

out, cases = Path(sys.argv[2]), sys.argv[3:]
RD, G, EPSI = 287.0, 9.8, 1 / 0.622
SETTINGS = dict(CKCD=1.0, ascent_flag=0, V_reduc=1.0, ptop=50, miss_handle=1)


def grid_profile(s, nlevels=80, dz=312.5):
    t = s.t + 273.15
    q = s.r / 1000.0
    z = [0.0]
    for i in range(1, len(s.p)):
        tv1, tv2 = t[i - 1] * (1 + EPSI * q[i - 1] - q[i - 1]), t[i] * (1 + EPSI * q[i] - q[i])
        z.append(z[-1] + RD * 0.5 * (tv1 + tv2) / (G * 0.5 * (s.p[i - 1] + s.p[i])) * (s.p[i - 1] - s.p[i]))
    z = np.array(z)
    az = 0.5 * dz + dz * np.arange(nlevels)
    return np.interp(az, z, s.p), np.interp(az, z, s.t), np.interp(az, z, s.r)


rows = []
for case in cases:
    case_dir = sim / "runs" / case
    params = {r.split()[2]: r.split()[0] for r in (case_dir / "hurr.in").read_text(encoding="latin-1").splitlines() if len(r.split()) >= 3}
    diss = 1 if float(params["DISS"]) > 0 else 0
    s = sd.read(case_dir / "s.in")
    keep = s.p >= 50
    direct = pi(s.sst, 1013.0, s.p[keep], s.t[keep], s.r[keep], diss_flag=diss, **SETTINGS)
    gp, gt, gr = grid_profile(s)
    keep_grid = gp >= 50
    on_grid = pi(s.sst, 1013.0, gp[keep_grid], gt[keep_grid], gr[keep_grid], diss_flag=diss, **SETTINGS)
    vmaxth = float(np.loadtxt(case_dir / "output" / "time.out", max_rows=1)[6])
    rows.append({"case": case, "vmaxth": vmaxth, "pypi_file_levels": float(direct[0]), "pypi_model_levels": float(on_grid[0]), "to_file": float(direct[3]), "to_grid": float(on_grid[3])})
table = pd.DataFrame(rows)
table["vmaxth_over_pypi"] = table.vmaxth / table.pypi_model_levels
table.to_csv(out, index=False)
print(table.round(2).to_string(index=False))
