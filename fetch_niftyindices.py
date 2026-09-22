import os, time, json
import requests
import pandas as pd

INDICES = [
    "NIFTY 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY NEXT 50",
    "NIFTY200 MOMENTUM 30", "NIFTY100 LOW VOLATILITY 30", "NIFTY200 QUALITY 30",
    "NIFTY ALPHA 50", "NIFTY50 VALUE 20", "NIFTY MIDCAP150 MOMENTUM 50",
    "NIFTY IT", "NIFTY BANK", "NIFTY PHARMA", "NIFTY AUTO", "NIFTY FMCG",
    "NIFTY METAL", "NIFTY ENERGY", "NIFTY INFRASTRUCTURE",
]
START_YEAR = 2005
URL = "https://www.niftyindices.com/Backpage.aspx/getHistoricaldatatabletoString"
HEAD = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Content-Type": "application/json; charset=UTF-8",
    "Referer": "https://www.niftyindices.com/reports/historical-data",
    "X-Requested-With": "XMLHttpRequest",
}

s = requests.Session()
s.headers.update(HEAD)
s.get("https://www.niftyindices.com/reports/historical-data", timeout=30)

os.makedirs("factors_full", exist_ok=True)
for idx in INDICES:
    rows = []
    for yr in range(START_YEAR, pd.Timestamp.today().year + 1):
        payload = {"name": idx, "startDate": f"01-Jan-{yr}", "endDate": f"31-Dec-{yr}"}
        try:
            r = s.post(URL, json=payload, timeout=60)
            data = json.loads(r.json()["d"])
            rows += data
        except Exception as e:
            print(f"  {idx} {yr}: {type(e).__name__} {str(e)[:60]}")
        time.sleep(0.4)
    if not rows:
        print(f"{idx}: NO DATA")
        continue
    df = pd.DataFrame(rows)
    cols = {c.upper(): c for c in df.columns}
    df["date"] = pd.to_datetime(df[cols["HISTORICALDATE"]], format="%d %b %Y", errors="coerce")
    for k in ["OPEN", "HIGH", "LOW", "CLOSE"]:
        df[k.lower()] = pd.to_numeric(df[cols[k]].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
    fn = idx.replace(" ", "_").replace("50", "50")
    df[["date", "open", "high", "low", "close"]].to_csv(f"factors_full/{fn}.csv", index=False)
    print(f"{idx:32s} {len(df):5d} days  {df.date.iloc[0].date()} -> {df.date.iloc[-1].date()}")
