# engine/generator.py
from __future__ import annotations
from typing import List, Dict, Any
import random


def weighted_choice(numbers: List[int], scores: Dict[int, float]) -> int:
    """
    Tire un numéro parmi 'numbers' avec une probabilité proportionnelle à son score.
    """
    weights = [max(scores.get(n, 0.0), 0.0001) for n in numbers]
    total = sum(weights)
    probs = [w / total for w in weights]
    return random.choices(numbers, weights=probs, k=1)[0]


def compute_grid_score(
    main: List[int],
    specials: List[int],
    scores_main: Dict[int, float],
    scores_special: Dict[int, float],
) -> float:
    """
    Calcule un score global pour la grille.

    Étapes :
    - moyenne des scores des numéros principaux / spéciaux (0–1 environ)
    - pondération 70 % principaux / 30 % spéciaux
    - mise à l'échelle pour mieux exploiter le 0–100 :
      on "étire" les valeurs, puis on tronque entre 0 et 100
    """
    if not main and not specials:
        return 0.0

    # Moyenne des numéros principaux
    if main:
        main_scores = [scores_main.get(n, 0.0) for n in main]
        avg_main = sum(main_scores) / len(main_scores)
    else:
        avg_main = 0.0

    # Moyenne des numéros spéciaux
    if specials:
        special_scores = [scores_special.get(n, 0.0) for n in specials]
        avg_special = sum(special_scores) / len(special_scores)
    else:
        avg_special = 0.0

    # Score brut entre ~0 et 1
    grid_score_01 = 0.7 * avg_main + 0.3 * avg_special

    # Étirement autour de 0.5 pour mieux occuper 0–100
    centered = grid_score_01 - 0.5          # autour de 0
    stretched = centered * 3.0 + 0.5        # on amplifie les écarts

    raw_0_100 = stretched * 100.0
    clamped = max(0.0, min(100.0, raw_0_100))

    return round(clamped, 1)


def compute_grid_details(
    main: List[int],
    specials: List[int],
    scores_main: Dict[int, float],
    scores_special: Dict[int, float],
) -> Dict[str, Any]:
    """
    Calcule des détails sur la grille, basés sur les scores individuels (0–1).

    - moyenne des scores principaux / spéciaux
    - nombre de numéros "forts" (score >= 0.7)
    - nombre de numéros "faibles" (score <= 0.3)
    """
    main_scores = [scores_main.get(n, 0.0) for n in main] if main else []
    special_scores = [scores_special.get(n, 0.0) for n in specials] if specials else []

    avg_main = sum(main_scores) / len(main_scores) if main_scores else 0.0
    avg_special = sum(special_scores) / len(special_scores) if special_scores else 0.0

    high_main = sum(1 for s in main_scores if s >= 0.7)
    high_special = sum(1 for s in special_scores if s >= 0.7)

    low_main = sum(1 for s in main_scores if s <= 0.3)
    low_special = sum(1 for s in special_scores if s <= 0.3)

    return {
        "avg_main": round(avg_main, 3),
        "avg_specials": round(avg_special, 3),
        "high_main_count": int(high_main),
        "high_specials_count": int(high_special),
        "low_main_count": int(low_main),
        "low_specials_count": int(low_special),
    }


def generate_grids(
    all_main_numbers: List[int],
    all_special_numbers: List[int],
    scores_main: Dict[int, float],
    scores_special: Dict[int, float],
    main_count: int,
    special_count: int,
    grids_count: int = 10,
) -> List[Dict[str, Any]]:
    """
    Génère 'grids_count' grilles.
    Retourne une liste de dict :
      {
        "main": [...],
        "specials": [...],
        "score": 87.3,
        "details": { ... }
      }
    """
    grids: List[Dict[str, Any]] = []

    for _ in range(grids_count):
        main = []
        specials = []

        # Tirage des numéros principaux
        available_main = all_main_numbers.copy()
        for _ in range(main_count):
            n = weighted_choice(available_main, scores_main)
            main.append(n)
            available_main.remove(n)

        # Tirage des numéros spéciaux
        available_specials = all_special_numbers.copy()
        for _ in range(special_count):
            n = weighted_choice(available_specials, scores_special)
            specials.append(n)
            available_specials.remove(n)

        main.sort()
        specials.sort()

        score = compute_grid_score(main, specials, scores_main, scores_special)
        details = compute_grid_details(main, specials, scores_main, scores_special)

        grids.append(
            {
                "main": main,
                "specials": specials,
                "score": score,
                "details": details,
            }
        )

    return grids