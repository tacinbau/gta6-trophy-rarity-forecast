"""GTA VI trophy rarity forecaster (Python 3.13, stdlib only, no network).

Reads every <id>.in case in the input dir, writes one <id>.out forecast
per case: five quantiles of each trophy's Exophase earn rate at the target.

A rate is earned / tracked, so the two counts are grown separately in
log-time since release (2026-11-19T00:00Z), then divided again. Tracked
grows with slope aN on ln(t+1h), fitted from the case's reads when they
vary, else a prior of 1.0. Earned grows per trophy with slope aE, fitted
and shrunk toward its tier's mean, else a prior of 0.3. Exophase refreshes
in jumps, so the displayed page lags the players who already synced: the
lag L is the hours since the tracked count last moved (or since the first
read). Both counts are caught up over that lag, then grown to the target.
New players hold far fewer trophies than the launch cohort, so the earned
catch-up is only a fraction f of the tracked one (f rises with the rate;
the trophy everyone holds stays at 100%). Quantiles are logit-normal
around the median, with a spread widening with the horizon, the
extrapolation distance and the display lag. Deterministic: no randomness,
no clocks, no I/O beyond the case files.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

IN = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUT = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
REL = datetime(2026, 11, 19, tzinfo=timezone.utc)
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]


def clamp(x):
    return min(99.99, max(0.01, x))


def logit(p):
    p = clamp(p) / 100.0
    return math.log(p / (1 - p))


def invlogit(x):
    return 100.0 / (1.0 + math.exp(-x))


def round4(x):
    s = x * 10000
    w = math.floor(s)
    if s - w >= 0.5:
        w += 1
    v = w / 10000
    return int(v) if float(v).is_integer() else v


def hrs(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (dt - REL).total_seconds() / 3600.0


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 1e-9:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def sd(ys):
    m = sum(ys) / len(ys)
    return math.sqrt(sum((y - m) ** 2 for y in ys) / len(ys))


def fit(xs, ys, prior, k):
    s = ols(xs, ys)
    if s is None or sd(ys) < 0.02:
        return prior
    return (k * s + prior) / (k + 1.0)


def forecast(case):
    hist = case["history"]
    if not hist:
        raise ValueError("no history")
    u = max(hrs(case["at"]), 0.5)
    v = max(hrs(case["target"]), u + 0.01)
    d = case["horizon_minutes"] / 1440.0
    hh = case["horizon_minutes"] / 60.0
    last = hist[-1]
    n0 = float(last["players_tracked"])
    t_last = hrs(hist[0]["at"])
    for i in range(1, len(hist)):
        if hist[i]["players_tracked"] != hist[i - 1]["players_tracked"]:
            t_last = hrs(hist[i]["at"])
    lag = min(6.0, max(0.0, u - t_last))
    xs = [math.log(max(hrs(h["at"]), 0.0) + 1.0) for h in hist]
    aN = fit(xs, [math.log(max(h["players_tracked"], 1)) for h in hist],
             1.0, min(4.0, len(hist) / 5.0))
    aN = min(1.5, max(0.0, aN))
    grow = ((v + 1.0) / (u + 1.0)) ** aN
    lag_n = ((u + 1.0) / (max(u - lag, 0.0) + 1.0)) ** aN
    n1 = n0 * lag_n * grow
    lx = math.log((v + 1.0) / (u + 1.0))

    def series(i):
        ex, ey = [], []
        for x, h in zip(xs, hist):
            r = h["rates"][i]
            if r is not None and r > 0:
                ex.append(x)
                ey.append(math.log(max(r * h["players_tracked"] / 100.0, 0.05)))
        return ex, ey

    tier = {}
    for i, tr in enumerate(case["trophies"]):
        ex, ey = series(i)
        s = ols(ex, ey) if len(ex) >= 3 else None
        if s is not None and sd(ey) >= 0.02:
            tier.setdefault(tr["tier"], []).append(s)
    tmean = {t: sum(vv) / len(vv) for t, vv in tier.items()}
    s_rw = 0.5 * math.sqrt(d)
    s_tr = 0.35 * lx
    s_jp = 0.5 * (1 - math.exp(-lag / 3.0)) * math.sqrt(hh / 24.0)
    rows = []
    for i, tr in enumerate(case["trophies"]):
        r = last["rates"][i]
        if r is None:
            r = 0.01
        if r >= 99.99:
            rows.append({"id": tr["id"], "q": [100, 100, 100, 100, 100]})
            continue
        ex, ey = series(i)
        aE = fit(ex, ey, tmean.get(tr["tier"], 0.3), min(4.0, len(ex) / 5.0))
        aE = min(2.0, max(-0.5, aE))
        f = 0.3 * r / (r + 2.0)
        e1 = max(r * n0 / 100.0, 0.05) * (1 + (lag_n - 1) * f) * math.exp(aE * lx)
        med = clamp(min(max(100.0 * e1 / n1, r / 25.0), r * 25.0))
        s = min(math.sqrt(s_rw ** 2 + s_tr ** 2 + s_jp ** 2 + 0.35 ** 2
                          + (0.15 ** 2 if r < 0.5 else 0.0)), 1.3)
        lm = logit(med)
        qs = [round4(min(100.0, max(0.0, invlogit(lm + z * s)))) for z in Z]
        for j in range(1, 5):
            qs[j] = max(qs[j], qs[j - 1])
        rows.append({"id": tr["id"], "q": qs})
    return {"trophies": rows}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(IN.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        (OUT / f"{path.stem}.out").write_text(
            json.dumps(forecast(case), separators=(",", ":")) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
