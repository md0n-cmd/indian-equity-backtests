import os, time
from datetime import date
import pandas as pd
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

load_dotenv()
dhan = dhanhq(DhanContext(os.environ["DHAN_CLIENT_ID"], os.environ["DHAN_ACCESS_TOKEN"]))

ASSETS = [  # name, security_id, segment, instrument_type
    ("NIFTY50", "13", "IDX_I", "INDEX"),
    ("MOMENTUM30", "480", "IDX_I", "INDEX"),
    ("LOWVOL30", "11", "IDX_I", "INDEX"),
    ("QUALITY30", "287", "IDX_I", "INDEX"),
    ("VALUE20", "286", "IDX_I", "INDEX"),
    ("ALPHA50", "12", "IDX_I", "INDEX"),
    ("ALPHALOWVOL", "482", "IDX_I", "INDEX"),
    ("GOLDBEES", "14428", "NSE_EQ", "EQUITY"),
]

os.makedirs("factors", exist_ok=True)
for name, sid, seg, itype in ASSETS:
    frames = []
    for yr in range(2005, date.today().year + 1):
        start, end = f"{yr}-01-01", min(f"{yr}-12-31", date.today().isoformat())
        r = dhan.historical_daily_data(security_id=sid, exchange_segment=seg, instrument_type=itype,
                                       from_date=start, to_date=end)
        d = r.get("data") if isinstance(r, dict) else None
        if isinstance(d, dict) and d.get("timestamp"):
            frames.append(pd.DataFrame(d))
        time.sleep(0.3)
    if not frames:
        print(f"{name}: NO DATA  last response: {r.get('remarks') if isinstance(r, dict) else r}")
        continue
    df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
    df["date"] = pd.to_datetime(df.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.date
    df = df[["date", "open", "high", "low", "close"]]
    df.to_csv(f"factors/{name}.csv", index=False)
    print(f"{name:12s} {len(df):5d} days  {df.date.iloc[0]} -> {df.date.iloc[-1]}  last close {df.close.iloc[-1]:,.2f}")
