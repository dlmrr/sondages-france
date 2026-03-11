"""
Merge all individual institute CSV files into one unified dataset.
For IPSOS, Harris, and IFOP: combines old (pre-2022) and new scrapes, deduplicating.
"""
import re
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
OLD_DIR = Path(__file__).resolve().parent.parent / "old project"


def normalize_date(val):
    """Normalize a date string to YYYY-MM-DD. Handles:
    - ISO datetime: 2025-09-22T07:00:12+00:00
    - ISO date: 2026-03-07
    - DD/MM/YYYY: 27/02/2026
    - DD.MM.YY: 23.03.22
    - DD.MM.YYYY: 23.03.2022
    """
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if not s:
        return ""

    # ISO datetime with T
    if "T" in s:
        s = s.split("T")[0]

    # Already YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # DD.MM.YY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$", s)
    if m:
        y = m.group(3)
        if len(y) == 2:
            y = "20" + y if int(y) < 50 else "19" + y
        return f"{y}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # Fallback: try pandas
    try:
        parsed = pd.to_datetime(s, dayfirst=True)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return s


def _merge_old_new(old_file, new_df, institut, date_col="date"):
    """Merge old CSV with new scrape, deduplicating by subject+date."""
    if not old_file.exists():
        return new_df

    old = pd.read_csv(old_file)
    if "institut" not in old.columns:
        old["institut"] = institut

    # Standardize columns — keep only common ones plus institut
    common_cols = ["date", "subject", "link", "institut"]
    for col in common_cols:
        if col not in old.columns:
            old[col] = ""
        if col not in new_df.columns:
            new_df[col] = ""

    old_subset = old[common_cols]
    new_subset = new_df[common_cols]

    combined = pd.concat([old_subset, new_subset], ignore_index=True)
    # Deduplicate on subject (titles should be unique enough)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["subject"], keep="last")
    dupes = before - len(combined)
    if dupes > 0:
        print(f"    Removed {dupes} duplicates")
    return combined


def merge():
    # Load all new scrapes
    new_files = list(DATA_DIR.glob("*_polls.csv"))
    if not new_files:
        print("No CSV files found in data/")
        return

    dfs = []
    for f in new_files:
        if f.name == "sondages_france.csv":
            continue
        try:
            df = pd.read_csv(f)
            if "institut" not in df.columns:
                name = f.stem.replace("_polls", "").upper().replace("_", " ")
                df["institut"] = name
            print(f"  {f.name}: {len(df)} rows (new)")
            dfs.append((f.stem, df))
        except Exception as e:
            print(f"  Error reading {f.name}: {e}")

    # Institutes that need old+new merge
    old_mappings = {
        "ipsos": ("ipsos_polls.csv", "IPSOS"),
        "ifop": ("ifop_polls.csv", "IFOP"),
        "harris_interactive": ("harris interactive_polls.csv", "HARRIS INTERACTIVE"),
    }

    all_dfs = []
    for stem, df in dfs:
        if stem.replace("_polls", "") in old_mappings:
            key = stem.replace("_polls", "")
            old_filename, institut = old_mappings[key]
            old_path = OLD_DIR / old_filename
            print(f"    Merging with old data: {old_path.name}")
            merged = _merge_old_new(old_path, df, institut)
            print(f"    -> {len(merged)} rows after merge")
            all_dfs.append(merged)
        else:
            common_cols = ["date", "subject", "link", "institut"]
            for col in common_cols:
                if col not in df.columns:
                    df[col] = ""
            all_dfs.append(df[common_cols])

    final = pd.concat(all_dfs, ignore_index=True)
    final = final[["date", "institut", "subject", "link"]]

    # Normalize all dates to YYYY-MM-DD
    print("\n  Normalizing dates...")
    before_empty = (final["date"].isna() | (final["date"].astype(str).str.strip() == "")).sum()
    final["date"] = final["date"].apply(normalize_date)
    after_empty = (final["date"] == "").sum()
    print(f"    Dates missing: {before_empty} -> {after_empty}")

    # Sort by date descending
    final = final.sort_values("date", ascending=False, na_position="last", key=lambda x: x.str.strip())

    out = DATA_DIR / "sondages_france.csv"
    final.to_csv(out, index=False, encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"  TOTAL: {len(final)} polls -> {out}")
    print(f"{'='*50}")
    print(f"\nBy institute:")
    for inst, count in final["institut"].value_counts().items():
        print(f"  {inst:25s} {count:>6}")
    return final


if __name__ == "__main__":
    merge()
