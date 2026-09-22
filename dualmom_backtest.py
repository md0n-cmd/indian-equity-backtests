import pandas as pd

CAPITAL = 50000
LOOKBACK = 12          # months
CASH_RATE = 0.065      # yearly, assumed liquid-fund yield
SWITCH_COST = 0.002    # ~0.2% per switch (slippage + fees, both sides)
DP = 15.93
DEV_END = "2020-12-31" # development period ends; 2021+ is the vault

def load(name):
    d = pd.read_csv(f"factors/{name}.csv", parse_dates=["date"]).set_index("date").close
    return d[~d.index.duplicated()].sort_index()

px = pd.concat({"NIFTY": load("NIFTY50"), "GOLD": load("GOLDBEES")}, axis=1).dropna()
m = px.resample("ME").last().dropna().iloc[:-1]   # drop incomplete current month
ret = m.pct_change()
mom = m / m.shift(LOOKBACK) - 1
cash_m = (1 + CASH_RATE) ** (1 / 12) - 1
cash_12 = CASH_RATE

hold, rows, eq = "CASH", [], CAPITAL
for i in range(LOOKBACK, len(m) - 1):
    d = m.index[i]
    best = mom.iloc[i].idxmax()
    target = best if mom.iloc[i][best] > cash_12 else "CASH"
    if target != hold:
        eq -= eq * SWITCH_COST + (DP if hold != "CASH" else 0)
        hold = target
    r = cash_m if hold == "CASH" else ret.iloc[i + 1][hold]
    eq *= 1 + r
    rows.append((m.index[i + 1], eq, hold, ret.iloc[i + 1]["NIFTY"], ret.iloc[i + 1]["GOLD"]))

res = pd.DataFrame(rows, columns=["date", "eq", "hold", "rn", "rg"]).set_index("date")
res["r_dm"] = res["eq"].pct_change().fillna(res["eq"].iloc[0] / CAPITAL - 1)
res["r_5050"] = 0.5 * res.rn + 0.5 * res.rg

def stats(r):
    curve = (1 + r).cumprod()
    yrs = len(r) / 12
    return curve.iloc[-1] ** (1 / yrs) - 1, (curve / curve.cummax().clip(lower=1) - 1).min()

def report(label, part):
    print(f"\n=== {label}: {part.index[0].strftime('%b %Y')} to {part.index[-1].strftime('%b %Y')} ===")
    for col, name in [("r_dm", "Dual momentum"), ("rn", "Buy & hold Nifty"),
                      ("rg", "Buy & hold Gold"), ("r_5050", "50/50 Nifty+Gold")]:
        cg, dd = stats(part[col])
        print(f"  {name:18s} CAGR {cg:6.1%} | Max drawdown {dd:6.1%}")

report("FULL PERIOD", res)
dev, vault = res[:DEV_END], res[DEV_END:].iloc[1:] if res[DEV_END:].index[0] == pd.Timestamp(DEV_END) else res[DEV_END:]
report("DEVELOPMENT", dev)
report("VAULT (2021+)", vault)
print("\nTime in each asset:", (res.hold.value_counts(normalize=True) * 100).round(0).to_dict())
print("Switches:", (res.hold != res.hold.shift()).sum() - 1, "over", len(res), "months")
