import os
from datetime import date
import pandas as pd
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

load_dotenv()
dhan = dhanhq(DhanContext(os.environ["DHAN_CLIENT_ID"], os.environ["DHAN_ACCESS_TOKEN"]))
m = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
row = m[(m.SEM_EXM_EXCH_ID == "NSE") & (m.SEM_SEGMENT == "E") & (m.SEM_TRADING_SYMBOL == "NIFTYBEES")]
print(row[["SEM_SMST_SECURITY_ID", "SEM_INSTRUMENT_NAME", "SEM_SERIES"]])
sid = str(row.SEM_SMST_SECURITY_ID.iloc[0])
r = dhan.historical_daily_data(security_id=sid, exchange_segment="NSE_EQ", instrument_type="EQUITY",
                               from_date="2021-09-01", to_date=date.today().isoformat())
if r.get("status") != "success":
    print(r)
    raise SystemExit
d = pd.DataFrame(r["data"])
d["date"] = pd.to_datetime(d.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.date
d = d[["date", "open", "high", "low", "close", "volume"]]
os.makedirs("etf", exist_ok=True)
d.to_csv("etf/NIFTYBEES.csv", index=False)
print(len(d), "days:", d.date.min(), "to", d.date.max())
