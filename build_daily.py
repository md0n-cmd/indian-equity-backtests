import glob, os
import pandas as pd

os.makedirs("daily", exist_ok=True)
for f in glob.glob("data/*_5m.csv"):
    sym = os.path.basename(f).rsplit("_", 1)[0]
    df = pd.read_csv(f)
    df["date"] = pd.to_datetime(df["time"].str[:10])
    d = df.groupby("date").agg(open=("open", "first"), high=("high", "max"),
                               low=("low", "min"), close=("close", "last"),
                               volume=("volume", "sum"))
    d.to_csv(f"daily/{sym}.csv")
    print(sym, len(d))
