"""Extraction déclarative de détails cliniques depuis les résumés PubMed
réels — étape 4.3 bis, ajoutée le 27/08 à la demande de Gisèle : au-delà du
titre/revue/date, faire ressortir le dosage testé, la durée de l'étude, la
taille de l'échantillon et le type d'étude, pour juger vite si un résultat
est solide ou préliminaire.

Best-effort assumé, pas une garantie : le texte libre d'un résumé médical
ne suit aucun format fixe (contrairement aux factures de
extraction-documents-poc, un abstract PubMed n'a pas de structure
attendue). Un champ non trouvé reste une liste vide, jamais une valeur
devinée. Le résumé brut est toujours conservé à côté pour vérification
manuelle avant de citer un chiffre.
"""
import re
import unicodedata
from pathlib import Path

import requests
import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_config_cache = None


def _load_config():
    global _config_cache
    if _config_cache is None:
        with open(CONFIG_DIR / "patterns_cliniques.yaml", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def recuperer_abstract(pmid):
    """Texte brut du resume via efetch. Retourne '' si aucun resume
    disponible (ex. simple lettre/commentaire sans abstract structure) --
    jamais une exception qui casserait un lot de plusieurs PMID."""
    reponse = requests.get(EFETCH_URL, params={
        "db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text",
    }, timeout=20)
    reponse.raise_for_status()
    return reponse.text


def normaliser_espaces(texte):
    """Les resumes PubMed contiennent des espaces unicode non standard
    (ex. U+2009 entre un nombre et son unite) et sont mis en forme avec des
    retours a la ligne fixes a ~80 caracteres, qui coupent parfois un terme
    au milieu (ex. "randomized" et "controlled trial" sur deux lignes).
    Tout est reduit a des espaces simples avant extraction, pour que le
    texte extrait reste lisible et comparable d'une etude a l'autre."""
    texte = unicodedata.normalize("NFKC", texte)
    return re.sub(r"\s+", " ", texte)


def extraire_details_cliniques(texte_abstract):
    """Retourne un dict {champ: [valeurs trouvees]} — toujours une liste,
    meme vide, jamais None, pour que l'appelant n'ait pas de cas particulier
    a gerer selon qu'un champ a ete trouve ou non."""
    config = _load_config()
    texte = normaliser_espaces(texte_abstract)
    resultats = {}
    for nom_champ, config_champ in config["champs"].items():
        trouvailles = []
        for pattern in config_champ["patterns"]:
            trouvailles.extend(re.findall(pattern, texte, flags=re.IGNORECASE))
        # dedoublonnage en conservant l'ordre d'apparition
        vues = set()
        uniques = [t for t in trouvailles if not (t.lower() in vues or vues.add(t.lower()))]
        resultats[nom_champ] = uniques
    return resultats


def extraire_resultats_et_conclusion(texte_abstract):
    """Beaucoup de résumés PubMed suivent un format structuré avec des
    libellés explicites (BACKGROUND/METHODS/RESULTS/CONCLUSION) — vérifié
    sur plusieurs études réelles avant d'écrire cette fonction (ex. PMID
    21744744, 38061271). Quand ce format existe, on extrait directement le
    texte des sections RESULTS et CONCLUSION : c'est là que se trouve
    l'effet observé sur le corps/la grossesse, pas dans le titre. Si le
    résumé n'est pas structuré ainsi (arrive souvent), les deux champs
    restent vides plutôt que de deviner où coupe le texte."""
    texte = normaliser_espaces(texte_abstract)
    resultats_effet = ""
    m = re.search(r"RESULTS?:\s*(.*?)(?=\s*CONCLUSIONS?:)", texte, flags=re.IGNORECASE)
    if m:
        resultats_effet = m.group(1).strip()

    conclusion = ""
    m = re.search(r"CONCLUSIONS?:\s*(.*?)(?=\s*(?:CLINICAL TRIAL REG|PMID:|DOI:|©|\Z))", texte, flags=re.IGNORECASE)
    if m:
        conclusion = m.group(1).strip()

    return {"resultats_effet": resultats_effet, "conclusion": conclusion}


def analyser_etude(pmid):
    """Point d'entree unique : recupere le resume reel et en extrait les
    details cliniques (dosage/duree/effectif/type) et, quand le format le
    permet, l'effet observe et la conclusion de l'etude. Retourne aussi le
    resume complet pour verification manuelle avant de citer un chiffre."""
    abstract = recuperer_abstract(pmid)
    details = extraire_details_cliniques(abstract)
    effets = extraire_resultats_et_conclusion(abstract)
    return {"pmid": pmid, "abstract": abstract, **details, **effets}


def main():
    exemple_pmid = "21744744"  # myo-inositol, resume structure avec RESULTS/CONCLUSION
    resultat = analyser_etude(exemple_pmid)
    print(f"PMID {exemple_pmid}")
    for champ in ["type_etude", "taille_echantillon", "duree", "dosage"]:
        valeurs = resultat[champ]
        print(f"  {champ} : {valeurs if valeurs else '(rien trouve)'}")
    print(f"  effet observe : {resultat['resultats_effet'][:200] or '(non trouve)'}")
    print(f"  conclusion : {resultat['conclusion'][:200] or '(non trouve)'}")


if __name__ == "__main__":
    main()
