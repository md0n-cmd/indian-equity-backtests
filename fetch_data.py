import os, time
from datetime import date, timedelta
import pandas as pd
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

WATCHLIST = pd.read_csv("nifty100.csv").Symbol.tolist()
DAYS_BACK = 1825
CHUNK = 85
INTERVAL = 5

load_dotenv()
dhan = dhanhq(DhanContext(os.environ["DHAN_CLIENT_ID"], os.environ["DHAN_ACCESS_TOKEN"]))

master = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
eq = master[(master.SEM_EXM_EXCH_ID == "NSE") & (master.SEM_SEGMENT == "E") & (master.SEM_SERIES == "EQ")]
ids = dict(zip(eq.SEM_TRADING_SYMBOL, eq.SEM_SMST_SECURITY_ID.astype(str)))

os.makedirs("data", exist_ok=True)
for sym in WATCHLIST:
    sid = ids.get(sym)
    if not sid:
        print(f"{sym}: not found in scrip master"); continue
    frames, end = [], date.today()
    start_limit = end - timedelta(days=DAYS_BACK)
    while end > start_limit:
        start = max(start_limit, end - timedelta(days=CHUNK))
        r = dhan.intraday_minute_data(sid, "NSE_EQ", "EQUITY",
                                      start.isoformat(), end.isoformat(), INTERVAL)
        d = r.get("data") or {}
        if d.get("timestamp"):
            frames.append(pd.DataFrame(d))
        else:
            print(f"{sym} {start}->{end}: {r.get('remarks', r.get('status'))}")
        end = start
        time.sleep(0.5)
    if frames:
        df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
        df["time"] = pd.to_datetime(df.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
        df = df[["time", "open", "high", "low", "close", "volume"]]
        df.to_csv(f"data/{sym}_{INTERVAL}m.csv", index=False)
        print(f"{sym}: {len(df)} candles saved")
