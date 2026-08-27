"""Extraction du jeu de données réel INSEE — fécondité/naissances, France
entière, séries longues 1957-2026. Projet personnel (Track B), voir
../../PROTOCOLE_ANALYSE_FERTILITE.md.

Source : API officielle INSEE Melodi (api.insee.fr/melodi), dataset
DS_NAISSANCES_FECONDITE_SERIES (succède à DS_FECONDITE, obsolète — vérifié
en direct le 27/08/2026, pas déduit du lien trouvé sur data.gouv.fr).

Les 6 indicateurs disponibles (EC_MEASURE) ont été identifiés par
recoupement entre le nom du code et la valeur réelle observée pour 2020
(pas par une documentation officielle des libellés, introuvable sur cette
API) : ex. FERIND=182 en 2020 correspond à l'indicateur conjoncturel de
fécondité x100 (1,82 enfant/femme, chiffre INSEE connu et stable pour
2020) ; AVERAGE_MOTHER=30,8 correspond à l'âge moyen à la maternité
(chiffre INSEE connu pour 2020). Si l'un de ces recoupements s'avère faux
en croisant d'autres années, le corriger ici, pas dans le protocole.
"""
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://api.insee.fr/melodi/data/DS_NAISSANCES_FECONDITE_SERIES"
GEO_FRANCE = "2025-FRANCE-F"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "insee_fecondite_france.csv"

MESURES = {
    "FERIND": "Indicateur conjoncturel de fécondité (÷100, ex. 182 = 1,82 enfant/femme)",
    "FERRT": "Taux de fécondité par âge (pour 100 femmes de la tranche)",
    "BRTHRT": "Taux brut de natalité (pour 1000 habitants)",
    "AVERAGE_MOTHER": "Âge moyen à la maternité (années)",
    "LVB_PLACE_RES": "Naissances vivantes, lieu de résidence de la mère",
    "LVB_PLACE_REG": "Naissances vivantes, lieu d'enregistrement",
}

LIBELLES_AGE = {
    "_T": "Toutes tranches", "_Z": "Non applicable",
    "Y15T24": "15-24 ans", "Y25T29": "25-29 ans", "Y25T34": "25-34 ans",
    "Y30T34": "30-34 ans", "Y35T39": "35-39 ans", "Y35T49": "35-49 ans",
    "Y40T50": "40-50 ans",
}


def telecharger_serie_france(force=False):
    """Une seule page suffit pour le niveau France entière (889 lignes,
    confirmé isLast=True le 27/08/2026) — pas besoin de paginer, contrairement
    à une extraction multi-niveaux (région/département) qui dépasserait
    10 000 lignes par page."""
    if not force and CACHE_FILE.exists():
        return pd.read_csv(CACHE_FILE, dtype={"annee": str})

    reponse = requests.get(API_URL, params={"GEO": GEO_FRANCE, "page": 1}, timeout=30)
    reponse.raise_for_status()
    donnees = reponse.json()
    if not donnees["paging"].get("isLast", False):
        raise RuntimeError(
            "Plus d'une page de résultats pour GEO=France entière : le volume de "
            "données a changé depuis la vérification du 27/08/2026, revoir la pagination."
        )

    lignes = []
    for obs in donnees["observations"]:
        dims = obs["dimensions"]
        mesure = dims["EC_MEASURE"]
        if mesure not in MESURES:
            continue  # mesure non identifiee/documentee, ecartee plutot que devinee
        lignes.append({
            "annee": dims["TIME_PERIOD"], "mesure": mesure,
            "libelle_mesure": MESURES[mesure],
            "tranche_age": dims["AGE"], "libelle_age": LIBELLES_AGE.get(dims["AGE"], dims["AGE"]),
            "valeur": obs["measures"]["OBS_VALUE_NIVEAU"]["value"],
            "statut": dims.get("OBS_STATUS", ""),
        })

    df = pd.DataFrame(lignes)
    # Series mensuelles/infra-annuelles (ex. "2026-06") ecartees : le protocole
    # vise des tendances longues annuelles, pas la volatilite mensuelle recente.
    df = df[df["annee"].str.match(r"^\d{4}$")].copy()
    df["annee"] = df["annee"].astype(int)
    df = df.sort_values(["mesure", "tranche_age", "annee"]).reset_index(drop=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE_FILE, index=False, encoding="utf-8")
    return df


def serie_fecondite_par_age(df):
    """Taux de fécondité par tranche d'âge quinquennale (FERRT), la série
    la plus directement utile à la question de décision du protocole."""
    return df[(df["mesure"] == "FERRT") & (df["tranche_age"] != "_T")].pivot(
        index="annee", columns="libelle_age", values="valeur"
    )


def serie_age_moyen_maternite(df):
    return df[df["mesure"] == "AVERAGE_MOTHER"].set_index("annee")["valeur"]


def main():
    df = telecharger_serie_france()
    print(f"{len(df)} observations annuelles, France entière, {df['annee'].min()}-{df['annee'].max()}")
    print(f"Mesures : {sorted(df['mesure'].unique())}")

    fecondite = serie_fecondite_par_age(df)
    print("\nTaux de fécondité par âge (dernières années disponibles) :")
    print(fecondite.tail(5).to_string())

    age_moyen = serie_age_moyen_maternite(df)
    print(f"\nÂge moyen à la maternité, {age_moyen.index.min()} -> {age_moyen.index.max()} : "
          f"{age_moyen.iloc[0]:.1f} -> {age_moyen.iloc[-1]:.1f} ans")


if __name__ == "__main__":
    main()
