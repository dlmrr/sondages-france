"""Web app to browse French polling data."""
import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
from pathlib import Path

app = Flask(__name__)
DATA_DIR = Path(__file__).resolve().parent / "data"
ENRICHED_PATH = DATA_DIR / "sondages_enriched.csv"
PLAIN_PATH = DATA_DIR / "sondages_france.csv"


# Cache loaded data (reloads on file change locally, loads once on serverless)
_cache = {"df": None, "mtime": 0, "instituts": [], "themes": []}


def get_data():
    # Prefer enriched CSV if it exists
    data_path = ENRICHED_PATH if ENRICHED_PATH.exists() else PLAIN_PATH
    try:
        mtime = os.path.getmtime(data_path)
    except OSError:
        mtime = 0
    if _cache["df"] is None or mtime != _cache["mtime"]:
        df = pd.read_csv(data_path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
        df = df.sort_values("date", ascending=False, na_position="last")

        _cache["df"] = df
        _cache["mtime"] = mtime
        _cache["instituts"] = sorted(df["institut"].dropna().unique().tolist())
        if "theme_name" in df.columns:
            _cache["themes"] = sorted(df["theme_name"].dropna().unique().tolist())
        else:
            _cache["themes"] = []
        print(f"Reloaded {len(df)} polls (file changed)")
    return _cache["df"], _cache["instituts"], _cache["themes"]


# Initial load
get_data()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/polls")
def api_polls():
    df, _, _ = get_data()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search", "").strip()
    institut = request.args.get("institut", "")
    theme = request.args.get("theme", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    sort_asc = request.args.get("sort_asc", "0") == "1"

    filtered = df

    if search:
        mask = filtered["subject"].str.contains(search, case=False, na=False)
        filtered = filtered[mask]

    if institut:
        filtered = filtered[filtered["institut"] == institut]

    if theme and "theme_name" in filtered.columns:
        filtered = filtered[filtered["theme_name"] == theme]

    if date_from:
        filtered = filtered[filtered["date"] >= pd.to_datetime(date_from)]

    if date_to:
        filtered = filtered[filtered["date"] <= pd.to_datetime(date_to)]

    filtered = filtered.sort_values("date", ascending=sort_asc, na_position="last")

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = filtered.iloc[start:end]

    has_themes = "theme_name" in df.columns

    records = []
    for _, row in page_data.iterrows():
        rec = {
            "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "",
            "institut": row["institut"] if pd.notna(row["institut"]) else "",
            "subject": row["subject"] if pd.notna(row["subject"]) else "",
            "link": row["link"] if pd.notna(row["link"]) else "",
        }
        if has_themes:
            rec["theme"] = row.get("theme_name", "")
        records.append(rec)

    return jsonify({
        "polls": records,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@app.route("/api/stats")
def api_stats():
    df, _, themes = get_data()
    has_themes = "theme_name" in df.columns

    stats = {
        "total": len(df),
        "by_institut": df["institut"].value_counts().to_dict(),
        "date_range": {
            "min": df["date"].min().strftime("%Y-%m-%d") if pd.notna(df["date"].min()) else "",
            "max": df["date"].max().strftime("%Y-%m-%d") if pd.notna(df["date"].max()) else "",
        },
        "by_year": df[df["date"].notna()].groupby(df["date"].dt.year).size().to_dict(),
    }

    if has_themes:
        stats["themes"] = themes
        stats["by_theme"] = df["theme_name"].value_counts().to_dict()

    return jsonify(stats)


if __name__ == "__main__":
    df, _, _ = get_data()
    print(f"Loaded {len(df)} polls")
    app.run(debug=True, port=5000)
