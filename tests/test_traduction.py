"""Tests unitaires — traduction.py. N'appelle jamais le vrai service de
traduction (réseau, lent, quota) : monkeypatch de _traduire_bloc pour
tester la logique de découpage/cache/repli en erreur, même logique que le
reste du portfolio (voir test_extraction.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import traduction as trad


def test_traduire_texte_vide_retourne_immediatement():
    """Un texte vide ne doit jamais déclencher d'appel réseau (economie de
    quota, et un champ vide en amont — ex. resume_bref absent — ne doit
    jamais planter l'affichage)."""
    texte, ok = trad.traduire("", source="en", cible="fr")
    assert texte == ""
    assert ok is True


def test_traduire_texte_none_retourne_chaine_vide():
    texte, ok = trad.traduire(None, source="en", cible="fr")
    assert texte == ""
    assert ok is True


def test_decouper_en_blocs_un_seul_bloc_si_texte_court():
    assert trad.decouper_en_blocs("Une phrase courte.") == ["Une phrase courte."]


def test_decouper_en_blocs_respecte_la_limite():
    phrase = "Mot " * 200 + ". "  # ~1000 caracteres par phrase
    texte = phrase * 10  # ~10000 caracteres, doit être découpé
    blocs = trad.decouper_en_blocs(texte, limite=4500)
    assert len(blocs) > 1
    for bloc in blocs:
        assert len(bloc) <= 4500 + len(phrase)  # une phrase peut dépasser marginalement, jamais coupée


def test_decouper_en_blocs_ne_perd_aucune_phrase():
    texte = "Phrase un. Phrase deux. Phrase trois."
    blocs = trad.decouper_en_blocs(texte, limite=15)
    reconstitue = "".join(blocs)
    assert "Phrase un" in reconstitue
    assert "Phrase deux" in reconstitue
    assert "Phrase trois" in reconstitue


def test_traduire_gere_un_echec_reseau(monkeypatch):
    """Le service de traduction peut échouer (réseau, throttling) : le
    texte original doit revenir avec ok=False, jamais une exception qui
    casserait l'affichage d'une étude."""
    def _echec(texte, source, cible):
        raise ConnectionError("service indisponible")

    monkeypatch.setattr(trad, "_traduire_bloc", _echec)
    trad._traduire_avec_cache.cache_clear()

    texte, ok = trad.traduire("Un texte quelconque jamais vu avant.", source="en", cible="fr")
    assert texte == "Un texte quelconque jamais vu avant."
    assert ok is False


def test_traduire_vers_anglais_utilise_le_bon_sens(monkeypatch):
    appels = []

    def _fausse_traduction(texte, source, cible):
        appels.append((source, cible))
        return "translated"

    monkeypatch.setattr(trad, "_traduire_bloc", _fausse_traduction)
    trad._traduire_avec_cache.cache_clear()

    texte, ok = trad.traduire_vers_anglais("texte francais unique 1")
    assert ok is True
    assert appels == [("fr", "en")]


def test_traduire_vers_francais_utilise_le_bon_sens(monkeypatch):
    appels = []

    def _fausse_traduction(texte, source, cible):
        appels.append((source, cible))
        return "traduit"

    monkeypatch.setattr(trad, "_traduire_bloc", _fausse_traduction)
    trad._traduire_avec_cache.cache_clear()

    texte, ok = trad.traduire_vers_francais("english text unique 2")
    assert ok is True
    assert appels == [("en", "fr")]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
