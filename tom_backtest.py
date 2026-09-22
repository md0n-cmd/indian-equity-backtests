import pandas as pd
import numpy as np

CAPITAL = 50000
SLIP = 0.0005          # 0.05% per side
DP = 15.93
CASH_RATE = 0.065      # liquid-fund yield assumed when out of market

def buy_cost(v):
    return v * (0.00015 + (0.0000297 + 0.000001) * 1.18)

def sell_cost(v):
    return v * (0.00001 + (0.0000297 + 0.000001) * 1.18) + DP

d = pd.read_csv("etf/NIFTYBEES.csv", parse_dates=["date"]).set_index("date").sort_index()
mon = pd.Series(d.index.to_period("M"), index=d.index)
d, mon = d[mon < mon.iloc[-1]], mon[mon < mon.iloc[-1]]   # drop incomplete current month
c = d.close
ret = c.pct_change()
from_end = mon.groupby(mon).cumcount(ascending=False)     # 0 = last trading day
from_start = mon.groupby(mon).cumcount()                  # 0 = first trading day
window = (from_end == 0) | (from_start <= 2)              # days -1, +1, +2, +3

def run(cash_rate):
    eq, invested, curve, days_in = CAPITAL, False, [], 0
    for t in range(1, len(c)):
        if invested:
            eq *= 1 + ret.iloc[t]
            days_in += 1
        else:
            eq *= 1 + cash_rate / 252
        if not invested and from_end.iloc[t] == 1:
            eq -= buy_cost(eq) + eq * SLIP
            invested = True
        elif invested and from_start.iloc[t] == 2:
            eq -= sell_cost(eq) + eq * SLIP
            invested = False
        curve.append((c.index[t], eq))
    return pd.Series(dict(curve)), days_in

def stats(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1, (eq / eq.cummax() - 1).min()

tom0, days_in = run(0.0)
tomc, _ = run(CASH_RATE)
bh = CAPITAL * (1 - 0.0007) * (1 + ret.iloc[1:]).cumprod()

a, b = ret[window].dropna(), ret[~window].dropna()
tstat = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
print(f"Period: {c.index[0].date()} to {c.index[-1].date()} | Time in market: {days_in / (len(c) - 1):.0%}")
print(f"Avg daily return  in window: {a.mean() * 100:.3f}%  |  outside: {b.mean() * 100:.3f}%  |  t-stat: {tstat:.2f}")
for name, eq in [("TOM (cash earns 0%)", tom0), (f"TOM + liquid fund {CASH_RATE:.1%}", tomc), ("Buy & hold NIFTYBEES", bh)]:
    cg, dd = stats(eq)
    print(f"{name:28s} CAGR {cg:6.1%} | Max drawdown {dd:6.1%} | Final Rs {eq.iloc[-1]:,.0f}")
print("\nYearly (TOM+liquid vs buy & hold):")
ty = tomc.resample("YE").last().pct_change()
by = bh.resample("YE").last().pct_change()
ty.iloc[0] = tomc.resample("YE").last().iloc[0] / CAPITAL - 1
by.iloc[0] = bh.resample("YE").last().iloc[0] / CAPITAL - 1
for dt, x in ty.items():
    print(f"  {dt.year}: {x:7.1%}  vs  {by[dt]:7.1%}")
