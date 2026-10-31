"""Build model-neutral soundings with the construction described for the RE87 s.in file.

The boundary-layer parcel follows a dry adiabat to its lifting condensation level and a pseudo-moist
adiabat above it, up to a tropopause, with an isothermal stratosphere above. Water loading is ignored
and the latent heat varies with temperature, which matches the bundled sounding closely enough to be
checked by `reproduce_s_in`.
"""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soundings as sd  # noqa: E402

RD, RV, CPD, EPS = 287.04, 461.5, 1005.7, 0.622


def _es(t_k):
    return sd.es(t_k - 273.15)


def _rs(p, t_k):
    e = np.minimum(_es(t_k), 0.5 * p)
    return EPS * e / (p - e)


def _lv(t_k):
    return 2.501e6 - 2370.0 * (t_k - 273.15)


def _dtdlnp(p, t_k):
    """Pseudo-adiabatic temperature change per unit log pressure."""
    r = _rs(p, t_k)
    lv = _lv(t_k)
    return (RD * t_k + lv * r) / (CPD + lv * lv * r * EPS / (RD * t_k * t_k))


def parcel_profile(p_levels, p0, t0_c, r0_gkg):
    """Temperature (C) of a parcel lifted from (p0, t0, r0) to each pressure level, ascending order of height."""
    r0 = r0_gkg / 1000.0
    t = t0_c + 273.15
    p = p0
    theta = t * (1000.0 / p0) ** (RD / CPD)
    out = np.zeros(len(p_levels))
    # Find the LCL by marching the dry adiabat upward.
    lcl_p = p0
    for trial in np.arange(p0, 300.0, -0.25):
        trial_t = theta * (trial / 1000.0) ** (RD / CPD)
        if _rs(trial, trial_t) <= r0:
            lcl_p = trial
            break
    lcl_t = theta * (lcl_p / 1000.0) ** (RD / CPD)
    for i, level in enumerate(p_levels):
        if level >= lcl_p:
            out[i] = theta * (level / 1000.0) ** (RD / CPD) - 273.15
            continue
        if i == 0 or p_levels[i - 1] >= lcl_p:
            p, t = lcl_p, lcl_t
        steps = max(1, int(np.ceil(abs(np.log(p / level)) / 0.005)))
        dlnp = np.log(level / p) / steps
        for _ in range(steps):
            k1 = _dtdlnp(p, t)
            mid_p = p * np.exp(0.5 * dlnp)
            k2 = _dtdlnp(mid_p, t + 0.5 * dlnp * k1)
            t = t + dlnp * k2
            p = p * np.exp(dlnp)
        out[i] = t - 273.15
    return out


def neutral_state(template: sd.Sounding, dt: float, sst: float, humidity: str = "rh") -> sd.Sounding:
    """Warm or cool the template's boundary layer by dt and rebuild its neutral temperature profile.

    Tropopause temperature and the isothermal stratosphere stay at the template's values, so warming
    raises the tropopause instead of heating the stratosphere and the outflow temperature changes little.
    RH is preserved level by level when humidity is 'rh'. With 'q' the mixing ratio is kept and
    capped at saturation so the initial state cannot condense.
    """
    p = template.p
    itrop = int(np.argmin(template.t))
    t_trop = float(template.t[itrop])
    top = int(np.searchsorted(-p, -30.0))
    lifted = parcel_profile(p[: top + 1], p[0], template.t[0] + dt, float(template.r[0]) * _rh_factor(template, dt))
    base = parcel_profile(p[: top + 1], p[0], template.t[0], float(template.r[0]))
    # Keep the template's departure from a pure parcel profile so dt=0 returns it unchanged.
    departure = np.full(top + 1, template.t[itrop] - base[itrop])
    departure[: itrop + 1] = template.t[: itrop + 1] - base[: itrop + 1]
    t = np.full(len(p), t_trop)
    t[: top + 1] = np.maximum(lifted + departure, t_trop)
    if dt == 0:
        t = template.t.copy()
    new_trop = int(np.argmax(t <= t_trop + 1e-6))
    t[new_trop:] = t_trop
    itrop = new_trop
    if humidity == "rh":
        # The template holds RH slightly above 1 near its cold tropopause; do not carry that into new states.
        r = np.minimum(sd.rh(template), 1.0) * sd.rsat(p, t)
    else:
        r = np.minimum(template.r, sd.rsat(p, t))
    # Above the tropopause mixing ratio stays negligible and is left alone.
    r[itrop + 1 :] = template.r[itrop + 1 :]
    return sd.replace(template, t=t, r=r, sst=sst)


def _rh_factor(template, dt):
    """Ratio of mixing ratio at the warmed lowest level with RH preserved."""
    p0, t0 = template.p[:1], template.t[:1]
    return float(sd.rsat(p0, t0 + dt)[0] / sd.rsat(p0, t0)[0])


def reproduce_s_in(path):
    s = sd.read(path)
    itrop = int(np.argmin(s.t))
    prof = parcel_profile(s.p[: itrop + 1], s.p[0], s.t[0], s.r[0])
    return s, itrop, prof
