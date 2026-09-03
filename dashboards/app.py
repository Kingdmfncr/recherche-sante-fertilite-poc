"""Recherche de littérature santé/fertilité (PubMed réel) — projet
personnel (Track B). Trois façons d'utiliser le même moteur réel :
1. Recherche libre sur un sujet précis.
2. Les sujets déjà suivis avec Gisèle (mis en cache).
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
import traduction as trad
import facteurs_solutions as fac_sol

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


def _afficher_liste_extraits(entrees, message_si_vide):
    """Traduit et tronque chaque extrait pour un scan rapide — le texte
    complet reste disponible dans le détail de l'étude correspondante
    (afficher_etude), jamais dupliqué en entier ici."""
    if not entrees:
        st.caption(message_si_vide)
        return
    vus = set()
    for entree in entrees:
        if entree["pmid"] in vus:
            continue
        vus.add(entree["pmid"])
        extrait_fr, ok = trad.traduire_vers_francais(entree["extrait"])
        apercu = extrait_fr if len(extrait_fr) <= 220 else extrait_fr[:220].rstrip() + "…"
        avertissement = "" if ok else " ⚠️"
        st.markdown(f"- **[{entree['pmid']}]** _{apercu}_{avertissement}")


def afficher_synthese_categorie(df_categorie, titre):
    """Synthèse chiffrée (niveau de preuve + direction) — jamais une phrase
    de conclusion inventée, seulement des comptages vérifiables étude par
    étude (voir synthese.py) — suivie d'un regroupement par facteurs
    possibles / pistes étudiées (facteurs_solutions.py, classification par
    mots-clés sur le texte déjà réel), ajouté le 03/09 pour répondre à la
    vraie question derrière une recherche santé : pourquoi, et qu'est-ce
    qui a été étudié pour y répondre — même sans certitude à 100%, d'où le
    niveau de preuve toujours affiché juste au-dessus."""
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

    fs = fac_sol.classer_facteurs_et_solutions(df_categorie)
    if fs["facteurs"] or fs["solutions"]:
        st.caption(
            "🧭 Ce que ces études évoquent — classification par mots-clés sur le texte réel "
            "ci-dessous, **pas un avis médical** : vérifie le niveau de preuve et l'étude "
            "complète avant de conclure quoi que ce soit."
        )
        cf, cs = st.columns(2)
        with cf:
            st.markdown("**🔍 Facteurs / causes possibles évoqués**")
            _afficher_liste_extraits(fs["facteurs"], "Aucune étude ci-dessus n'évoque explicitement un facteur de risque ou une cause.")
        with cs:
            st.markdown("**💡 Pistes / solutions étudiées**")
            _afficher_liste_extraits(fs["solutions"], "Aucune étude ci-dessus n'évoque explicitement un traitement ou une intervention.")


def afficher_etude(etude, contexte=""):
    """Tout le texte scientifique (titre, résumé bref, effet, conclusion)
    vient réellement de PubMed en anglais — traduit ici pour la lecture
    (traduction.py, vrai service, jamais une reformulation IA du sens),
    texte original anglais toujours gardé à côté pour vérifier un chiffre
    avant de s'appuyer dessus. Une traduction indisponible (réseau) affiche
    l'anglais avec un avertissement plutôt que de rien montrer."""
    titre_fr, titre_ok = trad.traduire_vers_francais(etude["titre"])
    resume_bref = valeur_ou_vide(etude.get("resume_bref"))
    resume_bref_fr, resume_ok = trad.traduire_vers_francais(resume_bref)
    niveau = syn.evaluer_niveau_preuve(etude.get("type_etude", ""))
    badge = f"{niveau['emoji']} {niveau['libelle']}"
    avertissement_trad = "" if (titre_ok and resume_ok) else "  \n⚠️ _traduction indisponible pour le moment, texte original affiché_"
    # Résumé bref affiché en clair, hors du expander : c'est la seule chose
    # à lire pour un scan rapide de plusieurs études, sans tout ouvrir.
    if resume_bref_fr:
        st.markdown(f"**[{etude['pmid']}]** {titre_fr}  \n{badge}  \n💡 _{resume_bref_fr}_{avertissement_trad}")
    else:
        st.markdown(f"**[{etude['pmid']}]** {titre_fr}  \n{badge}  \n_Pas de résumé structuré — voir le détail._{avertissement_trad}")

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
            effet_fr, effet_ok = trad.traduire_vers_francais(effet)
            st.markdown(f"**Effet observé (traduit)** : {effet_fr}")
            if not effet_ok:
                st.caption("⚠️ Traduction indisponible pour le moment.")
            with st.expander("Texte original (anglais)"):
                st.caption(effet)
        if conclusion:
            conclusion_fr, conclusion_ok = trad.traduire_vers_francais(conclusion)
            st.markdown(f"**Conclusion des auteurs (traduite)** : {conclusion_fr}")
            if not conclusion_ok:
                st.caption("⚠️ Traduction indisponible pour le moment.")
            with st.expander("Texte original (anglais)"):
                st.caption(conclusion)
        if not effet and not conclusion:
            st.caption("Résumé non structuré (pas de section RESULTS/CONCLUSION identifiable) — lire l'étude complète via le lien PubMed.")
        st.caption("Traduction automatique : vérifie toujours le texte original avant de citer un chiffre précis.")

        pmid = str(etude["pmid"])
        cle_widget = f"note_{contexte}_{pmid}"
        note_actuelle = notes.charger_notes().get(pmid, "")
        nouvelle_note = st.text_area("Ma note perso (jamais publiée, reste en local)", value=note_actuelle, key=cle_widget, height=68)
        if st.button("Enregistrer la note", key=f"save_{cle_widget}"):
            notes.sauvegarder_note(pmid, nouvelle_note)
            st.success("Note enregistrée.")


tab_libre, tab_suivis, tab_problematique = st.tabs(
    ["Recherche libre", "Sujets déjà suivis", "Depuis une problématique"]
)

with tab_libre:
    st.caption(
        "Tape un complément ou un sujet de santé, en français ou en anglais (ex. \"ménopause\", "
        "\"myo-inositol PCOS\"). Recherche PubMed en direct, jamais une réponse inventée — si la "
        "requête en français ne trouve rien, elle est retraduite en anglais automatiquement."
    )

    with st.expander("💡 Une vingtaine de problématiques de santé courantes — clique pour lancer la recherche"):
        categories_connues = dp.lister_categories()
        colonnes = st.columns(3)
        for i, categorie in enumerate(categories_connues):
            if colonnes[i % 3].button(categorie["nom_categorie"], key=f"sugg_libre_{i}", use_container_width=True):
                st.session_state["requete_libre_texte"] = categorie["nom_categorie"]
                st.session_state["requete_libre_force_en"] = categorie["requete_pubmed"]

    requete = st.text_input(
        "Ou tape ton propre sujet (français ou anglais)",
        key="requete_libre_texte",
        placeholder='ex. "ménopause", myo-inositol PCOS oocyte quality',
    )
    max_resultats = st.slider("Nombre d'études", 3, 10, 5, key="slider_libre")

    if requete:
        # Une suggestion cliquée porte déjà sa requête PubMed anglaise
        # validée (config/categories_problematique.yaml) : on l'utilise
        # directement plutôt que de retraduire le libellé français affiché.
        requete_a_chercher = st.session_state.pop("requete_libre_force_en", None) or requete
        with st.spinner("Recherche PubMed en cours (une requête par étude, quelques secondes)..."):
            df = rp.rechercher_requete_libre(requete_a_chercher, max_resultats=max_resultats)

        if df.empty:
            message = "Aucune étude trouvée pour cette requête sur PubMed, même après traduction en anglais."
            if not df.attrs.get("traduction_ok", True):
                message += " (la traduction automatique était indisponible — essaie de taper directement en anglais)"
            st.warning(message)
        else:
            st.success(f"{len(df)} étude(s) trouvée(s), voir détail ci-dessous.")
            if df.attrs.get("traduite"):
                st.caption(f"🔤 Recherché en anglais (traduit automatiquement) : *{df.attrs['requete_effective']}*")
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
