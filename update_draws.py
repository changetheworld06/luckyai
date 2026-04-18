"""
Mise a jour des tirages Loto et EuroMillions (LuckyAI).

Source : archives ZIP officielles FDJ (open data), republiees apres chaque
tirage.
  - Loto         : https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afp6
  - EuroMillions : https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afe6

Format cible (contrat attendu par analyzer.py — ne pas casser) :
  - loto_cleaned.csv         : date_de_tirage,boule_1..5,numero_chance
  - euromillions_cleaned.csv : date_de_tirage,boule_1..5,etoile_1,etoile_2
  Dates ISO YYYY-MM-DD, separateur virgule, tri chronologique ASC.

Logique :
  1. Telechargement du ZIP FDJ (timeout 30 s).
  2. Extraction de l'unique CSV contenu, lecture en memoire (sep=";").
  3. Projection sur les colonnes utiles, conversion de la date DD/MM/YYYY →
     YYYY-MM-DD, cast des numeros en int.
  4. Filtrage : on ne garde que les lignes dont date_de_tirage est > au max
     present dans le cleaned local (le cleaned DOIT exister ; sinon exit 1).
  5. Si aucun nouveau tirage : log "deja a jour" et sortie propre (pas de
     backup, pas d'ecriture).
  6. Sinon : backup timestampe du cleaned, puis ecriture atomique (.tmp +
     os.replace) du cleaned fusionne et trie ASC.

Usage :
  python update_draws.py                # Loto puis EuroMillions
  python update_draws.py --loto-only    # Loto uniquement
  python update_draws.py --euro-only    # EuroMillions uniquement
  python update_draws.py --dry-run      # affiche le diff, n'ecrit rien

Exit code :
  0 si tout est OK (y compris "deja a jour").
  1 si au moins un des deux jeux a echoue (l'autre est tout de meme tente).
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent

URL_LOTO = (
    "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/"
    "documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afp6"
)
URL_EURO = (
    "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/"
    "documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afe6"
)

HTTP_TIMEOUT_SECONDS = 30

LOTO_COLUMNS: list[str] = [
    "date_de_tirage",
    "boule_1",
    "boule_2",
    "boule_3",
    "boule_4",
    "boule_5",
    "numero_chance",
]
EURO_COLUMNS: list[str] = [
    "date_de_tirage",
    "boule_1",
    "boule_2",
    "boule_3",
    "boule_4",
    "boule_5",
    "etoile_1",
    "etoile_2",
]

LOTO_CSV = BASE_DIR / "loto_cleaned.csv"
EURO_CSV = BASE_DIR / "euromillions_cleaned.csv"


@dataclass(frozen=True)
class Job:
    name: str
    url: str
    target: Path
    columns: list[str]


def _fetch_zip(url: str) -> bytes:
    """Telecharge un ZIP FDJ et renvoie son contenu brut."""
    resp = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    if not resp.content:
        raise RuntimeError(f"Reponse vide depuis {url}")
    return resp.content


def _read_single_csv_from_zip(zip_bytes: bytes) -> pd.DataFrame:
    """Lit l'unique CSV contenu dans le ZIP FDJ (separateur ';')."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise RuntimeError(
                f"Le ZIP doit contenir exactement 1 fichier .csv, trouve : {csv_names}"
            )
        with zf.open(csv_names[0]) as handle:
            return pd.read_csv(handle, sep=";", encoding="utf-8", dtype=str)


def _project_and_cast(raw: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Garde les colonnes utiles, convertit la date et cast les numeros."""
    missing = [c for c in columns if c not in raw.columns]
    if missing:
        raise RuntimeError(
            f"Colonnes manquantes dans le CSV FDJ : {missing}. "
            f"Colonnes disponibles : {list(raw.columns)[:10]}..."
        )
    df = raw[columns].copy()
    df["date_de_tirage"] = pd.to_datetime(
        df["date_de_tirage"], format="%d/%m/%Y", errors="raise"
    )
    numeric_cols = [c for c in columns if c != "date_de_tirage"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(int)
    return df


def _load_existing(csv_path: Path) -> pd.DataFrame:
    """Charge le CSV cleaned existant. Erreur si absent."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Fichier cleaned introuvable : {csv_path}. "
            "Le script ne cree PAS de cleaned from scratch — refuser et investiguer."
        )
    df = pd.read_csv(csv_path)
    df["date_de_tirage"] = pd.to_datetime(df["date_de_tirage"], errors="raise")
    return df


def _backup(target: Path) -> Path:
    """Copie le fichier cible vers un .bak.YYYYMMDD_HHMMSS a cote."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = target.with_suffix(target.suffix + f".bak.{stamp}")
    bak.write_bytes(target.read_bytes())
    return bak


def _write_atomic(df: pd.DataFrame, target: Path) -> None:
    """Ecrit le DataFrame trie ASC dans target via un .tmp + os.replace."""
    out = df.copy()
    out["date_de_tirage"] = out["date_de_tirage"].dt.strftime("%Y-%m-%d")
    tmp = target.with_suffix(target.suffix + ".tmp")
    out.to_csv(tmp, index=False)
    os.replace(tmp, target)


def update_game(job: Job, dry_run: bool) -> None:
    """Pipeline complet pour un jeu : telecharger, transformer, fusionner, ecrire."""
    print(f"[{job.name}] Telechargement du ZIP FDJ...")
    zip_bytes = _fetch_zip(job.url)
    raw = _read_single_csv_from_zip(zip_bytes)
    fresh = _project_and_cast(raw, job.columns)

    existing = _load_existing(job.target)
    last_date = existing["date_de_tirage"].max()

    new_rows = (
        fresh[fresh["date_de_tirage"] > last_date]
        .sort_values("date_de_tirage")
        .reset_index(drop=True)
    )

    if new_rows.empty:
        print(
            f"[{job.name}] Deja a jour "
            f"(dernier = {last_date.strftime('%Y-%m-%d')}, total = {len(existing)})."
        )
        return

    first_new = new_rows["date_de_tirage"].iloc[0].strftime("%Y-%m-%d")
    last_new = new_rows["date_de_tirage"].iloc[-1].strftime("%Y-%m-%d")
    merged = (
        pd.concat([existing, new_rows], ignore_index=True)
        .sort_values("date_de_tirage")
        .reset_index(drop=True)
    )

    if dry_run:
        print(
            f"[{job.name}] DRY-RUN : +{len(new_rows)} tirages "
            f"({first_new} -> {last_new}). Total simule : {len(merged)}."
        )
        return

    bak = _backup(job.target)
    _write_atomic(merged, job.target)
    print(
        f"[{job.name}] +{len(new_rows)} tirages ({first_new} -> {last_new}). "
        f"Total : {len(merged)} tirages. Backup : {bak.name}"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Met a jour loto_cleaned.csv et euromillions_cleaned.csv depuis les ZIP FDJ.",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--loto-only", action="store_true", help="Ne traite que le Loto."
    )
    selection.add_argument(
        "--euro-only", action="store_true", help="Ne traite que l'EuroMillions."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait ajoute sans ecrire ni creer de backup.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    jobs: list[Job] = []
    if not args.euro_only:
        jobs.append(Job("Loto", URL_LOTO, LOTO_CSV, LOTO_COLUMNS))
    if not args.loto_only:
        jobs.append(Job("EuroMillions", URL_EURO, EURO_CSV, EURO_COLUMNS))

    print(
        f"=== Mise a jour des tirages LuckyAI "
        f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ==="
    )
    if args.dry_run:
        print("Mode : DRY-RUN (aucune ecriture, aucun backup).")

    errors = 0
    for job in jobs:
        try:
            update_game(job, dry_run=args.dry_run)
        except Exception as exc:
            errors += 1
            print(f"[{job.name}] ERREUR : {exc}", file=sys.stderr)
        print()

    if errors:
        print(f"Termine avec {errors} erreur(s).", file=sys.stderr)
        return 1
    print("Termine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
