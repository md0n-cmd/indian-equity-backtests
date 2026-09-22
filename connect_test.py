import os
from datetime import date, timedelta
from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq

load_dotenv()
ctx = DhanContext(os.environ["DHAN_CLIENT_ID"], os.environ["DHAN_ACCESS_TOKEN"])
dhan = dhanhq(ctx)

print("--- Funds ---")
print(dhan.get_fund_limits())

print("--- LTP (HDFCBANK, security_id 1333) ---")
print(dhan.ticker_data(securities={"NSE_EQ": [1333]}))

print("--- Daily candles, raw ---")
resp = dhan.historical_daily_data(
    security_id="1333",
    exchange_segment="NSE_EQ",
    instrument_type="EQUITY",
    from_date=(date.today() - timedelta(days=30)).isoformat(),
    to_date=date.today().isoformat(),
)
print(resp)

