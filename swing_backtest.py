import glob, os
import pandas as pd

CAPITAL = 50000
MAX_POS = 5            # max open positions
BREAKOUT = 50          # close at N-day high
TREND = 200            # close above N-day average
MOM = 126              # rank by ~6-month return
ATR_N = 20
ATR_MULT = 3.0         # trailing stop distance
BREADTH_MIN = 0.5      # min share of stocks above 200-day average
SLIP = 0.001           # 0.1% slippage per side
DP = 15.93             # Dhan DP charge per stock sold (incl. GST)

def buy_cost(v):
    return v * (0.001 + 0.00015 + (0.0000297 + 0.000001) * 1.18)

def sell_cost(v):
    return v * (0.001 + (0.0000297 + 0.000001) * 1.18) + DP

frames = {os.path.basename(f)[:-4]: pd.read_csv(f, index_col="date", parse_dates=True)
          for f in glob.glob("daily/*.csv")}
O = pd.DataFrame({s: d.open for s, d in frames.items()}).sort_index()
H = pd.DataFrame({s: d.high for s, d in frames.items()}).sort_index()
L = pd.DataFrame({s: d.low for s, d in frames.items()}).sort_index()
C = pd.DataFrame({s: d.close for s, d in frames.items()}).sort_index()

sma = C.rolling(TREND).mean()
hi = C.rolling(BREAKOUT).max()
mom = C / C.shift(MOM) - 1
pc = C.shift(1)
tr = pd.concat([H - L, (H - pc).abs(), (L - pc).abs()]).groupby(level=0).max()
atr = tr.rolling(ATR_N).mean()
breadth = (C > sma).sum(axis=1) / sma.notna().sum(axis=1)
signal = (C >= hi) & (C > sma) & breadth.ge(BREADTH_MIN).values[:, None]

dates = C.index[sma.notna().any(axis=1).values.argmax():]
cash, pos, trades, curve = CAPITAL, {}, [], []
to_buy, to_sell = [], []
for d in dates:
    for s in list(to_sell):
        px = O.at[d, s]
        if pd.isna(px):
            continue
        px *= 1 - SLIP
        p = pos.pop(s)
        val = p["qty"] * px
        cash += val - sell_cost(val)
        trades.append(dict(sym=s, entry_date=p["date"], exit_date=d, entry=p["entry"], exit=px,
                           qty=p["qty"], net=val - sell_cost(val) - p["cost"],
                           days=(d - p["date"]).days))
        to_sell.remove(s)
    equity_prev = curve[-1][1] if curve else CAPITAL
    for s in to_buy:
        px = O.at[d, s]
        if pd.isna(px) or len(pos) >= MAX_POS:
            continue
        px *= 1 + SLIP
        qty = int(min(equity_prev / MAX_POS, cash) / (px * 1.0012))
        if qty < 1:
            continue
        val = qty * px
        cash -= val + buy_cost(val)
        pos[s] = dict(qty=qty, entry=px, date=d, peak=C.at[d, s], cost=val + buy_cost(val))
    to_buy = []

    for s, p in pos.items():
        c = C.at[d, s]
        if pd.isna(c):
            continue
        p["peak"] = max(p["peak"], c)
        if c < p["peak"] - ATR_MULT * atr.at[d, s] and s not in to_sell:
            to_sell.append(s)
    equity = cash + sum(p["qty"] * (C.at[d, s] if pd.notna(C.at[d, s]) else p["entry"])
                        for s, p in pos.items())
    curve.append((d, equity))

    slots = MAX_POS - len(pos) + len(to_sell)
    if slots > 0:
        cands = mom.loc[d][signal.loc[d]].drop(list(pos), errors="ignore").dropna()
        to_buy = cands.sort_values(ascending=False).index[:slots].tolist()

eq = pd.Series(dict(curve))
years = (eq.index[-1] - eq.index[0]).days / 365.25
cagr = (eq.iloc[-1] / CAPITAL) ** (1 / years) - 1
mdd = (eq / eq.cummax() - 1).min()
bench = (1 + C.loc[dates].pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod() * CAPITAL
b_cagr = (bench.iloc[-1] / CAPITAL) ** (1 / years) - 1
b_mdd = (bench / bench.cummax() - 1).min()
t = pd.DataFrame(trades)
t.to_csv("swing_trades.csv", index=False)

print(f"Period: {eq.index[0].date()} to {eq.index[-1].date()} ({years:.1f} yrs)")
print(f"Final equity: Rs {eq.iloc[-1]:,.0f} | CAGR: {cagr:.1%} | Max drawdown: {mdd:.1%}")
print(f"Benchmark (buy & hold all stocks): CAGR {b_cagr:.1%} | Max drawdown {b_mdd:.1%}")
print(f"Trades: {len(t)} | Win rate: {(t.net > 0).mean():.1%} | Avg hold: {t.days.mean():.0f} days")
print(f"Avg win: Rs {t.net[t.net > 0].mean():,.0f} | Avg loss: Rs {t.net[t.net <= 0].mean():,.0f}")
print(f"Open positions at end: {len(pos)}")
yr = eq.resample("YE").last()
yr = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), yr]).pct_change().dropna()
by = bench.resample("YE").last()
by = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), by]).pct_change().dropna()
print("\nYearly return (strategy vs benchmark):")
for (d1, a), b in zip(yr.items(), by.values):
    print(f"  {d1.year}: {a:7.1%}  vs  {b:7.1%}")
