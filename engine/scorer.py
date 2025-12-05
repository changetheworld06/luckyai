# engine/scorer.py
from __future__ import annotations
from typing import Dict
from datetime import datetime
from .analyser import Stats


def score_numbers(stats: Stats, as_of: datetime | None = None) -> Dict[int, float]:
    """
    Calcule un score basique pour chaque numéro.
    Idée :
      - plus la fréquence est élevée, plus le score est haut
      - plus le numéro est "en retard", plus on lui ajoute un bonus
    """
    if as_of is None:
        as_of = datetime.utcnow()

    if stats.total_draws == 0:
        # Pas de tirage -> tout le monde a le même score
        return {n: 1.0 for n in stats.frequencies.keys()}

    max_freq = max(stats.frequencies.values()) or 1

    scores: Dict[int, float] = {}

    for n, freq in stats.frequencies.items():
        freq_component = freq / max_freq  # entre 0 et 1

        last = stats.last_seen.get(n)
        if last is None:
            delay_days = 999  # jamais sorti
        else:
            delay_days = (as_of - last).days

        delay_component = min(delay_days / 100.0, 1.0)  # clamp à 1

        # pondération simple (on améliorera plus tard)
        score = 0.6 * freq_component + 0.4 * delay_component
        scores[n] = score

    return scores