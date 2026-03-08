"""Merge all individual institute CSV files into one unified dataset."""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def merge():
    files = list(DATA_DIR.glob("*_polls.csv"))
    if not files:
        print("No CSV files found in data/")
        return

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if "institut" not in df.columns:
                name = f.stem.replace("_polls", "").upper().replace("_", " ")
                df["institut"] = name
            dfs.append(df)
            print(f"  {f.name}: {len(df)} rows")
        except Exception as e:
            print(f"  Error reading {f.name}: {e}")

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged[["date", "institut", "subject", "link"]]
    out = DATA_DIR / "sondages_france.csv"
    merged.to_csv(out, index=False, encoding="utf-8")
    print(f"\nMerged {len(merged)} total polls -> {out}")
    return merged


if __name__ == "__main__":
    merge()
