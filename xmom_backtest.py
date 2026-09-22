import glob, os
import pandas as pd

CAPITAL = 50000
TOP_N = 10             # stocks held
KEEP_N = 20            # keep a holding while it ranks in the top 20
LOOKBACK = 252         # 12 months
SKIP = 21              # skip the latest month
TREND = 200
BREADTH_MIN = 0.5      # min share of stocks above 200-day average
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

mom = C.shift(SKIP) / C.shift(LOOKBACK) - 1
sma = C.rolling(TREND).mean()
breadth = (C > sma).sum(axis=1) / sma.notna().sum(axis=1)

idx = C.index
month_end = pd.Series(idx.month, index=idx) != pd.Series(idx.month, index=idx).shift(-1)
dates = idx[mom.notna().sum(axis=1).values >= TOP_N * 2]
cash, pos, trades, curve, orders = CAPITAL, {}, [], [], None

for d in dates:
    if orders is not None:
        target = orders
        for s in [s for s in pos if s not in target]:
            px = O.at[d, s]
            if pd.isna(px):
                continue
            px *= 1 - SLIP
            p = pos.pop(s)
            val = p["qty"] * px
            cash += val - sell_cost(val)
            trades.append(dict(sym=s, entry_date=p["date"], exit_date=d,
                               net=val - sell_cost(val) - p["cost"], days=(d - p["date"]).days))
        equity_prev = curve[-1][1] if curve else CAPITAL
        new = [s for s in target if s not in pos]
        for s in new:
            px = O.at[d, s]
            if pd.isna(px):
                continue
            px *= 1 + SLIP
            qty = int(min(equity_prev / TOP_N, cash) / (px * 1.0012))
            if qty < 1:
                continue
            val = qty * px
            cash -= val + buy_cost(val)
            pos[s] = dict(qty=qty, date=d, cost=val + buy_cost(val), entry=px)
        orders = None

    equity = cash + sum(p["qty"] * (C.at[d, s] if pd.notna(C.at[d, s]) else p["entry"])
                        for s, p in pos.items())
    curve.append((d, equity))

    if month_end.at[d]:
        if breadth.at[d] < BREADTH_MIN:
            orders = []
        else:
            rank = mom.loc[d].dropna().sort_values(ascending=False)
            keep = [s for s in pos if s in rank.index[:KEEP_N]]
            fill = [s for s in rank.index if s not in keep][:max(0, TOP_N - len(keep))]
            orders = keep + fill

eq = pd.Series(dict(curve))
years = (eq.index[-1] - eq.index[0]).days / 365.25
cagr = (eq.iloc[-1] / CAPITAL) ** (1 / years) - 1
mdd = (eq / eq.cummax() - 1).min()
bench = (1 + C.loc[eq.index].pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod() * CAPITAL
b_cagr = (bench.iloc[-1] / CAPITAL) ** (1 / years) - 1
b_mdd = (bench / bench.cummax() - 1).min()
t = pd.DataFrame(trades)
t.to_csv("xmom_trades.csv", index=False)

print(f"Period: {eq.index[0].date()} to {eq.index[-1].date()} ({years:.1f} yrs)")
print(f"Final equity: Rs {eq.iloc[-1]:,.0f} | CAGR: {cagr:.1%} | Max drawdown: {mdd:.1%}")
print(f"Benchmark (buy & hold all stocks): CAGR {b_cagr:.1%} | Max drawdown {b_mdd:.1%}")
print(f"Closed trades: {len(t)} | Win rate: {(t.net > 0).mean():.1%} | Avg hold: {t.days.mean():.0f} days")
yr = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), eq.resample("YE").last()]).pct_change().dropna()
by = pd.concat([pd.Series([CAPITAL], index=[eq.index[0]]), bench.resample("YE").last()]).pct_change().dropna()
print("\nYearly return (strategy vs benchmark):")
for (d1, a), b in zip(yr.items(), by.values):
    print(f"  {d1.year}: {a:7.1%}  vs  {b:7.1%}")
