"""Tests unitaires — transformation des données INSEE déjà extraites.
Ne re-télécharge jamais l'API dans un test (lent, dépendance réseau) :
utilise un petit DataFrame construit à la main, même logique que le reste
du portfolio.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import extraction_insee as ei
import recherche_pubmed as rp
import extraction_details_etudes as ede


def _df_exemple():
    return pd.DataFrame([
        {"annee": 2020, "mesure": "FERRT", "libelle_mesure": "x", "tranche_age": "Y30T34",
         "libelle_age": "30-34 ans", "valeur": 12.4, "statut": "D"},
        {"annee": 2021, "mesure": "FERRT", "libelle_mesure": "x", "tranche_age": "Y30T34",
         "libelle_age": "30-34 ans", "valeur": 12.7, "statut": "D"},
        {"annee": 2020, "mesure": "FERRT", "libelle_mesure": "x", "tranche_age": "_T",
         "libelle_age": "Toutes tranches", "valeur": 99.9, "statut": "D"},
        {"annee": 2020, "mesure": "AVERAGE_MOTHER", "libelle_mesure": "x", "tranche_age": "_Z",
         "libelle_age": "Non applicable", "valeur": 30.8, "statut": "D"},
        {"annee": 2021, "mesure": "AVERAGE_MOTHER", "libelle_mesure": "x", "tranche_age": "_Z",
         "libelle_age": "Non applicable", "valeur": 31.0, "statut": "D"},
    ])


def test_serie_fecondite_par_age_exclut_le_total():
    df = _df_exemple()
    pivot = ei.serie_fecondite_par_age(df)
    assert "Toutes tranches" not in pivot.columns
    assert "30-34 ans" in pivot.columns


def test_serie_fecondite_par_age_indexee_par_annee():
    df = _df_exemple()
    pivot = ei.serie_fecondite_par_age(df)
    assert pivot.loc[2020, "30-34 ans"] == 12.4
    assert pivot.loc[2021, "30-34 ans"] == 12.7


def test_serie_age_moyen_maternite():
    df = _df_exemple()
    serie = ei.serie_age_moyen_maternite(df)
    assert serie.loc[2020] == 30.8
    assert serie.loc[2021] == 31.0


def test_toutes_les_mesures_documentees_ont_un_libelle():
    for code in ei.MESURES:
        assert isinstance(ei.MESURES[code], str) and len(ei.MESURES[code]) > 0


# ── recherche_pubmed : parsing (sans reseau) ────────────────────────────────

def test_parser_resumes_ignore_un_pmid_absent_du_resultat():
    """Un PMID demande mais absent de la reponse esummary (erreur NCBI rare)
    est ignore plutot que de produire une ligne a moitie vide."""
    resultat_esummary = {"111": {"title": "Etude A", "fulljournalname": "Revue A", "pubdate": "2024"}}
    lignes = rp._parser_resumes(["111", "222"], resultat_esummary)
    assert len(lignes) == 1
    assert lignes[0]["pmid"] == "111"


def test_parser_resumes_construit_l_url_pubmed_reelle():
    resultat_esummary = {"38850663": {"title": "T", "fulljournalname": "R", "pubdate": "2024"}}
    lignes = rp._parser_resumes(["38850663"], resultat_esummary)
    assert lignes[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/38850663/"


def test_sujets_couvre_preconception_et_perinatalite():
    """Ajoute le 27/08 a la demande de Gisele : le module doit suivre ces
    deux themes, pas seulement les 3 sujets specifiques d'origine."""
    assert "preconception_sante" in rp.SUJETS
    assert "perinatalite" in rp.SUJETS


def test_sujets_couvre_les_4_complements_demandes():
    for cle in ["nac_fertilite", "myo_inositol_fertilite", "pqq_fertilite", "omega3_dha_grossesse"]:
        assert cle in rp.SUJETS


# ── extraction_details_etudes : dosage sans faux positif, effets/conclusion ─

def test_dosage_ignore_un_faux_positif_type_coq10_group():
    """Regression du bug reel trouve le 27/08 : 'CoQ10 group' etait lu comme
    un dosage '10 g' (le 10 de CoQ10 + le g de group)."""
    resultats = ede.extraire_details_cliniques("Women in the CoQ10 group had better outcomes.")
    assert resultats["dosage"] == []


def test_dosage_trouve_un_vrai_dosage_avec_limites_de_mot():
    resultats = ede.extraire_details_cliniques("Patients received 200 mg CoQ10 daily for 12 weeks (n=45).")
    assert "200 mg" in resultats["dosage"]
    assert "12 weeks" in resultats["duree"]


def test_extraire_resultats_et_conclusion_texte_structure():
    texte = ("BACKGROUND: context. METHODS: how. "
             "RESULTS: oocyte quality improved significantly. "
             "CONCLUSION: myoinositol may help PCOS patients. PMID: 12345")
    r = ede.extraire_resultats_et_conclusion(texte)
    assert "oocyte quality improved" in r["resultats_effet"]
    assert "myoinositol may help" in r["conclusion"]
    assert "PMID" not in r["conclusion"]


def test_extraire_resultats_et_conclusion_texte_non_structure_reste_vide():
    """Un resume qui ne suit pas le format BACKGROUND/METHODS/RESULTS/
    CONCLUSION (frequent) ne doit jamais produire un texte devine."""
    r = ede.extraire_resultats_et_conclusion("Ceci est un resume libre, sans section structuree.")
    assert r["resultats_effet"] == ""
    assert r["conclusion"] == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
