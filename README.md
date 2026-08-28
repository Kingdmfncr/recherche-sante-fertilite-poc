# Recherche Santé & Fertilité (données réelles)

🔗 **Démo live** : [recherche-sante-fertilite-poc.streamlit.app](https://recherche-sante-fertilite-poc.streamlit.app/)

⚠️ **Projet personnel**, pas un avis médical. Toute information affichée cite un vrai PMID vérifiable sur [pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov) — jamais une conclusion inventée. Consulter un professionnel de santé avant toute décision (supplémentation, dosage) basée sur une étude trouvée ici.

Je voulais comprendre comment construire un outil de recherche santé qui ne dit jamais n'importe quoi : interroger de vraies bases (INSEE, PubMed), citer systématiquement la source exacte, et signaler explicitement quand une information n'a pas été trouvée plutôt que de la deviner — alors j'ai construit ce projet, étape par étape.

## Ce que ça fait

- **Tendances démographiques réelles** (`src/extraction_insee.py`) : taux de fécondité par tranche d'âge et âge moyen à la maternité en France, 1957-2025, via l'API officielle INSEE Melodi.
- **Recherche de littérature scientifique réelle** (`src/recherche_pubmed.py`) : interroge PubMed (NCBI E-utilities) sur un sujet donné, retourne les vraies études trouvées (titre, revue, date, PMID).
- **Extraction de détails cliniques** (`src/extraction_details_etudes.py`) : dosage testé, durée de l'étude, taille de l'échantillon, type d'étude, effet observé et conclusion — extraits du texte réel du résumé (règles déclaratives, `config/patterns_cliniques.yaml`), jamais devinés. Un champ non trouvé reste vide.
- **Recherche libre-service** (`dashboards/app.py`) : n'importe quel sujet tapé par l'utilisateur relance la même recherche PubMed en direct, pas seulement une liste de sujets prédéfinis.

## Avancement

- ✅ Extraction INSEE (séries longues fécondité), 4 tests.
- ✅ Recherche PubMed sur 9 sujets suivis (sport & grossesse, CoQ10, vitamine D, préconception, périnatalité, NAC, myo-inositol, PQQ, oméga-3 DHA).
- ✅ Extraction déclarative dosage/durée/effectif/type d'étude + effet observé/conclusion (sections structurées RESULTS/CONCLUSION). Bug réel trouvé et corrigé en testant : un premier jet du regex de dosage lisait "CoQ10 group" comme un dosage "10 g".
- ✅ Recherche libre-service (dashboard), testée dans le navigateur avec une requête inédite.
- ⏳ Visualisation des séries temporelles INSEE (pas encore fait).
- ⏳ Lecture qualitative des rapports officiels français (Ministère de la Santé, Santé Publique France).

## Stack

Python · Pandas · PyYAML (règles déclaratives) · Streamlit.

## Lancer en local

```bash
pip install -r requirements.txt

python src/extraction_insee.py       # séries INSEE fécondité
python src/recherche_pubmed.py       # recherche sur les 9 sujets suivis
python src/extraction_details_etudes.py  # exemple d'extraction sur une étude

streamlit run dashboards/app.py      # recherche libre-service

pytest tests/ -v
```

---

**Gisèle Metouck** — [GitHub](https://github.com/Kingdmfncr)
