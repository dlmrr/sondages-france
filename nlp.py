"""
NLP pipeline: extract keywords and themes from poll subjects.
Uses sentence-transformers for embeddings, sklearn for clustering,
TF-IDF for keyword extraction.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from nltk.corpus import stopwords
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

DATA_DIR = Path(__file__).parent / "data"
MERGED_CSV = DATA_DIR / "sondages_france.csv"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.npy"
THEMES_FILE = DATA_DIR / "themes.json"
ENRICHED_CSV = DATA_DIR / "sondages_enriched.csv"

# French stopwords + common poll filler words
FRENCH_STOPS = set(stopwords.words("french"))
EXTRA_STOPS = {
    "français", "françaises", "france", "sondage", "baromètre", "enquête",
    "étude", "vague", "résultats", "regard", "avis", "opinion", "opinions",
    "perception", "perceptions", "observatoire", "tableau", "bord",
    "ifop", "ipsos", "elabe", "bva", "odoxa", "harris", "csa", "opinionway",
    "edition", "édition", "n°", "numéro",
}

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
N_THEMES = 35


def load_polls():
    with open(MERGED_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_text(text):
    """Normalize unicode and clean up text for NLP."""
    # Fix mojibake-style characters (common in French scraping)
    text = unicodedata.normalize("NFC", text)
    # Remove special chars but keep accented letters
    text = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçœæ'-]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords_tfidf(subjects, top_n=5):
    """Extract top keywords per document using TF-IDF."""
    all_stops = FRENCH_STOPS | EXTRA_STOPS

    vectorizer = TfidfVectorizer(
        stop_words=list(all_stops),
        max_features=10000,
        min_df=2,
        max_df=0.3,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zàâäéèêëïîôùûüÿçœæ]{3,}\b",
    )

    cleaned = [normalize_text(s).lower() for s in subjects]
    tfidf_matrix = vectorizer.fit_transform(cleaned)
    feature_names = vectorizer.get_feature_names_out()

    keywords_per_doc = []
    for i in range(tfidf_matrix.shape[0]):
        row = tfidf_matrix[i].toarray().flatten()
        top_indices = row.argsort()[-top_n:][::-1]
        kws = [feature_names[j] for j in top_indices if row[j] > 0]
        keywords_per_doc.append(kws)

    return keywords_per_doc, vectorizer, tfidf_matrix


def compute_embeddings(subjects, batch_size=256):
    """Compute sentence embeddings for all subjects."""
    print(f"Loading model '{MODEL_NAME}'...")
    sys.stdout.flush()
    model = SentenceTransformer(MODEL_NAME)

    print(f"Computing embeddings for {len(subjects)} subjects...")
    sys.stdout.flush()
    embeddings = model.encode(
        subjects,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings


def cluster_themes(embeddings, n_clusters=N_THEMES):
    """Cluster embeddings into themes using KMeans."""
    print(f"Clustering into {n_clusters} themes...")
    sys.stdout.flush()
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)
    return labels, km


def name_themes(subjects, labels, n_clusters):
    """Auto-name each theme cluster using top TF-IDF terms."""
    all_stops = FRENCH_STOPS | EXTRA_STOPS

    theme_names = {}
    for cluster_id in range(n_clusters):
        cluster_subjects = [s for s, l in zip(subjects, labels) if l == cluster_id]
        if not cluster_subjects:
            theme_names[cluster_id] = f"Theme {cluster_id}"
            continue

        vectorizer = TfidfVectorizer(
            stop_words=list(all_stops),
            max_features=1000,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[a-zàâäéèêëïîôùûüÿçœæ]{3,}\b",
        )
        try:
            tfidf = vectorizer.fit_transform([normalize_text(s).lower() for s in cluster_subjects])
            mean_tfidf = tfidf.mean(axis=0).A1
            top_indices = mean_tfidf.argsort()[-5:][::-1]
            top_terms = [vectorizer.get_feature_names_out()[i] for i in top_indices]
            theme_names[cluster_id] = " / ".join(top_terms[:3])
        except ValueError:
            theme_names[cluster_id] = f"Theme {cluster_id}"

    return theme_names


def run_pipeline():
    """Full NLP pipeline: embeddings, clustering, keywords, save results."""
    polls = load_polls()
    subjects = [p["subject"] for p in polls]
    print(f"Loaded {len(subjects)} polls")
    sys.stdout.flush()

    # Step 1: Embeddings
    if EMBEDDINGS_FILE.exists():
        print("Loading cached embeddings...")
        embeddings = np.load(EMBEDDINGS_FILE)
        if len(embeddings) != len(subjects):
            print("Cache size mismatch, recomputing...")
            embeddings = compute_embeddings(subjects)
            np.save(EMBEDDINGS_FILE, embeddings)
    else:
        embeddings = compute_embeddings(subjects)
        np.save(EMBEDDINGS_FILE, embeddings)
    print(f"Embeddings shape: {embeddings.shape}")

    # Step 2: Clustering
    labels, km = cluster_themes(embeddings)

    # Step 3: Name themes
    theme_names = name_themes(subjects, labels, N_THEMES)
    print("\n--- Discovered Themes ---")
    theme_counts = Counter(labels)
    for cid in sorted(theme_counts, key=theme_counts.get, reverse=True):
        print(f"  [{cid:2d}] ({theme_counts[cid]:5d}) {theme_names[cid]}")
    sys.stdout.flush()

    # Step 4: Keywords per poll
    print("\nExtracting keywords...")
    sys.stdout.flush()
    keywords_per_doc, _, _ = extract_keywords_tfidf(subjects)

    # Step 5: Save enriched data
    print("Saving results...")
    themes_data = {
        "n_themes": N_THEMES,
        "themes": {str(k): v for k, v in theme_names.items()},
        "theme_counts": {str(k): v for k, v in theme_counts.items()},
    }
    with open(THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(themes_data, f, ensure_ascii=False, indent=2)

    with open(ENRICHED_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "institut", "subject", "link", "theme_id", "theme_name", "keywords"])
        for poll, label, kws in zip(polls, labels, keywords_per_doc):
            writer.writerow([
                poll["date"],
                poll["institut"],
                poll["subject"],
                poll["link"],
                int(label),
                theme_names[int(label)],
                "|".join(kws),
            ])

    print(f"\nDone! Saved:")
    print(f"  {THEMES_FILE}")
    print(f"  {ENRICHED_CSV}")
    print(f"  {EMBEDDINGS_FILE} ({embeddings.nbytes / 1e6:.1f} MB)")
    return themes_data


if __name__ == "__main__":
    run_pipeline()
