"""Classification déclarative (mots-clés, sans IA) des études réelles déjà
récupérées sur un sujet en deux angles utiles à quelqu'un qui fait cette
recherche : les facteurs/causes possibles évoqués dans la littérature, et
les pistes/solutions étudiées — même quand la preuve n'est pas définitive
(le niveau de preuve de chaque étude reste affiché à côté, jamais masqué).

Ajouté le 03/09 à la demande de Gisèle : le dashboard listait déjà les
études réelles une par une (voir dashboards/app.py), mais ne répondait
pas à la question que se pose concrètement quelqu'un qui fait cette
recherche — "pourquoi j'ai ça, et qu'est-ce qui a été étudié pour y
répondre ?". Classification purement déclarative sur le texte déjà
extrait (conclusion/effet observé/résumé bref, voir
extraction_details_etudes.py) : jamais une conclusion inventée, chaque
ligne affichée reste un vrai PMID avec un extrait réel, juste regroupé
différemment. Même principe que synthese.py (classer_direction) : une
heuristique par mots-clés, pas une méta-analyse.
"""
import re

PATTERNS_FACTEUR = [
    r"\brisk factors?\b", r"\bassociated with\b", r"\blinked to\b", r"\bincreased risk\b",
    r"\bhigher risk\b", r"\brisk of\b", r"\bpredispos", r"\b(a)?etiology\b",
    r"\bpathogenesis\b", r"\bcaused? by\b", r"\bcontribut(e|es|ing|ion) to\b", r"\bexposure to\b",
]

PATTERNS_SOLUTION = [
    r"\btreatments?\b", r"\btherap(y|ies)\b", r"\bintervention", r"\bsupplementation\b",
    r"\bimprov(e|ed|es|ement)\b", r"\breduc(e|ed|es|tion)\b", r"\bprevent", r"\bmanagement\b",
    r"\befficacy\b", r"\bprotocols?\b", r"\bbenefit",
]


def _texte_pertinent(etude):
    """Le texte le plus informatif disponible pour une étude — conclusion
    en priorité (déjà la synthèse des auteurs), sinon effet observé, sinon
    résumé bref. Jamais le titre seul (trop court pour bien classer).
    Un champ vide relu depuis un CSV pandas est parfois un NaN (float),
    pas une chaîne vide — même garde que synthese._texte_ou_vide."""
    for champ in ("conclusion", "resultats_effet", "resume_bref"):
        valeur = etude.get(champ)
        if valeur and isinstance(valeur, str) and valeur.strip():
            return valeur.strip()
    return ""


def _correspond(texte, patterns):
    return any(re.search(p, texte, flags=re.IGNORECASE) for p in patterns)


def classer_facteurs_et_solutions(df_etudes):
    """Retourne {"facteurs": [...], "solutions": [...]} — chaque entrée
    garde pmid/titre/type_etude/extrait (texte réel, non traduit ici,
    voir traduction.py côté affichage). Une même étude peut apparaître
    dans les deux listes (ex. un facteur de risque ET une piste de
    traitement dans le même abstract) — pas un choix exclusif. Liste vide
    si aucune étude ne correspond, jamais une supposition."""
    facteurs, solutions = [], []
    for _, etude in df_etudes.iterrows():
        texte = _texte_pertinent(etude)
        if not texte:
            continue
        ligne = {
            "pmid": etude["pmid"], "titre": etude.get("titre", ""),
            "extrait": texte, "type_etude": etude.get("type_etude", ""),
        }
        if _correspond(texte, PATTERNS_FACTEUR):
            facteurs.append(ligne)
        if _correspond(texte, PATTERNS_SOLUTION):
            solutions.append(ligne)
    return {"facteurs": facteurs, "solutions": solutions}
