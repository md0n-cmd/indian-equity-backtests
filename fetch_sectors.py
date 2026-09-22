import os, time
from datetime import date
import pandas as pd
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

load_dotenv()
dhan = dhanhq(DhanContext(os.environ["DHAN_CLIENT_ID"], os.environ["DHAN_ACCESS_TOKEN"]))

ASSETS = [
    ("MIDCAP150", "1"), ("SMALLCAP250", "3"), ("NEXT50", "38"),
    ("IT", "29"), ("BANK", "25"), ("PHARMA", "32"), ("AUTO", "14"),
    ("FMCG", "28"), ("METAL", "31"), ("ENERGY", "42"), ("INFRA", "43"),
    ("CONSUMPTION", "40"), ("PSUBANK", "33"), ("REALTY", "34"),
]

os.makedirs("factors", exist_ok=True)
for name, sid in ASSETS:
    frames, last = [], None
    for yr in range(2006, date.today().year + 1):
        r = dhan.historical_daily_data(security_id=sid, exchange_segment="IDX_I", instrument_type="INDEX",
                                       from_date=f"{yr}-01-01",
                                       to_date=min(f"{yr}-12-31", date.today().isoformat()))
        last = r
        d = r.get("data") if isinstance(r, dict) else None
        if isinstance(d, dict) and d.get("timestamp"):
            frames.append(pd.DataFrame(d))
        time.sleep(0.3)
    if not frames:
        print(f"{name}: NO DATA  {last.get('remarks') if isinstance(last, dict) else last}")
        continue
    df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp")
    df["date"] = pd.to_datetime(df.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.date
    df[["date", "open", "high", "low", "close"]].to_csv(f"factors/{name}.csv", index=False)
    print(f"{name:12s} {len(df):5d} days  {df.date.iloc[0]} -> {df.date.iloc[-1]}")
