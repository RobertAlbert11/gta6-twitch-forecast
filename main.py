#!/usr/bin/env python3
"""GTA6 Twitch CCU launch-day forecast — make.fun gta6-twitch-ccu-forecast-01.

Model (see MODEL.md):
  q_tau(h) = p1 * exp(shrink * m_h + e_tau(h))
- p1: hour-1 (00:00-01:00 UTC) print from `known`.
- m_h: weighted median over comparable launches of the launch-day log ratio
  ln(v_h / v1_comp), weighted by (a) scale similarity — closeness of the
  comparable's own hour-1 count to p1 in log space — and (b) recency; then
  3-point smoothed in log space. Launch day starts at 00:00 UTC of
  day_start (matches the practice cases' convention and GTA VI's rolling
  midnight, where the UTC day holds the unlock for most of the world).
- e_tau(h): empirical quantiles of leave-one-out residuals of the pooled
  comparables, blended with the house's sqrt(h-1) Gaussian profile.
Deterministic (no RNG), stdlib-only, well under the runtime budget.
"""
import json
import math
import os
from datetime import datetime, timezone

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

SHRINK = 1.45          # multiplier on the median curve
BAND = 1.5             # log-scale similarity bandwidth
FLAT_MIX = 0.55        # weight of the flat sqrt(h-1) spread vs empirical residuals
SPREAD_SCALE = 0.60    # overall spread scaling
RECENCY = 0.15         # weight decay per year of age (from 2018)
CLIP = 2.0             # clip LOO residuals to +-CLIP log units
MIN_CURVE = 10         # min hours for a comparable's curve to be used
EARLY_WIN, LATE_WIN = 3, 2   # residual-pooling window (hours either side)


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def hour_index(dt, day_start):
    return int((dt - day_start).total_seconds() // 3600)


def launch_curve(comp):
    """log ratios v_h / v_1 for hours 2..24 of the launch day + hour-1 count."""
    ds = parse_iso(comp["day_start"])
    by_hour = {}
    for row in comp.get("hourly") or []:
        at = parse_iso(row["from"])
        h = hour_index(at, ds)
        if 0 <= h <= 24:
            v = row.get("viewers")
            if v is not None and v > 0:
                by_hour[h] = v
    v1 = by_hour.get(0)
    if not v1 or v1 <= 0:
        return None, None
    curve = {h: math.log(v) - math.log(v1) for h, v in by_hour.items() if 2 <= h <= 24}
    return curve, v1


def weighted_median_log(pairs):
    if not pairs:
        return None
    pairs = sorted(pairs)
    tw = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= 0.5 * tw:
            return v
    return pairs[-1][0]


def empirical_quantile(sorted_vals, tau):
    n = len(sorted_vals)
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def build_forecast(case):
    p1 = 1.0
    for r in case.get("known") or []:
        v = r.get("viewers")
        if v is not None and v > 0:
            p1 = float(v)
    p1 = max(p1, 1.0)

    curves = []  # (name, curve, weight)
    for comp in case.get("comparables") or []:
        curve, cv1 = launch_curve(comp)
        if not curve or len(curve) < MIN_CURVE:
            continue
        d = abs(math.log(cv1) - math.log(p1))
        w = math.exp(-((d / BAND) ** 2)) + 0.05
        try:
            yr = int(comp["day_start"][:4])
            w *= math.exp((yr - 2018) * RECENCY)
        except (ValueError, KeyError):
            pass
        curves.append((comp.get("name", "?"), curve, w))

    hours = range(2, 25)

    # weighted median log-ratio per hour, 3-point smoothed
    med = {}
    for h in hours:
        pairs = [(c[h], w) for _, c, w in curves if h in c]
        m = weighted_median_log(pairs)
        med[h] = m if m is not None else 0.0
    sm = {}
    for h in hours:
        vals = [med[k] for k in (h - 1, h, h + 1) if k in med]
        sm[h] = sum(vals) / len(vals)
    med = sm

    # leave-one-out residuals for the spread
    resid = {h: [] for h in hours}
    for name, curve, _ in curves:
        for h in hours:
            if h not in curve:
                continue
            pairs = [(c[h], ww) for n2, c, ww in curves if n2 != name and h in c]
            m = weighted_median_log(pairs)
            r = curve[h] - (m if m is not None else 0.0)
            resid[h].append(max(-CLIP, min(CLIP, r)))

    out = {"hours": []}
    for h in hours:
        win = EARLY_WIN if h <= 6 else LATE_WIN
        pl = []
        for k in range(h - win, h + win + 1):
            pl.extend(resid.get(k, []))
        pl.sort()
        row = []
        for i, tau in enumerate(LEVELS):
            if len(pl) >= 8:
                e = empirical_quantile(pl, tau)
            else:
                e = Z[i] * 0.14
            e = (1 - FLAT_MIX) * e + FLAT_MIX * (Z[i] * 0.15 * math.sqrt(h - 1))
            e *= SPREAD_SCALE
            v = p1 * math.exp(SHRINK * med[h] + e)
            row.append(round(min(max(v, 1e-9), 1e9), 2))
        for i in range(1, 5):
            if row[i] < row[i - 1]:
                row[i] = row[i - 1]
        out["hours"].append({"hour": h, "q": row})
    return out


def main():
    indir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    for fname in sorted(f for f in os.listdir(indir) if f.endswith(".in")):
        with open(os.path.join(indir, fname), "r", encoding="utf-8") as f:
            case = json.load(f)
        result = build_forecast(case)
        with open(os.path.join(outdir, fname[:-3] + ".out"), "w", encoding="utf-8") as f:
            json.dump(result, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
