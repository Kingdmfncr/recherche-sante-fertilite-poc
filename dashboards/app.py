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
    with st.expander(f"[{etude['pmid']}] {etude['titre']}"):
        st.caption(f"{etude['revue']}, {etude['date']} — [Voir sur PubMed]({etude['url']})")
        c1, c2 = st.columns(2)
        c1.markdown(f"**Dosage** : {etude['dosage'] or '_non trouvé dans le résumé_'}")
        c1.markdown(f"**Durée** : {etude['duree'] or '_non trouvée dans le résumé_'}")
        c2.markdown(f"**Type d'étude** : {etude['type_etude'] or '_non trouvé dans le résumé_'}")
        c2.markdown(f"**Effectif** : {etude['taille_echantillon'] or '_non trouvé dans le résumé_'}")
        if etude.get("resultats_effet"):
            st.markdown(f"**Effet observé** : {etude['resultats_effet']}")
        if etude.get("conclusion"):
            st.markdown(f"**Conclusion des auteurs** : {etude['conclusion']}")
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
        "Tape une problématique complète (une vraie question, pas juste un mot-clé). Une IA la "
        "décompose en catégories de recherche, puis chaque catégorie est interrogée sur PubMed en "
        "direct — l'IA ne propose que la structure, jamais un résultat scientifique lui-même."
    )
    if not api_key:
        st.warning(
            "🔑 Aucune clé Anthropic configurée (`ANTHROPIC_API_KEY` dans `.streamlit/secrets.toml`) "
            "— cette fonctionnalité a besoin d'une IA pour décomposer la problématique, elle est "
            "désactivée sans clé. Utilise l'onglet \"Recherche libre\" en attendant."
        )
    else:
        problematique = st.text_area(
            "Problématique",
            placeholder="ex. Quels facteurs modifiables soutiennent la fertilité après 35 ans ?",
        )
        max_par_categorie = st.slider("Études par catégorie", 3, 8, 5, key="slider_problematique")

        if st.button("Explorer cette problématique", disabled=not problematique):
            with st.spinner("Décomposition de la problématique puis recherche PubMed par catégorie..."):
                categories, resultats = dp.explorer_problematique(
                    problematique, api_key, max_resultats_par_categorie=max_par_categorie,
                )

            if not categories:
                st.error(
                    "La décomposition a échoué (clé invalide, appel IA échoué, ou réponse mal "
                    "formée). Rien n'est affiché plutôt qu'un résultat deviné."
                )
            else:
                st.success(f"{len(categories)} catégorie(s) identifiée(s).")
                for categorie in categories:
                    nom = categorie["nom_categorie"]
                    df_cat = resultats[nom]
                    st.subheader(f"{nom}  `{categorie['requete_pubmed']}`")
                    if df_cat.empty:
                        st.caption("Aucune étude trouvée sur PubMed pour cette catégorie.")
                    else:
                        for _, etude in df_cat.iterrows():
                            afficher_etude(etude)
