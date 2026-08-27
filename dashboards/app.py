"""Recherche de littérature santé/fertilité (PubMed réel) — projet
personnel (Track B). Réponse à la question produit du 27/08 : jusque-là
c'était Gisèle qui indiquait les sujets à Claude ; ici, n'importe quel
utilisateur tape son propre sujet et obtient la même recherche PubMed en
direct (dosage, durée, effet observé, conclusion, citation vérifiable).
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import recherche_pubmed as rp

st.set_page_config(page_title="Recherche Santé & Fertilité", page_icon="🔬", layout="wide")

st.title("Recherche Santé & Fertilité (données réelles PubMed)")
st.caption(
    "Tape un complément ou un sujet de santé (ex. \"myo-inositol PCOS\", \"zinc sperm quality\", "
    "\"vitamin D pregnancy\"). Recherche PubMed en direct, jamais une réponse inventée."
)
st.info(
    "⚠️ Projet personnel, pas un avis médical. Chaque résultat cite un vrai PMID vérifiable sur "
    "pubmed.ncbi.nlm.nih.gov. Dosage/durée extraits automatiquement du résumé quand le format le "
    "permet — vérifier l'étude complète avant d'agir dessus."
)

tab_libre, tab_suivis = st.tabs(["Recherche libre", "9 sujets déjà suivis"])

with tab_libre:
    requete = st.text_input("Sujet de recherche (en anglais, PubMed indexe mieux ainsi)",
                             placeholder="ex. myo-inositol PCOS oocyte quality")
    max_resultats = st.slider("Nombre d'études", 3, 10, 5)

    if requete:
        with st.spinner("Recherche PubMed en cours (peut prendre quelques secondes, une requête par étude)..."):
            df = rp.rechercher_requete_libre(requete, max_resultats=max_resultats)

        if df.empty:
            st.warning("Aucune étude trouvée pour cette requête sur PubMed. Essaie des termes plus généraux ou en anglais.")
        else:
            st.success(f"{len(df)} étude(s) trouvée(s), voir détail ci-dessous.")
            for _, etude in df.iterrows():
                with st.expander(f"[{etude['pmid']}] {etude['titre']}"):
                    st.caption(f"{etude['revue']}, {etude['date']} — [Voir sur PubMed]({etude['url']})")
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Dosage** : {etude['dosage'] or '_non trouvé dans le résumé_'}")
                    c1.markdown(f"**Durée** : {etude['duree'] or '_non trouvée dans le résumé_'}")
                    c2.markdown(f"**Type d'étude** : {etude['type_etude'] or '_non trouvé dans le résumé_'}")
                    c2.markdown(f"**Effectif** : {etude['taille_echantillon'] or '_non trouvé dans le résumé_'}")
                    if etude["resultats_effet"]:
                        st.markdown(f"**Effet observé** : {etude['resultats_effet']}")
                    if etude["conclusion"]:
                        st.markdown(f"**Conclusion des auteurs** : {etude['conclusion']}")
                    if not etude["resultats_effet"] and not etude["conclusion"]:
                        st.caption("Résumé non structuré (pas de section RESULTS/CONCLUSION identifiable) — lire l'étude complète via le lien PubMed.")

with tab_suivis:
    st.caption("Les 9 sujets déjà explorés avec Gisèle le 27/08, mis en cache (pas de nouvel appel réseau).")
    df_suivis = rp.rechercher_tous_les_sujets()
    df_suivis = rp.enrichir_avec_details_cliniques(df_suivis)
    sujet_choisi = st.selectbox("Sujet", sorted(df_suivis["sujet"].unique()))
    sous_ensemble = df_suivis[df_suivis["sujet"] == sujet_choisi]
    st.dataframe(
        sous_ensemble[["pmid", "titre", "revue", "date", "dosage", "duree", "type_etude", "url"]],
        use_container_width=True, hide_index=True,
    )
