from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import datetime
import os

from engine.analyser import load_history, compute_stats
from engine.scorer import score_numbers
from engine.generator import generate_grids

router = APIRouter()


class GridDetails(BaseModel):
    avg_main: float
    avg_specials: float
    high_main_count: int
    high_specials_count: int
    low_main_count: int
    low_specials_count: int


class Grid(BaseModel):
    main: List[int]
    specials: List[int]
    score: float
    details: GridDetails


class GenerateResponse(BaseModel):
    game: str
    generated_at: datetime
    grids: List[Grid]


@router.post("/generate", response_model=GenerateResponse)
def generate_euromillions_grids() -> GenerateResponse:
    """
    Génère 10 grilles Euromillions optimisées (version 1 : algo simple + score).
    """
    # Paramètres Euromillions
    all_main = list(range(1, 51))      # 1–50
    all_specials = list(range(1, 13))  # étoiles 1–12
    main_count = 5
    special_count = 2

    csv_path = os.path.join("data", "euromillions_history.csv")

    try:
        draws = load_history(csv_path, numbers_count=main_count, specials_count=special_count)
        stats_main = compute_stats(draws, all_main)
        stats_special = compute_stats(draws, all_specials)
    except FileNotFoundError:
        stats_main = compute_stats([], all_main)
        stats_special = compute_stats([], all_specials)

    scores_main = score_numbers(stats_main)
    scores_special = score_numbers(stats_special)

    raw_grids = generate_grids(
        all_main_numbers=all_main,
        all_special_numbers=all_specials,
        scores_main=scores_main,
        scores_special=scores_special,
        main_count=main_count,
        special_count=special_count,
        grids_count=10,
    )

    grids = [Grid(**g) for g in raw_grids]

    return GenerateResponse(
        game="euromillions",
        generated_at=datetime.utcnow(),
        grids=grids,
    )