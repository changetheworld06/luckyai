# engine/analyser.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import csv
import os
from datetime import datetime


@dataclass
class Draw:
    date: datetime
    numbers: List[int]
    specials: List[int]


@dataclass
class Stats:
    frequencies: Dict[int, int]
    last_seen: Dict[int, Optional[datetime]]
    total_draws: int


def load_history(csv_path: str, numbers_count: int, specials_count: int) -> List[Draw]:
    """
    Charge l'historique des tirages depuis un CSV.

    Format attendu minimal :
    date, n1, n2, ..., nN, s1, [s2]

    - date au format ISO (YYYY-MM-DD) ou jour/mois/année (DD/MM/YYYY)
    - les colonnes suivantes doivent être des entiers

    Si le fichier contient une ligne d'en-tête, elle est ignorée.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fichier CSV introuvable : {csv_path}")

    draws: List[Draw] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)

        # Détecte si la première ligne est un header (non-numérique dans les colonnes de numéros)
        has_header = False
        if first_row:
            try:
                # On tente de parser la date et le premier numéro
                _ = _parse_date(first_row[0])
                _ = int(first_row[1])
            except Exception:
                has_header = True

        # Si première ligne = header, on recommence derrière
        if not has_header and first_row:
            rows_iter = [first_row] + list(reader)
        else:
            rows_iter = list(reader)

        for row in rows_iter:
            if not row:
                continue

            try:
                date_str = row[0].strip()
                date = _parse_date(date_str)

                nums_part = row[1 : 1 + numbers_count]
                specs_part = row[1 + numbers_count : 1 + numbers_count + specials_count]

                numbers = [int(x.strip()) for x in nums_part]
                specials = [int(x.strip()) for x in specs_part]

                if len(numbers) != numbers_count or len(specials) != specials_count:
                    # Ligne invalide -> on ignore
                    continue

                draws.append(Draw(date=date, numbers=numbers, specials=specials))
            except Exception:
                # Ligne mal formée -> on l'ignore
                continue

    return draws


def _parse_date(raw: str) -> datetime:
    """
    Essaie plusieurs formats de date usuels :
      - YYYY-MM-DD
      - DD/MM/YYYY
    """
    raw = raw.strip()
    # format ISO
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        pass

    # format français
    try:
        return datetime.strptime(raw, "%d/%m/%Y")
    except Exception:
        pass

    # Si vraiment rien ne passe
    raise ValueError(f"Format de date inconnu : {raw}")


def compute_stats(draws: List[Draw], all_numbers: List[int]) -> Stats:
    """
    Calcule des stats basiques : fréquence et dernier tirage.
    """
    frequencies: Dict[int, int] = {n: 0 for n in all_numbers}
    last_seen: Dict[int, Optional[datetime]] = {n: None for n in all_numbers}

    for draw in draws:
        for n in draw.numbers + draw.specials:
            if n in frequencies:
                frequencies[n] += 1
                last_seen[n] = draw.date

    return Stats(
        frequencies=frequencies,
        last_seen=last_seen,
        total_draws=len(draws),
    )