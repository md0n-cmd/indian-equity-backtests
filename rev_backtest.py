import glob, os
import pandas as pd

CAPITAL = 50000
TOP_N = 10             # stocks held
LOOKBACK = 5           # rank by 5-day return (worst first)
TREND = 200            # only stocks above 200-day average
SLIP = 0.001
DP = 15.93

def buy_cost(v):
    return v * (0.001 + 0.00015 + (0.0000297 + 0.000001) * 1.18)

def sell_cost(v):
    return v * (0.001 + (0.0000297 + 0.000001) * 1.18) + DP

frames = {os.path.basename(f)[:-4]: pd.read_csv(f, index_col="date", parse_dates=True)
          for f in glob.glob("daily/*.csv")}
O = pd.DataFrame({s: d.open for s, d in frames.items()}).sort_index()
C = pd.DataFrame({s: d.close for s, d in frames.items()}).sort_index()

ret = C / C.shift(LOOKBACK) - 1
sma = C.rolling(TREND).mean()
idx = C.index
wk = pd.Series((idx - pd.to_timedelta(idx.weekday, unit="D")).values, index=idx)
week_end = (wk != wk.shift(-1)).fillna(True).astype(bool)
dates = idx[sma.notna().sum(axis=1).values >= TOP_N * 2]
cash, pos, trades, curve, orders, cost_total = CAPITAL, {}, [], [], None, 0.0

for d in dates:
    if orders is not None:
        for s in [s for s in pos if s not in orders]:
            px = O.at[d, s]
            if pd.isna(px):
                continue
            px *= 1 - SLIP
            p = pos.pop(s)
            val = p["qty"] * px
            cash += val - sell_cost(val)
            cost_total += sell_cost(val)
            trades.append(dict(sym=s, entry_date=p["date"], exit_date=d,
                               net=val - sell_cost(val) - p["cost"]))
        equity_prev = curve[-1][1] if curve else CAPITAL
        for s in [s for s in orders if s not in pos]:
            px = O.at[d, s]
            if pd.isna(px):
                continue
            px *= 1 + SLIP
            qty = int(min(equity_prev / TOP_N, cash) / (px * 1.0012))
            if qty < 1:
                continue
            val = qty * px
            cash -= val + buy_cost(val)
            cost_total += buy_cost(val)
            pos[s] = dict(qty=qty, date=d, cost=val + buy_cost(val), entry=px)
        orders = None

    equity = cash + sum(p["qty"] * (C.at[d, s] if pd.notna(C.at[d, s]) else p["entry"])
                        for s, p in pos.items())
    curve.append((d, equity))

    if week_end.at[d]:
        r = ret.loc[d][C.loc[d] > sma.loc[d]].dropna()
        orders = r.sort_values().index[:TOP_N].tolist()

eq = pd.Series(dict(curve))
years = (eq.index[-1] - eq.index[0]).days / 365.25
cagr = (eq.iloc[-1] / CAPITAL) ** (1 / years) - 1
mdd = (eq / eq.cummax() - 1).min()
bench = (1 + C.loc[eq.index].pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod() * CAPITAL
b_cagr = (bench.iloc[-1] / CAPITAL) ** (1 / years) - 1
t = pd.DataFrame(trades)
t.to_csv("rev_trades.csv", index=False)

print(f"Period: {eq.index[0].date()} to {eq.index[-1].date()} ({years:.1f} yrs)")
print(f"Final equity: Rs {eq.iloc[-1]:,.0f} | CAGR: {cagr:.1%} | Max drawdown: {mdd:.1%}")
print(f"Benchmark (buy & hold all stocks): CAGR {b_cagr:.1%}")
print(f"Closed trades: {len(t)} | Win rate: {(t.net > 0).mean():.1%} | Total costs: Rs {cost_total:,.0f}")
yr = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), eq.resample("YE").last()]).pct_change().dropna()
by = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), bench.resample("YE").last()]).pct_change().dropna()
print("\nYearly return (strategy vs benchmark):")
for (d1, a), b in zip(yr.items(), by.values):
    print(f"  {d1.year}: {a:7.1%}  vs  {b:7.1%}")
