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
import decomposition_problematique as dp


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


def test_sujets_couvre_les_pistes_de_la_cartographie():
    """Ajoute le 27/08 suite a la problematique formalisee (PROTOCOLE
    section 3) : age paternel et exposition environnementale, aussi
    documentes que la nutrition mais pas encore creuses avant ce jour."""
    for cle in ["age_paternel_qualite_sperme", "exposition_environnementale"]:
        assert cle in rp.SUJETS


def test_sujets_couvre_le_detail_exposition_environnementale():
    for cle in ["bpa_phtalates_fertilite", "pesticides_fertilite", "pollution_air_fertilite"]:
        assert cle in rp.SUJETS


def test_sujets_couvre_les_5_sujets_sante_generale():
    for cle in ["tension_arterielle", "foie_gras_steatose", "diabete_type2", "arthrose", "arthrite"]:
        assert cle in rp.SUJETS


def test_sujets_couvre_la_menopause():
    assert "menopause" in rp.SUJETS


def test_decomposer_par_mots_cles_couvre_la_menopause():
    categories = dp.decomposer_par_mots_cles("Comment gerer les symptomes de la menopause ?")
    noms = {c["nom_categorie"] for c in categories}
    assert "Ménopause" in noms


def test_sujets_couvre_les_5_causes_mecanismes_demandes():
    for cle in ["mycoplasme_fertilite", "trompes_bouchees", "qualite_ovocytaire",
                "qualite_spermatique", "cycle_3_mois_spermatogenese"]:
        assert cle in rp.SUJETS


def test_decomposer_par_mots_cles_couvre_trompes_bouchees_et_cycle_3_mois():
    categories = dp.decomposer_par_mots_cles("Trompes bouchees, est-ce reversible ? Et le cycle des 3 mois ?")
    noms = {c["nom_categorie"] for c in categories}
    assert "Trompes bouchées" in noms
    assert "Cycle des 3 mois (spermatogenèse/folliculogenèse)" in noms


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


def test_resumer_brievement_priorise_la_conclusion():
    resume = ede.resumer_brievement(
        resultats_effet="Les resultats bruts sur plusieurs phrases.",
        conclusion="Le complement ameliore la qualite ovocytaire. Autre phrase ignoree.",
    )
    assert resume == "Le complement ameliore la qualite ovocytaire."


def test_resumer_brievement_repli_sur_effet_observe_si_pas_de_conclusion():
    resume = ede.resumer_brievement(resultats_effet="L'effet observe est significatif.", conclusion="")
    assert resume == "L'effet observe est significatif."


def test_resumer_brievement_vide_si_rien_a_resumer():
    assert ede.resumer_brievement(resultats_effet="", conclusion="") == ""


# ── decomposition_problematique : parsing JSON (sans reseau) ────────────────

def test_parser_reponse_json_cas_valide():
    texte = '[{"nom_categorie": "Nutrition", "requete_pubmed": "diet heart health women"}]'
    categories = dp._parser_reponse_json(texte)
    assert categories == [{"nom_categorie": "Nutrition", "requete_pubmed": "diet heart health women"}]


def test_parser_reponse_json_retire_le_bloc_markdown():
    texte = '```json\n[{"nom_categorie": "Sport", "requete_pubmed": "exercise cardiovascular women"}]\n```'
    categories = dp._parser_reponse_json(texte)
    assert categories[0]["nom_categorie"] == "Sport"


def test_parser_reponse_json_invalide_retourne_none():
    assert dp._parser_reponse_json("ceci n'est pas du JSON") is None


def test_parser_reponse_json_categorie_incomplete_invalide_tout():
    """Une seule categorie mal formee (cle manquante) invalide toute la
    decomposition plutot que de retourner une liste partiellement fiable."""
    texte = '[{"nom_categorie": "Nutrition", "requete_pubmed": "diet"}, {"nom_categorie": "Sport"}]'
    assert dp._parser_reponse_json(texte) is None


def test_decomposer_problematique_sans_cle_retourne_none():
    assert dp.decomposer_problematique("une question", api_key=None) is None


# ── decomposition_problematique : methode sans IA (mots-cles) ──────────────

def test_decomposer_par_mots_cles_trouve_les_bonnes_categories():
    problematique = "Impact du sommeil et de l'exposition environnementale sur la fertilite"
    categories = dp.decomposer_par_mots_cles(problematique)
    noms = {c["nom_categorie"] for c in categories}
    assert "Sommeil / stress" in noms
    assert "Exposition environnementale" in noms


def test_decomposer_par_mots_cles_insensible_aux_accents():
    """'steatose' (sans accent, faute de frappe courante) doit quand meme
    matcher la categorie 'Foie gras / steatose'."""
    categories = dp.decomposer_par_mots_cles("Quel regime pour la steatose hepatique ?")
    noms = {c["nom_categorie"] for c in categories}
    assert "Foie gras / stéatose" in noms


def test_decomposer_par_mots_cles_aucune_categorie_retourne_liste_vide():
    categories = dp.decomposer_par_mots_cles("Question totalement hors sujet sur la cuisine")
    assert categories == []


def test_decomposer_par_mots_cles_probematique_vide():
    assert dp.decomposer_par_mots_cles("") == []


def test_explorer_problematique_sans_ia_ne_necessite_pas_de_cle():
    categories, resultats, methode = dp.explorer_problematique(
        "Quel impact du sommeil sur la fertilite ?", methode="mots_cles",
    )
    assert methode == "mots_cles"
    assert categories is not None
    assert "Sommeil / stress" in resultats


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
