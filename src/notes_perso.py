"""Notes personnelles par étude — ajouté le 27/08 à la demande de Gisèle :
garder une trace de ce qui a déjà été lu/décidé, pour ne pas relancer la
même recherche dans 2 mois sans se souvenir de la conclusion.

Persistance simple par fichier CSV local (pas de base de données, ce
projet tourne en local, pas déployé multi-utilisateurs pour l'instant).
Une note vide n'est jamais enregistrée — évite d'accumuler des lignes
vides à chaque relance du dashboard.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NOTES_FILE = DATA_DIR / "notes_perso.csv"


def charger_notes():
    """Retourne {pmid: note}. Fichier absent -> dict vide, jamais une
    erreur qui casserait le dashboard au premier lancement."""
    if not NOTES_FILE.exists():
        return {}
    df = pd.read_csv(NOTES_FILE, dtype=str)
    return dict(zip(df["pmid"], df["note"]))


def sauvegarder_note(pmid, note):
    """Ajoute/modifie/supprime (si note vide) la note d'un PMID. Réécrit
    tout le fichier à chaque sauvegarde — volume attendu (quelques
    dizaines de notes perso), pas besoin d'une écriture incrémentale."""
    notes = charger_notes()
    pmid = str(pmid)
    if note and note.strip():
        notes[pmid] = note.strip()
    else:
        notes.pop(pmid, None)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if notes:
        df = pd.DataFrame([{"pmid": k, "note": v} for k, v in notes.items()])
        df.to_csv(NOTES_FILE, index=False, encoding="utf-8")
    elif NOTES_FILE.exists():
        NOTES_FILE.unlink()  # plus aucune note -> pas de fichier vide qui traine


def main():
    sauvegarder_note("29587861", "A relire avant la prochaine prise de sang.")
    notes = charger_notes()
    print(f"{len(notes)} note(s) enregistrée(s) :")
    for pmid, note in notes.items():
        print(f"  [{pmid}] {note}")


if __name__ == "__main__":
    main()
