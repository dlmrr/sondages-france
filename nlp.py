"""
NLP pipeline: classify polls into curated thematic categories.
Uses sentence-transformers for semantic similarity.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent / "data"
MERGED_CSV = DATA_DIR / "sondages_france.csv"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.npy"
ENRICHED_CSV = DATA_DIR / "sondages_enriched.csv"
THEMES_FILE = DATA_DIR / "themes.json"

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Curated taxonomy — each category has a name and description sentences
# that capture the semantic field. The model matches poll subjects to these.
CATEGORIES = {
    "Elections": [
        "élections présidentielles législatives municipales européennes",
        "intentions de vote sondage électoral candidats scrutin",
        "premier tour second tour résultats électoraux campagne",
    ],
    "Popularite politique": [
        "cote de popularité image des personnalités politiques",
        "confiance envers le président baromètre politique",
        "tableau de bord des personnalités opinion favorable défavorable",
        "bilan du président Macron Hollande Sarkozy mandat quinquennat",
    ],
    "Politique": [
        "politique gouvernement assemblée nationale réforme loi",
        "gauche droite opposition majorité parti politique",
        "débat politique institutions République motion de censure",
    ],
    "Economie": [
        "économie pouvoir d'achat inflation prix consommation",
        "budget des ménages dépenses épargne fiscalité impôts",
        "crise économique récession croissance conjoncture",
        "modes de consommation achats commerce dépenses",
    ],
    "Entreprises": [
        "entreprises PME ETI TPE dirigeants entrepreneurs",
        "emploi chômage salariés travail recrutement salaires",
        "management ressources humaines conditions de travail",
        "rupture conventionnelle licenciement contrat de travail",
    ],
    "Sante": [
        "santé système de santé hôpital médecins soins",
        "maladie médicaments vaccination pandémie épidémie",
        "bien-être prévention accès aux soins déserts médicaux",
        "infertilité procréation natalité grossesse maternité",
    ],
    "Covid-19": [
        "covid coronavirus pandémie confinement couvre-feu",
        "vaccin vaccination pass sanitaire gestes barrières",
        "crise sanitaire covid-19 variants protocole sanitaire",
    ],
    "Environnement": [
        "environnement écologie climat réchauffement climatique",
        "énergie transition énergétique nucléaire renouvelables",
        "biodiversité pollution développement durable COP",
    ],
    "Education": [
        "éducation école université étudiants enseignants",
        "jeunes jeunesse génération adolescents lycéens",
        "formation apprentissage diplôme baccalauréat",
    ],
    "Numerique": [
        "numérique internet réseaux sociaux digital technologie",
        "intelligence artificielle données cybersécurité",
        "smartphone applications objets connectés e-commerce",
    ],
    "Societe": [
        "société valeurs religion laïcité identité",
        "immigration intégration diversité discrimination",
        "mariage famille moeurs évolution sociétale",
        "les Français et leur opinion regard moral optimisme",
        "sexualité couple vie privée comportements sociaux",
    ],
    "Securite": [
        "sécurité délinquance criminalité police justice",
        "terrorisme radicalisation insécurité violence",
        "prison peine réforme pénale forces de l'ordre",
    ],
    "International": [
        "politique étrangère relations internationales géopolitique",
        "guerre conflit armée diplomatie OTAN défense",
        "pays étranger Russie Ukraine Chine États-Unis Afrique",
        "Union européenne Brexit parlement européen Bruxelles",
    ],
    "Egalite femmes-hommes": [
        "femmes égalité hommes-femmes féminisme parité",
        "harcèlement violences sexistes droits des femmes",
        "genre mixité plafond de verre inégalités",
    ],
    "Sport et culture": [
        "sport football rugby jeux olympiques compétition match",
        "formule 1 F1 grand prix pilote course automobile tennis",
        "culture cinéma musique télévision médias festival",
        "loisirs vacances tourisme divertissement spectacle",
    ],
    "Territoires": [
        "territoire communes départements régions rural",
        "municipales collectivités locales maire décentralisation",
        "mobilité transports logement urbanisme aménagement",
    ],
    "Agriculture": [
        "alimentation agriculture alimentaire bio pesticides",
        "agriculteurs PAC élevage circuits courts",
        "nutrition santé alimentaire consommation responsable",
    ],
    "Retraites": [
        "retraites réforme des retraites système de retraite",
        "protection sociale sécurité sociale pension cotisations",
        "âge de départ régimes spéciaux solidarité",
    ],
    "Logement": [
        "logement immobilier loyer propriétaire locataire",
        "copropriété habitat résidence HLM construction",
        "prix immobiliers marché immobilier déménagement",
    ],
    "Transports": [
        "transports mobilité voiture automobile circulation",
        "train SNCF métro bus vélo transport en commun",
        "route permis de conduire covoiturage trafic",
    ],
}


def load_polls():
    with open(MERGED_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_embeddings(texts, model, batch_size=256):
    return model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )


def run_pipeline():
    """Classify all polls into curated categories using semantic similarity."""
    polls = load_polls()
    subjects = [p["subject"] for p in polls]
    print(f"Loaded {len(subjects)} polls")
    sys.stdout.flush()

    # Load model
    print(f"Loading model '{MODEL_NAME}'...")
    sys.stdout.flush()
    model = SentenceTransformer(MODEL_NAME)

    # Embed category descriptions
    cat_names = list(CATEGORIES.keys())
    cat_texts = []
    for name in cat_names:
        # Join all description sentences into one text per category
        cat_texts.append(" . ".join(CATEGORIES[name]))

    print(f"Embedding {len(cat_names)} category descriptions...")
    sys.stdout.flush()
    cat_embeddings = model.encode(cat_texts, normalize_embeddings=True)

    # Embed poll subjects
    if EMBEDDINGS_FILE.exists():
        print("Loading cached embeddings...")
        poll_embeddings = np.load(EMBEDDINGS_FILE)
        if len(poll_embeddings) != len(subjects):
            print("Cache size mismatch, recomputing...")
            poll_embeddings = compute_embeddings(subjects, model)
            np.save(EMBEDDINGS_FILE, poll_embeddings)
    else:
        print(f"Computing embeddings for {len(subjects)} subjects...")
        sys.stdout.flush()
        poll_embeddings = compute_embeddings(subjects, model)
        np.save(EMBEDDINGS_FILE, poll_embeddings)

    print(f"Embeddings shape: {poll_embeddings.shape}")

    # Classify: cosine similarity (embeddings are normalized, so dot product = cosine)
    print("Classifying polls...")
    sys.stdout.flush()
    similarity = poll_embeddings @ cat_embeddings.T  # (n_polls, n_categories)
    assignments = similarity.argmax(axis=1)
    confidences = similarity.max(axis=1)

    # Stats
    from collections import Counter
    counts = Counter(assignments)
    print(f"\n--- Categories ({len(cat_names)}) ---")
    for idx in sorted(counts, key=counts.get, reverse=True):
        avg_conf = np.mean(confidences[assignments == idx])
        print(f"  {cat_names[idx]:40s} {counts[idx]:5d}  (avg sim: {avg_conf:.3f})")
    sys.stdout.flush()

    # Save enriched CSV
    print("\nSaving results...")
    with open(ENRICHED_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "institut", "subject", "link", "theme_name"])
        for poll, cat_idx in zip(polls, assignments):
            writer.writerow([
                poll["date"],
                poll["institut"],
                poll["subject"],
                poll["link"],
                cat_names[int(cat_idx)],
            ])

    # Save themes metadata
    themes_data = {
        "categories": cat_names,
        "counts": {cat_names[k]: v for k, v in counts.items()},
    }
    with open(THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(themes_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Saved:")
    print(f"  {ENRICHED_CSV}")
    print(f"  {THEMES_FILE}")
    return themes_data


if __name__ == "__main__":
    run_pipeline()
