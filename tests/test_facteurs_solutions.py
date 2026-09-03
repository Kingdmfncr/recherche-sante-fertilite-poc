"""Tests unitaires — facteurs_solutions.py. Aucun appel réseau (données
construites à la main), même logique que le reste du portfolio."""
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import facteurs_solutions as fs


def _etude(pmid="1", titre="T", conclusion="", resultats_effet="", resume_bref="", type_etude=""):
    return {"pmid": pmid, "titre": titre, "conclusion": conclusion,
            "resultats_effet": resultats_effet, "resume_bref": resume_bref, "type_etude": type_etude}


def test_classe_une_etude_de_facteur_de_risque():
    df = pd.DataFrame([_etude(conclusion="Vitamin D deficiency is a risk factor for endometrial implantation failure.")])
    resultat = fs.classer_facteurs_et_solutions(df)
    assert len(resultat["facteurs"]) == 1
    assert resultat["solutions"] == []


def test_classe_une_etude_de_solution():
    df = pd.DataFrame([_etude(conclusion="Myo-inositol supplementation improved oocyte quality in this trial.")])
    resultat = fs.classer_facteurs_et_solutions(df)
    assert len(resultat["solutions"]) == 1
    assert resultat["facteurs"] == []


def test_une_etude_peut_etre_dans_les_deux_listes():
    df = pd.DataFrame([_etude(
        conclusion="Obesity is a risk factor for PCOS, and lifestyle intervention improved outcomes."
    )])
    resultat = fs.classer_facteurs_et_solutions(df)
    assert len(resultat["facteurs"]) == 1
    assert len(resultat["solutions"]) == 1


def test_liste_vide_si_aucun_mot_cle_ne_correspond():
    df = pd.DataFrame([_etude(conclusion="This study describes the general prevalence of the condition.")])
    resultat = fs.classer_facteurs_et_solutions(df)
    assert resultat["facteurs"] == []
    assert resultat["solutions"] == []


def test_etude_sans_aucun_texte_est_ignoree():
    df = pd.DataFrame([_etude(conclusion="", resultats_effet="", resume_bref="")])
    resultat = fs.classer_facteurs_et_solutions(df)
    assert resultat["facteurs"] == []
    assert resultat["solutions"] == []


def test_texte_pertinent_priorise_conclusion_sur_effet_et_resume():
    etude = pd.Series(_etude(
        conclusion="Conclusion text.", resultats_effet="Effet text.", resume_bref="Resume text.",
    ))
    assert fs._texte_pertinent(etude) == "Conclusion text."


def test_texte_pertinent_repli_sur_effet_si_pas_de_conclusion():
    etude = pd.Series(_etude(conclusion="", resultats_effet="Effet text.", resume_bref="Resume text."))
    assert fs._texte_pertinent(etude) == "Effet text."


def test_texte_pertinent_repli_sur_resume_bref_en_dernier():
    etude = pd.Series(_etude(conclusion="", resultats_effet="", resume_bref="Resume text."))
    assert fs._texte_pertinent(etude) == "Resume text."


def test_texte_pertinent_gere_un_nan_pandas():
    """Bug potentiel identique a synthese.py : un champ vide relu depuis un
    CSV pandas peut etre un NaN (float), pas une chaine vide."""
    etude = pd.Series({"pmid": "1", "titre": "T", "conclusion": math.nan,
                        "resultats_effet": math.nan, "resume_bref": "Resume text.", "type_etude": ""})
    assert fs._texte_pertinent(etude) == "Resume text."


def test_texte_pertinent_vide_si_tout_est_nan():
    etude = pd.Series({"pmid": "1", "titre": "T", "conclusion": math.nan,
                        "resultats_effet": math.nan, "resume_bref": math.nan, "type_etude": ""})
    assert fs._texte_pertinent(etude) == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
