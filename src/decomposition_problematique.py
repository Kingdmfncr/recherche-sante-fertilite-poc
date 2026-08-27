"""Décompose une problématique de recherche en catégories interrogeables
sur PubMed, via Claude (BYOK) — étape ajoutée le 27/08, option 2 demandée
par Gisèle : automatiser ce que je faisais manuellement jusque-là (lire la
problématique, choisir des catégories, écrire les requêtes PubMed).

Principe de groundage, même logique que rag_agent.py des autres projets du
jour : Claude ne propose QUE des noms de catégories et des requêtes de
recherche, jamais un résultat scientifique lui-même. Les vraies études et
leurs vrais volumes viennent ensuite de l'API PubMed réelle
(recherche_pubmed.py), jamais de la réponse de l'IA. Si l'appel échoue ou
si la réponse n'est pas un JSON valide et complet, retourne None — jamais
une décomposition inventée de repli qui masquerait l'échec.
"""
import json


def decomposer_problematique(problematique, api_key, nb_categories=5):
    """Retourne une liste de {"nom_categorie": str, "requete_pubmed": str}
    ou None si pas de clé API, appel échoué, ou réponse mal formée."""
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


def explorer_problematique(problematique, api_key, max_resultats_par_categorie=5):
    """Point d'entrée du dashboard : décompose la problématique puis lance
    une vraie recherche PubMed par catégorie (recherche_pubmed.py, données
    réelles). Retourne (categories, dict[nom_categorie -> DataFrame]).
    Ne cache jamais rien (chaque problématique est différente) et ne
    touche jamais le cache partagé des 19 sujets suivis."""
    import recherche_pubmed as rp

    categories = decomposer_problematique(problematique, api_key)
    if not categories:
        return None, {}

    resultats_par_categorie = {}
    for categorie in categories:
        df = rp.rechercher_requete_libre(
            categorie["requete_pubmed"], max_resultats=max_resultats_par_categorie,
        )
        resultats_par_categorie[categorie["nom_categorie"]] = df
    return categories, resultats_par_categorie


def main():
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Pas de ANTHROPIC_API_KEY dans l'environnement, impossible de tester en CLI.")
        return

    problematique = (
        "Quels facteurs modifiables soutiennent la santé cardiovasculaire "
        "chez les femmes après 40 ans ?"
    )
    categories, resultats = explorer_problematique(problematique, api_key, max_resultats_par_categorie=3)
    if not categories:
        print("Décomposition échouée (clé invalide, appel échoué, ou réponse mal formée).")
        return

    for categorie in categories:
        nom = categorie["nom_categorie"]
        df = resultats[nom]
        print(f"\n=== {nom} ({categorie['requete_pubmed']}) : {len(df)} étude(s) ===")
        for _, ligne in df.iterrows():
            print(f"  [{ligne['pmid']}] {ligne['titre'][:80]}")


if __name__ == "__main__":
    main()
