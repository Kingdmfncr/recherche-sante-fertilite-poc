"""Décompose une problématique de recherche en catégories interrogeables
sur PubMed — deux méthodes, ajoutées le 27/08.

**Méthode par mots-clés (par défaut, sans IA)** : cartographie déclarative
(`config/categories_problematique.yaml`), même principe que les autres
règles déclaratives du jour (`extraction_rules.yaml`, `patterns_cliniques.yaml`).
Aucune clé API, aucune dépendance externe, résultat déterministe et
testable. Gisèle a demandé "ce n'est pas possible de faire sans IA ?" —
si, et c'est même plus robuste pour les 19 sujets déjà couverts.

**Méthode par IA (optionnelle, Claude BYOK)** : pour une problématique qui
sort du champ des catégories déjà connues. Même principe de groundage que
rag_agent.py des autres projets du jour : l'IA ne propose QUE des noms de
catégories et des requêtes, jamais un résultat scientifique. Les vraies
études viennent toujours de l'API PubMed réelle. Une réponse mal formée
retourne None, jamais une décomposition devinée.
"""
import json
import unicodedata
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_config_categories_cache = None


def _load_categories():
    global _config_categories_cache
    if _config_categories_cache is None:
        with open(CONFIG_DIR / "categories_problematique.yaml", encoding="utf-8") as f:
            _config_categories_cache = yaml.safe_load(f)["categories"]
    return _config_categories_cache


def _normaliser(texte):
    """Minuscules, sans accents, pour un matching robuste aux variations
    d'orthographe (ex. 'stéatose' vs 'steatose')."""
    texte = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in texte if not unicodedata.combining(c))


def decomposer_par_mots_cles(problematique):
    """Retourne les catégories dont au moins un mot-clé déclencheur
    apparaît dans la problématique. Liste vide (pas None) si aucune
    catégorie connue ne correspond — un cas normal, pas une erreur."""
    if not problematique:
        return []
    texte_normalise = _normaliser(problematique)
    trouvees = []
    for categorie in _load_categories():
        mots_cles_normalises = [_normaliser(m) for m in categorie["mots_cles"]]
        if any(mot in texte_normalise for mot in mots_cles_normalises):
            trouvees.append({
                "nom_categorie": categorie["nom_categorie"],
                "requete_pubmed": categorie["requete_pubmed"],
            })
    return trouvees


def decomposer_problematique(problematique, api_key, nb_categories=5):
    """Décomposition par IA (Claude, BYOK) — optionnelle, voir docstring du
    module. Retourne None si pas de clé, appel échoué, ou réponse mal formée."""
    if not api_key or not problematique:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        prompt = (
            f"Tu es un assistant de recherche bibliographique médicale. "
            f"Décompose la problématique suivante en {nb_categories} catégories "
            f"de recherche distinctes et complémentaires, chacune interrogeable "
            f"indépendamment sur PubMed.\n\n"
            f"Problématique : {problematique}\n\n"
            f"Réponds UNIQUEMENT avec un JSON valide : une liste d'objets ayant "
            f"exactement ces deux clés : \"nom_categorie\" (nom court en français, "
            f"pour affichage) et \"requete_pubmed\" (requête de recherche PubMed "
            f"en anglais, 3 à 6 mots-clés, sans guillemets ni opérateurs booléens "
            f"complexes). Aucun texte avant ou après le JSON."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=700, temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parser_reponse_json(msg.content[0].text)
    except Exception:
        return None


def _parser_reponse_json(texte):
    """Fonction pure (testable sans réseau) : nettoie un éventuel bloc
    markdown ```json autour de la réponse et valide la structure attendue.
    Une seule catégorie mal formée invalide toute la décomposition plutôt
    que de retourner une liste partiellement fiable."""
    texte = texte.strip()
    if texte.startswith("```"):
        texte = texte.split("\n", 1)[1] if "\n" in texte else texte
        if texte.endswith("```"):
            texte = texte.rsplit("```", 1)[0]
    texte = texte.strip()

    try:
        categories = json.loads(texte)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(categories, list) or not categories:
        return None
    for categorie in categories:
        if not isinstance(categorie, dict):
            return None
        if "nom_categorie" not in categorie or "requete_pubmed" not in categorie:
            return None
    return categories


def explorer_problematique(problematique, api_key=None, max_resultats_par_categorie=5, methode="mots_cles"):
    """Point d'entrée du dashboard : décompose la problématique (par
    mots-clés par défaut, sans IA) puis lance une vraie recherche PubMed
    par catégorie (recherche_pubmed.py, données réelles). Retourne
    (categories, dict[nom_categorie -> DataFrame], methode_utilisee).

    methode="mots_cles" (défaut) : aucune clé API nécessaire.
    methode="ia" : nécessite api_key, retombe sur mots_cles si la
    décomposition IA échoue plutôt que de ne rien retourner du tout.

    Ne cache jamais rien (chaque problématique est différente) et ne
    touche jamais le cache partagé des 19 sujets suivis."""
    import recherche_pubmed as rp

    methode_utilisee = methode
    if methode == "ia":
        categories = decomposer_problematique(problematique, api_key)
        if not categories:
            categories = decomposer_par_mots_cles(problematique)
            methode_utilisee = "mots_cles (repli, IA indisponible ou échouée)"
    else:
        categories = decomposer_par_mots_cles(problematique)

    if not categories:
        return None, {}, methode_utilisee

    resultats_par_categorie = {}
    for categorie in categories:
        df = rp.rechercher_requete_libre(
            categorie["requete_pubmed"], max_resultats=max_resultats_par_categorie,
        )
        resultats_par_categorie[categorie["nom_categorie"]] = df
    return categories, resultats_par_categorie, methode_utilisee


def main():
    problematique = (
        "Quels facteurs modifiables soutiennent la fertilité et la santé "
        "cardiovasculaire chez les femmes après 35 ans, en tenant compte "
        "du sommeil et de l'exposition environnementale ?"
    )
    print(f"Problématique : {problematique}\n")

    categories, resultats, methode = explorer_problematique(problematique, methode="mots_cles")
    print(f"Méthode utilisée : {methode}")
    if not categories:
        print("Aucune catégorie connue ne correspond à cette problématique.")
        return

    for categorie in categories:
        nom = categorie["nom_categorie"]
        df = resultats[nom]
        print(f"\n=== {nom} ({categorie['requete_pubmed']}) : {len(df)} étude(s) ===")
        for _, ligne in df.iterrows():
            print(f"  [{ligne['pmid']}] {ligne['titre'][:80]}")


if __name__ == "__main__":
    main()
