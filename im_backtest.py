import glob, os
import pandas as pd

CAPITAL = 10000
MAX_POS = 3            # stocks traded per day
MIN_MOVE = 0.01        # min |return| from prev close to 9:45 (1%)
SLIP = 0.0005          # 0.05% slippage per side
SIGNAL_BAR = "09:40"   # bar ending 9:45
ENTRY_BAR = "14:50"    # enter at 14:50 open
EXIT_BAR = "15:10"     # exit at ~15:15 close

def costs(buy_val, sell_val):
    brok = (0.0003 * buy_val).clip(upper=20) + (0.0003 * sell_val).clip(upper=20)
    stt = 0.00025 * sell_val
    exch = 0.0000297 * (buy_val + sell_val)
    sebi = 0.000001 * (buy_val + sell_val)
    stamp = 0.00003 * buy_val
    gst = 0.18 * (brok + exch + sebi)
    return brok + stt + exch + sebi + stamp + gst

rows = []
for f in glob.glob("data/*_5m.csv"):
    sym = os.path.basename(f).rsplit("_", 1)[0]
    df = pd.read_csv(f)
    df["date"] = df.time.str[:10]
    df["hm"] = df.time.str[11:16]
    day_close = df.groupby("date").close.last()
    d = pd.DataFrame({
        "prev_close": day_close.shift(1),
        "sig": df[df.hm == SIGNAL_BAR].set_index("date").close,
        "entry": df[df.hm == ENTRY_BAR].set_index("date").open,
        "exit": df[df.hm == EXIT_BAR].set_index("date").close,
    }).dropna()
    del df
    d["r1"] = d.sig / d.prev_close - 1
    d["sym"] = sym
    rows.append(d.reset_index(names="date"))

a = pd.concat(rows)
a = a[a.r1.abs() >= MIN_MOVE].copy()
a["absr"] = a.r1.abs()
t = a.sort_values("absr", ascending=False).groupby("date").head(MAX_POS).copy()

t = t.reset_index(drop=True)
t["dir"] = (t.r1 > 0).map({True: 1, False: -1})
t["side"] = t.dir.map({1: "L", -1: "S"})
t["px_in"] = t.entry * (1 + SLIP * t.dir)
t["px_out"] = t.exit * (1 - SLIP * t.dir)
t["qty"] = (CAPITAL / MAX_POS / t.px_in).astype(int)
t = t[t.qty > 0].copy()
t["gross"] = (t.px_out - t.px_in) * t.qty * t.dir
lng = t.dir == 1
buy = (t.px_in * t.qty).where(lng, t.px_out * t.qty)
sell = (t.px_out * t.qty).where(lng, t.px_in * t.qty)
t["costs"] = costs(buy, sell)
t["net"] = t.gross - t.costs
t["raw_bps"] = (t.exit / t.entry - 1) * 10000 * t.dir

t = t.sort_values("date")
t.to_csv("im_trades.csv", index=False)
eq = t.groupby("date").net.sum().cumsum()
dd = (eq - eq.cummax().clip(lower=0)).min()
print(f"Period: {t.date.min()} to {t.date.max()}")
print(f"Trades: {len(t)} | Days traded: {t.date.nunique()}")
print(f"Win rate: {(t.net > 0).mean():.1%} | Avg raw move captured: {t.raw_bps.mean():.1f} bps (costs+slippage ~20 bps)")
print(f"Gross: Rs {t.gross.sum():,.0f} | Costs: Rs {t.costs.sum():,.0f} | Net: Rs {t.net.sum():,.0f}")
print(f"Net on Rs {CAPITAL:,}: {t.net.sum() / CAPITAL:.1%} | Max drawdown: Rs {dd:,.0f}")
print("\nBy side:\n", t.groupby("side").agg(trades=("net", "size"), net=("net", "sum"), raw_bps=("raw_bps", "mean")).round(1))
t["year"] = t.date.str[:4]
print("\nBy year:\n", t.groupby("year").agg(trades=("net", "size"), net=("net", "sum"), raw_bps=("raw_bps", "mean")).round(1))
