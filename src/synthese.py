"""Synthèse par catégorie — niveau de preuve + direction du résultat, sans
IA (à la demande de Gisèle). Ajouté le 27/08, réponses aux 3 pistes
"rendre le projet plus utile" : niveau de preuve visible, synthèse
croisée par catégorie. (Les notes perso sont dans notes_perso.py.)

Best-effort déclaratif, assumé comme tel : classer un résultat en
"positif/négatif" à partir de quelques mots-clés anglais n'est pas une
vraie méta-analyse, juste une première lecture rapide. Toujours lire le
résumé complet (ou l'étude entière) avant de trancher — voir la grille de
vérification du protocole.
"""
# Ordre = du plus fort au plus faible ; le premier type d'étude trouvé
# dans le texte determine le niveau (une étude peut être décrite par
# plusieurs mots, ex. "randomized ... systematic review" cite les deux,
# on garde le plus fort des deux).
NIVEAUX_PREUVE = [
    (1, "Fort (méta-analyse / revue systématique)", "🟢", ["meta-analysis", "systematic review"]),
    (2, "Bon (essai contrôlé randomisé)", "🟡", ["randomized", "randomised", "double-blind", "placebo-controlled"]),
    (3, "Modéré (étude de cohorte / prospective)", "🟠", ["cohort", "prospective study"]),
    (4, "Faible (cas-témoins / rétrospective)", "🔴", ["case-control", "retrospective"]),
]

MOTS_DIRECTION_NEGATIVE = [
    "no significant", "no effect", "no association", "did not improve",
    "insufficient evidence", "ineffective", "no difference", "not effective",
]
MOTS_DIRECTION_POSITIVE = [
    "improved", "improves", "increased", "beneficial", "effective",
    "significant improvement", "enhanced", "reduced risk", "positive effect",
]


def _texte_ou_vide(x):
    """Un champ vide relu depuis un CSV pandas est parfois un NaN (float),
    pas une chaîne vide -- voir le bug équivalent dans evaluer_niveau_preuve."""
    if not x or not isinstance(x, str):
        return ""
    return x


def evaluer_niveau_preuve(type_etude_texte):
    """Retourne {"niveau": int|None, "libelle": str, "emoji": str}.
    niveau=None si le type d'étude n'a pas été trouvé dans le résumé
    (voir extraction_details_etudes.py) — jamais un niveau deviné.

    Bug réel trouvé en testant : un champ vide relu depuis un CSV pandas
    n'est pas toujours une chaîne vide, parfois un NaN (float) selon la
    colonne — `not type_etude_texte` seul ne suffit pas à l'attraper."""
    if not type_etude_texte or not isinstance(type_etude_texte, str):
        return {"niveau": None, "libelle": "Non déterminé (type non trouvé)", "emoji": "⚪"}
    texte = type_etude_texte.lower()
    for niveau, libelle, emoji, mots_cles in NIVEAUX_PREUVE:
        if any(mot in texte for mot in mots_cles):
            return {"niveau": niveau, "libelle": libelle, "emoji": emoji}
    return {"niveau": None, "libelle": "Non classé (type non reconnu)", "emoji": "⚪"}


def classer_direction(texte):
    """Heuristique par mots-clés, PAS une analyse de sentiment fiable —
    retourne "positif", "negatif", "mixte" (les deux types de mots présents,
    à lire avec attention) ou "indetermine" (aucun mot-clé reconnu, pas
    forcément neutre — juste pas assez de signal pour classer)."""
    texte_lower = (texte or "").lower()
    a_negatif = any(mot in texte_lower for mot in MOTS_DIRECTION_NEGATIVE)
    a_positif = any(mot in texte_lower for mot in MOTS_DIRECTION_POSITIVE)
    if a_negatif and a_positif:
        return "mixte"
    if a_negatif:
        return "negatif"
    if a_positif:
        return "positif"
    return "indetermine"


def synthetiser_categorie(df_categorie):
    """Résumé chiffré d'un ensemble d'études (une catégorie/un sujet) :
    répartition par niveau de preuve et par direction. Jamais une phrase
    de conclusion générale inventée — seulement des comptages vérifiables
    ligne par ligne dans le DataFrame source."""
    n = len(df_categorie)
    if n == 0:
        return {"nb_etudes": 0, "par_niveau_preuve": {}, "par_direction": {}}

    par_niveau = {}
    par_direction = {}
    for _, ligne in df_categorie.iterrows():
        niveau_info = evaluer_niveau_preuve(ligne.get("type_etude", ""))
        libelle_niveau = niveau_info["libelle"]
        par_niveau[libelle_niveau] = par_niveau.get(libelle_niveau, 0) + 1

        texte_pour_direction = " ".join(filter(None, [
            _texte_ou_vide(ligne.get("resume_bref")),
            _texte_ou_vide(ligne.get("conclusion")),
        ]))
        direction = classer_direction(texte_pour_direction)
        par_direction[direction] = par_direction.get(direction, 0) + 1

    return {"nb_etudes": n, "par_niveau_preuve": par_niveau, "par_direction": par_direction}


def main():
    import pandas as pd
    from pathlib import Path
    donnees_dir = Path(__file__).resolve().parent.parent / "data"
    df = pd.read_csv(donnees_dir / "pubmed_etudes.csv", dtype=str).merge(
        pd.read_csv(donnees_dir / "pubmed_details_cliniques.csv", dtype=str), on="pmid", how="left",
    )
    for sujet in sorted(df["sujet"].unique())[:3]:
        sous = df[df["sujet"] == sujet]
        resume = synthetiser_categorie(sous)
        print(f"\n=== {sujet} ({resume['nb_etudes']} études) ===")
        print("  Niveau de preuve :", resume["par_niveau_preuve"])
        print("  Direction        :", resume["par_direction"])


if __name__ == "__main__":
    main()
