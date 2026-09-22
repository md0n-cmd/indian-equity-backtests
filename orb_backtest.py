import glob, os
import pandas as pd

CAPITAL = 10000
MAX_POS = 3            # max stocks traded per day
RISK_PCT = 0.01        # max 1% of capital risked per trade
MIN_RVOL = 4.0         # opening-range volume vs 20-day average
LOOKBACK = 20
MIN_RANGE_PCT = 0.4    # skip narrow opening ranges
MAX_RANGE_PCT = 2.5    # skip very wide ranges (stop too far)
TARGET_R = None        # e.g. 2.0; None = hold until exit time
SLIP = 0.0005          # 0.05% slippage per side
EXIT_TIME = "15:10"
TEST_START = "2021-01-01"
TEST_END = "2025-09-21"

def costs(buy_val, sell_val):
    brok = min(20, 0.0003 * buy_val) + min(20, 0.0003 * sell_val)
    stt = 0.00025 * sell_val
    exch = 0.0000297 * (buy_val + sell_val)
    sebi = 0.000001 * (buy_val + sell_val)
    stamp = 0.00003 * buy_val
    gst = 0.18 * (brok + exch + sebi)
    return brok + stt + exch + sebi + stamp + gst

def load(f):
    df = pd.read_csv(f)
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("Asia/Kolkata")
    df["date"] = df.time.dt.date
    df["hm"] = df.time.dt.strftime("%H:%M")
    return df[(df.hm >= "09:15") & (df.hm <= "15:25")]

def simulate(day, hi, lo):
    side = None
    for r in day.itertuples():
        if side is None:
            up, dn = r.high > hi, r.low < lo
            if up and dn:
                return None
            if not (up or dn):
                continue
            side = "L" if up else "S"
            entry = max(hi, r.open) * (1 + SLIP) if up else min(lo, r.open) * (1 - SLIP)
            stop = lo if up else hi
            risk = abs(entry - stop)
            target = (entry + TARGET_R * risk if up else entry - TARGET_R * risk) if TARGET_R else None
            entry_time = r.hm
            continue
        if side == "L":
            if r.low <= stop:
                return side, entry, min(stop, r.open) * (1 - SLIP), "stop", entry_time, r.hm
            if target and r.high >= target:
                return side, entry, target * (1 - SLIP), "target", entry_time, r.hm
        else:
            if r.high >= stop:
                return side, entry, max(stop, r.open) * (1 + SLIP), "stop", entry_time, r.hm
            if target and r.low <= target:
                return side, entry, target * (1 + SLIP), "target", entry_time, r.hm
    if side is None:
        return None
    last = day.iloc[-1]
    exitp = last.close * (1 - SLIP) if side == "L" else last.close * (1 + SLIP)
    return side, entry, exitp, "eod", entry_time, last.hm

files = {os.path.basename(f).rsplit("_", 1)[0]: f for f in glob.glob("data/*_5m.csv")}
days = []
for sym, f in files.items():
    df = load(f)
    o = df[df.hm < "09:30"].groupby("date").agg(
        or_high=("high", "max"), or_low=("low", "min"),
        or_vol=("volume", "sum"), n=("close", "size"))
    del df
    o = o[o.n == 3]
    o["rvol"] = o.or_vol / o.or_vol.shift(1).rolling(LOOKBACK).mean()
    o["range_pct"] = (o.or_high - o.or_low) / o.or_low * 100
    o["sym"] = sym
    days.append(o.reset_index())

allo = pd.concat(days).dropna()
s, e = pd.to_datetime(TEST_START).date(), pd.to_datetime(TEST_END).date()
allo = allo[(allo.date >= s) & (allo.date <= e)]
cand = allo[(allo.rvol >= MIN_RVOL) & allo.range_pct.between(MIN_RANGE_PCT, MAX_RANGE_PCT)]
picks = cand.sort_values("rvol", ascending=False).groupby("date").head(MAX_POS)

trades = []
for sym, grp in picks.groupby("sym"):
    df = load(files[sym])
    df = df[df.date.isin(set(grp.date)) & (df.hm >= "09:30") & (df.hm <= EXIT_TIME)]
    for p in grp.itertuples():
        res = simulate(df[df.date == p.date], p.or_high, p.or_low)
        if not res:
            continue
        side, entry, exitp, reason, et, xt = res
        risk = abs(entry - (p.or_low if side == "L" else p.or_high))
        qty = int(min(CAPITAL * RISK_PCT / risk, (CAPITAL / MAX_POS) / entry))
        if qty < 1:
            continue
        gross = (exitp - entry) * qty if side == "L" else (entry - exitp) * qty
        buy_val, sell_val = (entry * qty, exitp * qty) if side == "L" else (exitp * qty, entry * qty)
        c = costs(buy_val, sell_val)
        trades.append(dict(date=p.date, sym=sym, side=side, entry=round(entry, 2),
                           exit=round(exitp, 2), qty=qty, reason=reason, entry_time=et,
                           exit_time=xt, rvol=round(p.rvol, 2), gross=round(gross, 2),
                           costs=round(c, 2), net=round(gross - c, 2),
                           R=round((gross - c) / (risk * qty), 2)))
    del df

t = pd.DataFrame(trades).sort_values("date")
t.to_csv("orb_trades.csv", index=False)
eq = t.groupby("date").net.sum().cumsum()
dd = (eq - eq.cummax().clip(lower=0)).min()
print(f"Period: {t.date.min()} to {t.date.max()}")
print(f"Trades: {len(t)} | Days traded: {t.date.nunique()}")
print(f"Win rate: {(t.net > 0).mean():.1%} | Avg R: {t.R.mean():.2f}")
print(f"Gross: Rs {t.gross.sum():,.0f} | Costs: Rs {t.costs.sum():,.0f} | Net: Rs {t.net.sum():,.0f}")
print(f"Net on Rs {CAPITAL:,}: {t.net.sum() / CAPITAL:.1%} | Max drawdown: Rs {dd:,.0f}")
print("\nBy side:\n", t.groupby("side").net.agg(["count", "sum", "mean"]).round(1))
print("\nBy exit reason:\n", t.groupby("reason").net.agg(["count", "sum"]).round(1))
t["year"] = pd.to_datetime(t.date).dt.year
print("\nBy year:\n", t.groupby("year").agg(trades=("net", "size"), net=("net", "sum"), avgR=("R", "mean")).round(2))
