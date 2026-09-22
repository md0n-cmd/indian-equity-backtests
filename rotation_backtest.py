import pandas as pd

CAPITAL = 50000
LOOKBACK = 12
TOP_N = 2
CASH_RATE = 0.065
ONE_WAY = 0.001        # 0.1% per side (slippage + fees)
DP = 15.93
DEV_END = "2020-12-31"

ASSETS = ["NIFTY50", "MIDCAP150", "NEXT50", "IT", "BANK", "PHARMA", "AUTO",
          "FMCG", "ENERGY", "PSUBANK", "REALTY", "INFRA", "GOLDBEES"]

def load(n):
    d = pd.read_csv(f"factors/{n}.csv", parse_dates=["date"]).set_index("date").close
    return d[~d.index.duplicated()].sort_index()

px = pd.concat({a: load(a) for a in ASSETS}, axis=1).sort_index()
m = px.resample("ME").last().iloc[:-1]
ret = m.pct_change()
mom = m / m.shift(LOOKBACK) - 1
cash_m = (1 + CASH_RATE) ** (1 / 12) - 1

w, rows, eq = {}, [], CAPITAL
for i in range(LOOKBACK, len(m) - 1):
    sig = mom.iloc[i].dropna()
    sig = sig[ret.iloc[i + 1][sig.index].notna()]
    picks = sig.sort_values(ascending=False)[:TOP_N]
    picks = picks[picks > CASH_RATE]
    new = {a: 1 / TOP_N for a in picks.index}
    turn = sum(abs(new.get(a, 0) - w.get(a, 0)) for a in set(new) | set(w))
    sold = len([a for a in w if new.get(a, 0) < w[a]])
    eq -= eq * turn * ONE_WAY + sold * DP
    w = new
    r = sum(wt * ret.iloc[i + 1][a] for a, wt in w.items()) + (1 - sum(w.values())) * cash_m
    eq *= 1 + r
    rows.append((m.index[i + 1], eq, "+".join(sorted(w)) or "CASH", ret.iloc[i + 1]["NIFTY50"],
                 ret.iloc[i + 1]["GOLDBEES"]))

res = pd.DataFrame(rows, columns=["date", "eq", "hold", "rn", "rg"]).set_index("date")
res["r_rot"] = res["eq"].pct_change().fillna(res["eq"].iloc[0] / CAPITAL - 1)
res["r_5050"] = 0.5 * res.rn + 0.5 * res.rg

def stats(r):
    c = (1 + r).cumprod()
    return c.iloc[-1] ** (12 / len(r)) - 1, (c / c.cummax().clip(lower=1) - 1).min()

def report(label, part):
    print(f"\n=== {label}: {part.index[0].strftime('%b %Y')} to {part.index[-1].strftime('%b %Y')} ===")
    for col, name in [("r_rot", "Sector/size rotation"), ("rn", "Buy & hold Nifty"),
                      ("rg", "Buy & hold Gold"), ("r_5050", "50/50 Nifty+Gold")]:
        cg, dd = stats(part[col])
        print(f"  {name:22s} CAGR {cg:6.1%} | Max drawdown {dd:6.1%}")

report("FULL PERIOD", res)
report("DEVELOPMENT", res[:DEV_END])
v = res[DEV_END:]
report("VAULT (2021+)", v.iloc[1:] if v.index[0] == pd.Timestamp(DEV_END) else v)
print("\nSwitch months:", (res.hold != res.hold.shift()).sum() - 1, "of", len(res))
print("Most-held combos:\n", res.hold.value_counts().head(8).to_string())
