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


def afficher_etude(etude):
    resume_bref = etude.get("resume_bref") or ""
    # Résumé bref affiché en clair, hors du expander : c'est la seule chose
    # à lire pour un scan rapide de plusieurs études, sans tout ouvrir.
    if resume_bref:
        st.markdown(f"**[{etude['pmid']}]** {etude['titre']}  \n💡 _{resume_bref}_")
    else:
        st.markdown(f"**[{etude['pmid']}]** {etude['titre']}  \n_Pas de résumé structuré — voir le détail._")

    with st.expander("Détail (dosage, durée, effet complet, citation)"):
        st.caption(f"{etude['revue']}, {etude['date']} — [Voir sur PubMed]({etude['url']})")
        c1, c2 = st.columns(2)
        c1.markdown(f"**Dosage** : {etude['dosage'] or '_non trouvé dans le résumé_'}")
        c1.markdown(f"**Durée** : {etude['duree'] or '_non trouvée dans le résumé_'}")
        c2.markdown(f"**Type d'étude** : {etude['type_etude'] or '_non trouvé dans le résumé_'}")
        c2.markdown(f"**Effectif** : {etude['taille_echantillon'] or '_non trouvé dans le résumé_'}")
        if etude.get("resultats_effet"):
            st.markdown(f"**Effet observé (texte complet)** : {etude['resultats_effet']}")
        if etude.get("conclusion"):
            st.markdown(f"**Conclusion des auteurs (texte complet)** : {etude['conclusion']}")
        if not etude.get("resultats_effet") and not etude.get("conclusion"):
            st.caption("Résumé non structuré (pas de section RESULTS/CONCLUSION identifiable) — lire l'étude complète via le lien PubMed.")


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
            for _, etude in df.iterrows():
                afficher_etude(etude)

with tab_suivis:
    st.caption("Les 19 sujets déjà explorés avec Gisèle le 27/08, mis en cache (pas de nouvel appel réseau).")
    df_suivis = rp.rechercher_tous_les_sujets()
    df_suivis = rp.enrichir_avec_details_cliniques(df_suivis)
    sujet_choisi = st.selectbox("Sujet", sorted(df_suivis["sujet"].unique()))
    sous_ensemble = df_suivis[df_suivis["sujet"] == sujet_choisi]
    st.dataframe(
        sous_ensemble[["pmid", "titre", "revue", "date", "dosage", "duree", "type_etude", "url"]],
        use_container_width=True, hide_index=True,
    )

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
                    for _, etude in df_cat.iterrows():
                            afficher_etude(etude)
