"""Recherche de littérature scientifique réelle (PubMed) — étape 4.3 du
protocole, voir ../../PROTOCOLE_ANALYSE_FERTILITE.md.

Chaque résultat retourné est un vrai PMID, vérifiable individuellement sur
pubmed.ncbi.nlm.nih.gov/{pmid}, jamais une conclusion reformulée sans sa
source. Ne cherche pas à conclure à la place du lecteur : retourne les
études trouvées (titre, revue, date, lien), la lecture et l'interprétation
restent à faire à la main — voir la grille de vérification du protocole
(populations/année/taille d'échantillon avant de généraliser une étude).
"""
import time
from pathlib import Path

import pandas as pd
import requests

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "pubmed_etudes.csv"

# Un sujet suivi = une requête PubMed explicite, jamais un résultat codé en
# dur. Ajouter une ligne ici pour suivre un nouveau sujet du protocole.
SUJETS = {
    "sport_grossesse_cerveau_bebe": "maternal exercise pregnancy fetal brain development",
    "coq10_reserve_ovarienne": "coenzyme Q10 ovarian reserve fertility randomized",
    "vitamine_d_implantation": "vitamin D endometrial implantation IVF",
    "preconception_sante": "preconception care intervention pregnancy outcomes",
    "perinatalite": "perinatal maternal health outcomes intervention",
    # Ajoutés le 27/08 à la demande de Gisèle (compléments spécifiques) :
    "nac_fertilite": "N-acetylcysteine fertility ovarian PCOS randomized",
    "myo_inositol_fertilite": "myo-inositol fertility PCOS oocyte quality randomized",
    "pqq_fertilite": "pyrroloquinoline quinone PQQ fertility oocyte",
    "omega3_dha_grossesse": "omega-3 DHA pregnancy fetal development randomized",
    # Ajoutés le 27/08 suite à la cartographie par volume de la problématique
    # (PROTOCOLE_ANALYSE_FERTILITE.md §3) : deux pistes aussi documentées que
    # la nutrition mais pas encore creusées ici.
    "age_paternel_qualite_sperme": "paternal age sperm quality offspring outcomes",
    "exposition_environnementale": "fertility endocrine disruptor environmental exposure",
    # Creusé le 27/08 : exposition environnementale déclinée en 3 sous-sujets
    # spécifiques et actionnables (la vue d'ensemble ci-dessus reste, mais
    # "perturbateur endocrinien" seul n'aide pas à savoir quoi éviter).
    "bpa_phtalates_fertilite": "BPA phthalates exposure fertility female",
    "pesticides_fertilite": "pesticide exposure fertility reproductive",
    "pollution_air_fertilite": "air pollution PM2.5 fertility reproductive outcomes",
    # Sujets de santé générale ajoutés le 27/08 à la demande de Gisèle —
    # le projet s'appelle "Recherche Santé & Fertilité", pas seulement
    # fertilité.
    "menopause": "menopause hormone lifestyle intervention symptoms randomized",
    "tension_arterielle": "hypertension lifestyle diet intervention randomized",
    "foie_gras_steatose": "non-alcoholic fatty liver disease diet lifestyle intervention randomized",
    "diabete_type2": "type 2 diabetes lifestyle intervention prevention randomized",
    "arthrose": "osteoarthritis supplement diet intervention randomized",
    "arthrite": "rheumatoid arthritis diet supplement intervention randomized",
    # Ajoutés le 27/08 : causes/mécanismes concrets d'infertilité, pas
    # seulement des facteurs modifiables généraux.
    "mycoplasme_fertilite": "mycoplasma genital infection fertility reproductive",
    "trompes_bouchees": "tubal factor infertility blocked fallopian tubes treatment",
    "qualite_ovocytaire": "oocyte quality improvement women fertility randomized",
    "qualite_spermatique": "sperm quality improvement men fertility randomized",
    "cycle_3_mois_spermatogenese": "spermatogenesis cycle duration sperm quality",
    # Ajoutés le 27/08 suite à la lecture croisée des 2 rapports officiels
    # (PROTOCOLE_ANALYSE_FERTILITE.md §14) : le SOPK est la cause médicale la
    # plus fréquente selon le rapport Hamamah, pas encore suivi ici. Les 3
    # autres complètent le parcours (préparer une PMA, préparer une conception
    # naturelle, comprendre les causes d'échec), à la demande de Gisèle.
    "sopk_pcos": "polycystic ovary syndrome PCOS treatment fertility randomized",
    "preparation_pma": "IVF preparation protocol success rate optimization",
    "preparation_grossesse_naturelle": "preconception lifestyle natural fertility optimization",
    "causes_echec_pma": "IVF failure causes implantation recurrent",
}


def rechercher_pmids(requete, max_resultats=5):
    reponse = requests.get(ESEARCH_URL, params={
        "db": "pubmed", "term": requete, "retmax": max_resultats,
        "retmode": "json", "sort": "relevance",
    }, timeout=20)
    reponse.raise_for_status()
    return reponse.json()["esearchresult"]["idlist"]


def _parser_resumes(pmids, resultat_esummary):
    """Fonction pure (testable sans réseau) : transforme le JSON esummary
    brut en lignes propres. Un PMID absent du résultat (rare, erreur NCBI)
    est ignoré plutôt que de produire une ligne à moitié vide."""
    lignes = []
    for pmid in pmids:
        info = resultat_esummary.get(pmid)
        if not info:
            continue
        lignes.append({
            "pmid": pmid, "titre": info.get("title", ""),
            "revue": info.get("fulljournalname", ""), "date": info.get("pubdate", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return lignes


def recuperer_resumes(pmids):
    if not pmids:
        return []
    reponse = requests.get(ESUMMARY_URL, params={
        "db": "pubmed", "id": ",".join(pmids), "retmode": "json",
    }, timeout=20)
    reponse.raise_for_status()
    return _parser_resumes(pmids, reponse.json()["result"])


def rechercher_sujet(cle_sujet, max_resultats=5):
    pmids = rechercher_pmids(SUJETS[cle_sujet], max_resultats)
    resultats = recuperer_resumes(pmids)
    for r in resultats:
        r["sujet"] = cle_sujet
    return resultats


def rechercher_requete_libre(requete_utilisateur, max_resultats=5, enrichir=True):
    """Point d'entrée produit : contrairement à SUJETS (une liste fixe que
    Gisèle choisit), un utilisateur final tape n'importe quel terme
    (complément, sujet de santé) et obtient la même recherche PubMed réelle
    en direct, avec dosage/durée/effet/conclusion extraits — voir
    dashboards/app.py. Pas de dédup contre une liste figée, la requête de
    l'utilisateur EST la requête PubMed."""
    pmids = rechercher_pmids(requete_utilisateur, max_resultats)
    df = pd.DataFrame(recuperer_resumes(pmids))
    if df.empty:
        return df
    df["sujet"] = requete_utilisateur
    if enrichir:
        df = enrichir_avec_details_cliniques(df, utiliser_cache=False)
    return df


def rechercher_tous_les_sujets(max_resultats=5, force=False):
    if not force and CACHE_FILE.exists():
        return pd.read_csv(CACHE_FILE, dtype=str)

    lignes = []
    for cle in SUJETS:
        lignes.extend(rechercher_sujet(cle, max_resultats))
        time.sleep(0.4)  # limite NCBI sans clé API (~3 requetes/s)

    df = pd.DataFrame(lignes)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE_FILE, index=False, encoding="utf-8")
    return df


def enrichir_avec_details_cliniques(df_etudes, force=False, utiliser_cache=True):
    """Ajoute dosage/duree/taille_echantillon/type_etude/effet observe/
    conclusion a chaque etude, via extraction_details_etudes (efetch +
    regex declaratifs + extraction de sections structurees).

    utiliser_cache=True (defaut, sujets fixes de SUJETS) : mis en cache a
    part (un fichier par etape) pour ne pas retelecharger les resumes a
    chaque relance. utiliser_cache=False (requetes libres d'un utilisateur,
    voir rechercher_requete_libre) : calcule en memoire sans jamais lire ni
    ecrire le cache partage -- une requete libre ne doit pas ecraser le
    travail deja fait sur les 9 sujets suivis."""
    import extraction_details_etudes as ede

    cache_details = DATA_DIR / "pubmed_details_cliniques.csv"
    if utiliser_cache and not force and cache_details.exists():
        df_details = pd.read_csv(cache_details, dtype=str)
    else:
        lignes = []
        for pmid in df_etudes["pmid"].unique():
            details = ede.analyser_etude(str(pmid))
            lignes.append({
                "pmid": pmid,
                "dosage": " | ".join(details["dosage"]),
                "duree": " | ".join(details["duree"]),
                "taille_echantillon": " | ".join(details["taille_echantillon"]),
                "type_etude": " | ".join(details["type_etude"]),
                "resultats_effet": details["resultats_effet"],
                "conclusion": details["conclusion"],
                "resume_bref": details["resume_bref"],
            })
            time.sleep(0.4)
        df_details = pd.DataFrame(lignes)
        if utiliser_cache:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df_details.to_csv(cache_details, index=False, encoding="utf-8")

    return df_etudes.merge(df_details, on="pmid", how="left")


def main():
    df = rechercher_tous_les_sujets()
    df = enrichir_avec_details_cliniques(df)
    for sujet in df["sujet"].unique():
        sous_ensemble = df[df["sujet"] == sujet]
        print(f"\n=== {sujet} ({len(sous_ensemble)} etudes) ===")
        for _, ligne in sous_ensemble.iterrows():
            print(f"  [{ligne['pmid']}] {ligne['titre']}")
            print(f"    {ligne['revue']}, {ligne['date']} -- {ligne['url']}")
            print(f"    type : {ligne['type_etude'] or '(non trouve dans le resume)'}"
                  f" | effectif : {ligne['taille_echantillon'] or '(non trouve)'}")
            print(f"    duree : {ligne['duree'] or '(non trouve)'}"
                  f" | dosage : {ligne['dosage'] or '(non trouve dans le resume)'}")


if __name__ == "__main__":
    main()
