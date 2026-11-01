"""Export dense-output runs to compact files for the Cyclone Atlas simulation viewer.

Usage: python -I export_viz.py <simulation-dir> <output-dir>
Each case produces <id>.bin holding, in order:
  Int16 little-endian: frames x 3 x nPlan  (lowest-level v, lowest-level u, column condensate)
  Uint8:               frames x 5 x nz x nr (v, u, w, condensate, temperature anomaly)
Scales are stored in index.json. Frames are six-hourly means; frame k covers hours 6(k-1) to 6k.
Temperature anomaly is relative to the same height at the outer edge of the plotting grid (1000 km).
Column condensate uses an assumed density profile and is only used to shade the top-down view.
"""
import json
import sys
from pathlib import Path

import numpy as np

sim, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

CASES = [
    ("t0", "v_t0", "기준", "SST 28°C", 0, 28),
    ("warm2", "v_ad_p2_sstup", "바다와 대기 +2 K", "온난화에 가까운 조건, SST 30°C", 2, 30),
    ("cool2", "v_ad_m2_sstup", "바다와 대기 −2 K", "SST 26°C", -2, 26),
    ("air2", "v_ad_p2_sstfix", "대기만 +2 K", "SST 28°C 고정, 온난화 시나리오가 아닌 민감도 실험", 2, 28),
    ("airm2", "v_ad_m2_sstfix", "대기만 −2 K", "SST 28°C 고정, 민감도 실험", -2, 28),
]
RANGES = {"v": (-20.0, 130.0), "u": (-60.0, 60.0), "w": (-10.0, 30.0), "q": (0.0, 8.0), "t": (-20.0, 20.0)}
SECTION_RMAX, SECTION_ZMAX, ZSTEP = 200.0, 20.0, 2
PLAN_RMAX = 600.0
PLAN_SCALE = {"v": 0.05, "u": 0.05, "c": 0.01}


def load(output, name, number):
    return np.loadtxt(output / f"{name}{number:02d}.out")


index = {"cases": [], "fields": {k: {"min": a, "max": b} for k, (a, b) in RANGES.items()}, "planScale": PLAN_SCALE}
grid_written = False
for cid, run, label, note, dt, sst in CASES:
    output = sim / "runs" / run / "output"
    numbers = sorted(int(p.stem[4:]) for p in output.glob("vcon[0-9][0-9].out"))
    if not numbers:
        raise SystemExit(f"{run} has no output yet")
    if numbers != list(range(1, len(numbers) + 1)):
        raise SystemExit(f"{run}: frames are not contiguous")
    r_all = np.loadtxt(output / "rgraph.out").ravel()
    z_all = np.loadtxt(output / "zgraph.out").ravel()
    dz = z_all[1] - z_all[0]
    # Prognostic values sit half a grid step above the plotted coordinate in height.
    z_mid = z_all + 0.5 * dz
    r_sel = np.where(r_all <= SECTION_RMAX)[0]
    z_sel = np.where(z_mid <= SECTION_ZMAX)[0][::ZSTEP]
    p_sel = np.where(r_all <= PLAN_RMAX)[0]
    density = 1.15 * np.exp(-z_mid / 8.0)
    plan, section = [], []
    for k in numbers:
        v, u, w = load(output, "vcon", k), load(output, "ucon", k), load(output, "wcon", k)
        q, t = load(output, "liqcon", k), load(output, "tfcon", k)
        nz = min(len(z_mid), v.shape[0])
        column = (q[:nz, :] * density[:nz, None]).sum(axis=0) * dz  # g/kg * kg/m3 * km = kg/m2
        anomaly = t - t[:, [-1]]
        plan.append(np.stack([v[0, p_sel] / PLAN_SCALE["v"], u[0, p_sel] / PLAN_SCALE["u"], column[p_sel] / PLAN_SCALE["c"]]))
        fields = []
        for key, values in (("v", v), ("u", u), ("w", w), ("q", q), ("t", anomaly)):
            low, high = RANGES[key]
            scaled = np.clip((values[np.ix_(z_sel, r_sel)] - low) / (high - low), 0, 1) * 255
            fields.append(np.round(scaled).astype(np.uint8))
        section.append(np.stack(fields))
    plan = np.clip(np.round(np.array(plan)), -32768, 32767).astype("<i2")
    section = np.array(section, dtype=np.uint8)
    (out / f"{cid}.bin").write_bytes(plan.tobytes() + section.tobytes())

    series = np.loadtxt(output / "time.out")
    keep = series[::3]
    index["cases"].append({
        "id": cid, "label": label, "note": note, "dT": dt, "sst": sst, "pi": round(float(series[0, 6]), 1),
        "hours": [int(round(h)) for h in keep[:, 0]], "vmax": [round(float(x), 1) for x in keep[:, 1]],
        "pmin": [round(float(x), 1) for x in keep[:, 4]], "rmw": [round(float(x), 1) for x in keep[:, 5]],
    })
    if not grid_written:
        index["r"] = [round(float(x), 3) for x in r_all[r_sel]]
        index["z"] = [round(float(x), 3) for x in z_mid[z_sel]]
        index["rPlan"] = [round(float(x), 3) for x in r_all[p_sel]]
        index["frames"] = len(numbers)
        index["frameHours"] = 6
        grid_written = True
    if len(numbers) != index["frames"]:
        raise SystemExit(f"{run}: {len(numbers)} frames, expected {index['frames']}")
    print(cid, "frames", len(numbers), "bytes", (out / f"{cid}.bin").stat().st_size, "q max", round(float(max(load(output, 'liqcon', k).max() for k in numbers[-6:])), 2))

(out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
print("index", (out / "index.json").stat().st_size, "shapes r", len(index["r"]), "z", len(index["z"]), "plan", len(index["rPlan"]))
