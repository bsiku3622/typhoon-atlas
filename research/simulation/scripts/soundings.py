"""Read, modify and write RE87 sounding files (s.in format).

Columns are pressure (hPa), temperature (C) and mixing ratio (g/kg). The model reads only those three
and skips exactly the header layout kept here, so the first seven lines are preserved verbatim except
for the SST value.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Sounding:
    sst: float
    p: np.ndarray
    t: np.ndarray
    r: np.ndarray
    header: list
    extra: list


def read(path) -> Sounding:
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    p, t, r, extra = [], [], [], []
    for line in lines[7:]:
        parts = line.split()
        if len(parts) < 3:
            continue
        p.append(float(parts[0]))
        t.append(float(parts[1]))
        r.append(float(parts[2]))
        extra.append(parts[3:])
    return Sounding(float(lines[2].split()[0]), np.array(p), np.array(t), np.array(r), lines[:7], extra)


def write(snd: Sounding, path) -> None:
    header = list(snd.header)
    header[2] = f"             {snd.sst:.2f}"
    rows = []
    for i in range(len(snd.p)):
        tail = "   ".join(snd.extra[i])
        rows.append(f"  {snd.p[i]:7.1f}  {snd.t[i]:8.3f}   {snd.r[i]:10.6f}     {tail}".rstrip())
    Path(path).write_text("\n".join(header + rows) + "\n", encoding="latin-1", newline="\n")


def es(t_c):
    """Saturation vapor pressure over liquid (hPa), Bolton 1980."""
    return 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))


def rsat(p, t_c):
    """Saturation mixing ratio (g/kg), limited so that it stays finite at low pressure."""
    e = np.minimum(es(t_c), 0.5 * p)
    return 622.0 * e / (p - e)


def rh(snd: Sounding):
    return snd.r / rsat(snd.p, snd.t)


def replace(snd: Sounding, **changes) -> Sounding:
    values = {k: getattr(snd, k) for k in ("sst", "p", "t", "r", "header", "extra")}
    values.update(changes)
    return Sounding(**values)


def uniform_shift(base: Sounding, dt: float, humidity: str) -> Sounding:
    """Shift temperature by dt at fixed pressure. humidity is 'rh' to preserve RH or 'q' to keep mixing ratio."""
    t = base.t + dt
    r = base.r.copy() if humidity == "q" else rh(base) * rsat(base.p, t)
    return replace(base, t=t, r=r)


def topheavy_weight(s24: Sounding, s28: Sounding, s32: Sounding, dt: float):
    """Vertical shape from the bundled family, scaled to 1 at the lowest level.

    Warming uses the 28 to 32 C pair and cooling the 24 to 28 C pair, so only the temperature shape is
    borrowed. Humidity is handled separately because the family also changes mid-level humidity.
    """
    low, high = (s28, s32) if dt >= 0 else (s24, s28)
    difference = high.t - low.t
    return difference / difference[0]


def topheavy_shift(base: Sounding, s24: Sounding, s28: Sounding, s32: Sounding, dt: float) -> Sounding:
    """Apply dt with the family's vertical shape and preserve the base RH."""
    if not np.array_equal(base.p, s28.p):
        raise ValueError("base sounding must share the family's pressure levels")
    t = base.t + dt * topheavy_weight(s24, s28, s32, dt)
    return replace(base, t=t, r=rh(base) * rsat(base.p, t))


def family_state(s24: Sounding, s28: Sounding, s32: Sounding, dt: float) -> Sounding:
    """Interpolate the bundled sounding family linearly at fixed pressure to SST 28 + dt."""
    for other in (s24, s32):
        if not np.array_equal(other.p, s28.p):
            raise ValueError("bundled soundings do not share pressure levels")
    low, high, frac = (s28, s32, dt / 4.0) if dt >= 0 else (s24, s28, (dt + 4.0) / 4.0)
    return replace(
        s28,
        t=low.t + frac * (high.t - low.t),
        r=low.r + frac * (high.r - low.r),
        sst=s28.sst + dt,
    )
