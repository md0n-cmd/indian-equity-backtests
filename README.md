# Indian Equity Strategy Backtests

Systematic backtests of eight trading strategies on NSE equities and indices, with full Indian transaction costs, slippage, and out-of-sample validation.

**Six of the eight failed.** That is the point of the repository. Most published backtests report gross returns on survivorship-biased universes. These report net returns after every cost a retail trader actually pays.

---

## Results

### Intraday strategies

| Strategy | Period | Result | Verdict |
|---|---|---|---|
| Opening Range Breakout (15-min, relative-volume filter) | 2021–2025, Nifty 100 | −21.8% over 4 years. Gross profit ₹173 on 759 trades; costs ₹2,357 | **Fail** |
| Intraday momentum (first 30 min → last 30 min) | 2021–2026, Nifty 100 | Captured 1.5 bps per trade against ~20 bps of costs | **Fail** |

The ORB strategy looked profitable in-sample (+10.4% in a single tuned year) and lost money in every out-of-sample year. This is the clearest illustration in the repo of why in-sample results cannot be trusted.

### Swing and positional strategies

| Strategy | Period | CAGR | Benchmark | Max DD | Verdict |
|---|---|---|---|---|---|
| Weekly short-term reversal | 2022–2026 | −3.8% | 22.7% | −41.2% | **Fail** — costs consumed ₹44,557 of ₹50,000 |
| 50-day breakout + 200-DMA + ATR trail | 2022–2026 | 19.0% | 22.7% | −21.3% | **Fail** — trails buy-and-hold |
| Monthly cross-sectional momentum (12-1, top 10) | 2022–2026 | 23.4% | 20.2% | −21.5% | **Inconclusive** — survivorship-inflated |
| Sector / size rotation (top 2 of 13 indices) | 2007–2026 | 12.1% | 9.5% | −48.3% | **Fail** — lost in-sample, extreme drawdown |

### Strategies that worked

| Strategy | Period | CAGR | Benchmark | Max DD | Verdict |
|---|---|---|---|---|---|
| Turn-of-month (NIFTYBEES + liquid fund) | 2021–2026 | 9.0% | 8.1% | −7.6% vs −16.1% | **Marginal pass** |
| **Dual momentum (Nifty / gold / cash)** | 2008–2026 | **12.1%** | 9.2% | **−15.7% vs −46.7%** | **Pass** |

Dual momentum was the only strategy to beat its benchmark with materially lower risk, and it held up on held-out data (15.4% vs 10.1% for the Nifty over 2021–2026).

**Robustness check** — the result is not an artifact of one parameter:

| Lookback | Strategy CAGR | Nifty CAGR | Max DD |
|---|---|---|---|
| 6 months | 9.2% | 8.6% | −25.7% |
| 9 months | 12.2% | 7.7% | −17.9% |
| 12 months | 12.1% | 9.2% | −15.7% |
| 15 months | 12.6% | 10.3% | −23.6% |
| 18 months | 14.1% | 10.7% | −14.8% |

Every setting beat the index. A result that only worked at one parameter value would indicate curve-fitting.

---

## Cost model

Every backtest charges the costs a retail trader actually pays. These are the numbers that killed most of the strategies above.

**Intraday equity (per round trip)**
- Brokerage: ₹20 or 0.03% per order, whichever is lower
- STT: 0.025% on the sell side
- Exchange transaction charges: 0.00297%
- SEBI turnover fee: 0.0001%
- Stamp duty: 0.003% on the buy side
- GST: 18% on brokerage + exchange charges
- Slippage: 0.05% per side

**Delivery equity**
- Brokerage: ₹0
- STT: 0.1% on both buy and sell
- DP charge: ~₹16 per scrip sold (flat — this is what destroys small accounts)
- Stamp duty: 0.015% on the buy side
- Slippage: 0.1% per side

**ETF**
- STT: 0.001% on the sell side, two orders of magnitude below delivery equity

At a ₹50,000 account size, a flat ₹16 DP charge is 0.32% of a ₹5,000 position. Any strategy holding for less than about two months is structurally unprofitable at that capital, regardless of signal quality.

---

## Methodology

**Out-of-sample validation.** Parameters were tuned on one period and tested on data never used for tuning. The ORB strategy is the cautionary example: +10.4% in the tuned year, −21.8% across four out-of-sample years.

**Survivorship bias.** Stock-level tests use the current Nifty 100 constituents, which biases results upward because today's index members are partly there *because* they rose. Results from those tests are flagged as inflated rather than presented as reliable. The index and ETF tests (turn-of-month, dual momentum, sector rotation) are free of this bias, which is why they are the trustworthy ones.

**Multiple-testing discipline.** Strategies were specified in full before being run. Testing enough variations guarantees one will look profitable by chance, so parameter sweeps are reported in full rather than selectively.

**Statistical significance.** The turn-of-month effect showed a t-statistic of 1.69 (0.118% average return on turn-of-month days vs 0.016% on other days) and is reported as suggestive rather than conclusive.

**Known limitations.** Index data is price return, excluding dividends, which understates equity returns by roughly 1.2–1.5% a year. Taxes are not modelled; high-turnover strategies would fare worse after short-term capital gains tax. Gold's 2008–2026 performance was exceptional and may not repeat.

---

## Data

Historical data is **not included** in this repository (broker-licensed). The fetch scripts will rebuild it:

- `fetch_data.py` — 5-minute candles for the Nifty 100
- `build_daily.py` — daily candles aggregated from 5-minute data
- `fetch_factors.py` — index and gold ETF histories
- `fetch_sectors.py` — sector and size index histories
- `fetch_etf.py` — NIFTYBEES daily data

Requires a DhanHQ account with Data API access. Credentials go in a `.env` file (see `.env.example`).

---

## Repository contents

```
orb_backtest.py         Opening range breakout
im_backtest.py          Intraday momentum
rev_backtest.py         Weekly short-term reversal
swing_backtest.py       Breakout swing with ATR trailing stop
xmom_backtest.py        Monthly cross-sectional momentum
tom_backtest.py         Turn-of-month ETF timing
dualmom_backtest.py     Dual momentum (Nifty / gold / cash)
rotation_backtest.py    Sector and size rotation
```

Each script prints a summary and writes a trade-level CSV.

**Requirements:** Python 3.10+, pandas, dhanhq, python-dotenv

---

## What this is not

Not investment advice, and not a signal service. This is backtesting code and the results it produced. Past performance does not predict future returns, and a backtest is a hypothesis, not a promise.

---

## About

Built by Mujahid A R — research consultant at WorldQuant BRAIN, working on systematic equity strategy research.

Available for freelance work in backtesting, strategy validation, market-data pipelines, and trading automation.
