"""Traduction automatique (français <-> anglais) via un vrai service de
traduction (Google Translate, aucune clé API requise) — deux usages :
1. Traduire une requête tapée en français avant de l'envoyer à PubMed, qui
   n'indexe quasiment que l'anglais (voir rechercher_requete_libre).
2. Traduire les résumés/extraits d'études réels (déjà extraits par
   extraction_details_etudes.py, jamais inventés) pour un affichage en
   français — le texte original reste toujours disponible à côté pour
   vérification, même principe de groundage que le reste du projet : la
   traduction transforme un texte réel, elle n'en invente jamais un.

Best-effort assumé : le service peut être indisponible (réseau,
throttling, changement d'API non annoncé côté Google). Une traduction
échouée retourne le texte original avec ok=False, jamais un texte vide ni
une exception qui casserait l'affichage d'une étude.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import lru_cache

from deep_translator import GoogleTranslator

# Marge sous la limite ~5000 caracteres de l'API Google Translate utilisee
# par deep-translator.
LIMITE_CARACTERES = 4500

# deep-translator n'expose aucun timeout reseau (verifie dans sa source,
# google.py fait un requests.get() sans timeout=...) : un throttling ou un
# reseau qui traine peut bloquer tout le dashboard indefiniment. Bug reel
# trouve le 03/09 en testant en direct (l'app entiere s'est figee apres une
# vingtaine d'appels de traduction rapproches). Un thread avec timeout
# transforme ca en un echec normal (ok=False), jamais un blocage.
DELAI_MAX_SECONDES = 8
_executeur = ThreadPoolExecutor(max_workers=4)


def _traduire_bloc(texte, source, cible):
    future = _executeur.submit(lambda: GoogleTranslator(source=source, target=cible).translate(texte))
    try:
        return future.result(timeout=DELAI_MAX_SECONDES)
    except FutureTimeoutError:
        raise TimeoutError(f"traduction {source}->{cible} au-dela de {DELAI_MAX_SECONDES}s")


def decouper_en_blocs(texte, limite=LIMITE_CARACTERES):
    """Découpe un texte long sur des frontières de phrases ('. '), pour
    qu'aucun bloc envoyé à l'API ne dépasse la limite et qu'aucune phrase
    ne soit coupée au milieu."""
    phrases = texte.replace(". ", ".|").split("|")
    blocs, bloc_actuel = [], ""
    for phrase in phrases:
        if bloc_actuel and len(bloc_actuel) + len(phrase) > limite:
            blocs.append(bloc_actuel)
            bloc_actuel = ""
        bloc_actuel += phrase
    if bloc_actuel:
        blocs.append(bloc_actuel)
    return blocs


@lru_cache(maxsize=512)
def _traduire_avec_cache(texte, source, cible):
    """Mise en cache mémoire (durée du process Streamlit) : un même texte
    (ex. un résumé déjà vu) n'est jamais renvoyé deux fois au service de
    traduction pendant une session."""
    blocs = decouper_en_blocs(texte)
    return " ".join(_traduire_bloc(bloc, source, cible) for bloc in blocs)


def traduire(texte, source, cible):
    """Retourne (texte_traduit, ok). Si le service échoue, ok=False et
    texte_traduit == texte original, jamais un texte vide ni une
    exception : l'appelant peut toujours afficher quelque chose de vrai."""
    texte = (texte or "").strip()
    if not texte:
        return "", True
    try:
        return _traduire_avec_cache(texte, source, cible), True
    except Exception:
        return texte, False


def traduire_vers_anglais(texte_fr):
    return traduire(texte_fr, source="fr", cible="en")


def traduire_vers_francais(texte_en):
    return traduire(texte_en, source="en", cible="fr")
