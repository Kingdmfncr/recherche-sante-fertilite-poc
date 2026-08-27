"""Recherche de littérature santé/fertilité (PubMed réel) — projet
personnel (Track B). Trois façons d'utiliser le même moteur réel :
1. Recherche libre sur un sujet précis.
2. Les 19 sujets déjà suivis avec Gisèle (mis en cache).
3. Depuis une problématique complète (IA optionnelle qui décompose en
   catégories de recherche, ajoutée le 27/08 — voir decomposition_problematique.py
   pour le principe de groundage : l'IA ne propose que des catégories et
   des requêtes, jamais un résultat scientifique lui-même).
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import recherche_pubmed as rp
import decomposition_problematique as dp
import synthese as syn
import notes_perso as notes

st.set_page_config(page_title="Recherche Santé & Fertilité", page_icon="🔬", layout="wide")

st.title("Recherche Santé & Fertilité (données réelles PubMed)")
st.info(
    "⚠️ Projet personnel, pas un avis médical. Chaque résultat cite un vrai PMID vérifiable sur "
    "pubmed.ncbi.nlm.nih.gov. Dosage/durée/effet extraits automatiquement du résumé quand le "
    "format le permet — vérifier l'étude complète avant d'agir dessus."
)

try:
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    api_key = None


def valeur_ou_vide(x):
    """Neutralise les NaN pandas (champ vide relu depuis un CSV en cache,
    ex. resume_bref absent) -- sans ça `x or "fallback"` affiche le texte
    "nan" car un float NaN est vrai au sens booléen en Python."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x)


def afficher_synthese_categorie(df_categorie, titre):
    """Synthèse chiffrée (niveau de preuve + direction) — jamais une phrase
    de conclusion inventée, seulement des comptages vérifiables étude par
    étude (voir synthese.py)."""
    resume = syn.synthetiser_categorie(df_categorie)
    if resume["nb_etudes"] == 0:
        return
    st.caption(f"📊 Synthèse « {titre} » — {resume['nb_etudes']} étude(s)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Niveau de preuve**")
        for libelle, n in sorted(resume["par_niveau_preuve"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {libelle} : {n}")
    with c2:
        st.markdown("**Direction du résultat**")
        libelles_direction = {"positif": "🟢 Positif", "negatif": "🔴 Négatif/sans effet", "mixte": "🟡 Mixte", "indetermine": "⚪ Indéterminé"}
        for direction, n in sorted(resume["par_direction"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {libelles_direction.get(direction, direction)} : {n}")


def afficher_etude(etude, contexte=""):
    resume_bref = valeur_ou_vide(etude.get("resume_bref"))
    niveau = syn.evaluer_niveau_preuve(etude.get("type_etude", ""))
    badge = f"{niveau['emoji']} {niveau['libelle']}"
    # Résumé bref affiché en clair, hors du expander : c'est la seule chose
    # à lire pour un scan rapide de plusieurs études, sans tout ouvrir.
    if resume_bref:
        st.markdown(f"**[{etude['pmid']}]** {etude['titre']}  \n{badge}  \n💡 _{resume_bref}_")
    else:
        st.markdown(f"**[{etude['pmid']}]** {etude['titre']}  \n{badge}  \n_Pas de résumé structuré — voir le détail._")

    with st.expander("Détail (dosage, durée, effet complet, citation, ma note)"):
        st.caption(f"{etude['revue']}, {etude['date']} — [Voir sur PubMed]({etude['url']})")
        c1, c2 = st.columns(2)
        c1.markdown(f"**Dosage** : {valeur_ou_vide(etude.get('dosage')) or '_non trouvé dans le résumé_'}")
        c1.markdown(f"**Durée** : {valeur_ou_vide(etude.get('duree')) or '_non trouvée dans le résumé_'}")
        c2.markdown(f"**Type d'étude** : {valeur_ou_vide(etude.get('type_etude')) or '_non trouvé dans le résumé_'}")
        c2.markdown(f"**Effectif** : {valeur_ou_vide(etude.get('taille_echantillon')) or '_non trouvé dans le résumé_'}")
        effet = valeur_ou_vide(etude.get("resultats_effet"))
        conclusion = valeur_ou_vide(etude.get("conclusion"))
        if effet:
            st.markdown(f"**Effet observé (texte complet)** : {effet}")
        if conclusion:
            st.markdown(f"**Conclusion des auteurs (texte complet)** : {conclusion}")
        if not effet and not conclusion:
            st.caption("Résumé non structuré (pas de section RESULTS/CONCLUSION identifiable) — lire l'étude complète via le lien PubMed.")

        pmid = str(etude["pmid"])
        cle_widget = f"note_{contexte}_{pmid}"
        note_actuelle = notes.charger_notes().get(pmid, "")
        nouvelle_note = st.text_area("Ma note perso (jamais publiée, reste en local)", value=note_actuelle, key=cle_widget, height=68)
        if st.button("Enregistrer la note", key=f"save_{cle_widget}"):
            notes.sauvegarder_note(pmid, nouvelle_note)
            st.success("Note enregistrée.")


tab_libre, tab_suivis, tab_problematique = st.tabs(
    ["Recherche libre", "19 sujets déjà suivis", "Depuis une problématique"]
)

with tab_libre:
    st.caption(
        "Tape un complément ou un sujet de santé (ex. \"myo-inositol PCOS\", \"zinc sperm quality\"). "
        "Recherche PubMed en direct, jamais une réponse inventée."
    )
    requete = st.text_input("Sujet de recherche (en anglais, PubMed indexe mieux ainsi)",
                             placeholder="ex. myo-inositol PCOS oocyte quality")
    max_resultats = st.slider("Nombre d'études", 3, 10, 5, key="slider_libre")

    if requete:
        with st.spinner("Recherche PubMed en cours (une requête par étude, quelques secondes)..."):
            df = rp.rechercher_requete_libre(requete, max_resultats=max_resultats)

        if df.empty:
            st.warning("Aucune étude trouvée pour cette requête sur PubMed. Essaie des termes plus généraux ou en anglais.")
        else:
            st.success(f"{len(df)} étude(s) trouvée(s), voir détail ci-dessous.")
            afficher_synthese_categorie(df, requete)
            for _, etude in df.iterrows():
                afficher_etude(etude, contexte="libre")

with tab_suivis:
    st.caption("Les sujets déjà explorés avec Gisèle, mis en cache (pas de nouvel appel réseau).")
    df_suivis = rp.rechercher_tous_les_sujets()
    df_suivis = rp.enrichir_avec_details_cliniques(df_suivis)
    sujet_choisi = st.selectbox("Sujet", sorted(df_suivis["sujet"].unique()))
    sous_ensemble = df_suivis[df_suivis["sujet"] == sujet_choisi]
    afficher_synthese_categorie(sous_ensemble, sujet_choisi)
    for _, etude in sous_ensemble.iterrows():
        afficher_etude(etude, contexte="suivis")

with tab_problematique:
    st.caption(
        "Tape une problématique complète (une vraie question, pas juste un mot-clé). Elle est "
        "décomposée en catégories de recherche, puis chaque catégorie est interrogée sur PubMed "
        "en direct."
    )

    methode = "mots_cles"
    if api_key:
        methode = st.radio(
            "Méthode de décomposition",
            ["mots_cles", "ia"],
            format_func=lambda m: (
                "Par mots-clés (par défaut, sans IA, limité aux 13 catégories connues)"
                if m == "mots_cles" else
                "Par IA (Claude, peut couvrir n'importe quel sujet)"
            ),
            horizontal=False,
        )
    else:
        st.caption(
            "🔑 Pas de clé Anthropic configurée — décomposition par mots-clés uniquement "
            "(aucune clé nécessaire pour cette méthode, voir `config/categories_problematique.yaml`)."
        )

    problematique = st.text_area(
        "Problématique",
        placeholder="ex. Quels facteurs modifiables soutiennent la fertilité après 35 ans ?",
    )
    max_par_categorie = st.slider("Études par catégorie", 3, 8, 5, key="slider_problematique")

    if st.button("Explorer cette problématique", disabled=not problematique):
        with st.spinner("Décomposition de la problématique puis recherche PubMed par catégorie..."):
            categories, resultats, methode_utilisee = dp.explorer_problematique(
                problematique, api_key, max_resultats_par_categorie=max_par_categorie, methode=methode,
            )

        if not categories:
            st.warning(
                "Aucune catégorie connue ne correspond à cette problématique (méthode mots-clés) "
                "ou la décomposition IA a échoué. Essaie l'onglet \"Recherche libre\" avec tes "
                "propres mots-clés, ou reformule la problématique."
            )
        else:
            st.success(f"{len(categories)} catégorie(s) identifiée(s) — méthode : {methode_utilisee}.")
            for categorie in categories:
                nom = categorie["nom_categorie"]
                df_cat = resultats[nom]
                st.subheader(f"{nom}  `{categorie['requete_pubmed']}`")
                if df_cat.empty:
                    st.caption("Aucune étude trouvée sur PubMed pour cette catégorie.")
                else:
                    afficher_synthese_categorie(df_cat, nom)
                    for _, etude in df_cat.iterrows():
                        afficher_etude(etude, contexte=f"probl_{nom}")
