"""
LuckyAI - Moteur d'analyse statistique multi-strategie pour le Loto et EuroMillions.
Analyse les patterns historiques et genere des grilles optimisees.
"""
import pandas as pd
import numpy as np
from itertools import combinations
from collections import Counter


def _py(val):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    return val


class LotoAnalyzer:
    def __init__(self, csv_path="loto_cleaned.csv"):
        df = pd.read_csv(csv_path)
        df["date_de_tirage"] = pd.to_datetime(df["date_de_tirage"])
        df = df.sort_values("date_de_tirage").reset_index(drop=True)
        self.df = df
        self.cols = ["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]
        self.draws = df[self.cols].values
        self.dates = df["date_de_tirage"].values
        self.chances = df["numero_chance"].values
        self.total = len(df)

    # --- Numeros chauds : les plus frequents sur les N derniers tirages ---
    def hot_numbers(self, window=50):
        recent = self.draws[-window:]
        counter = Counter(recent.flatten())
        results = []
        for num in range(1, 50):
            count = counter.get(num, 0)
            results.append({"num": num, "count": count, "pct": round(count / window * 100, 1)})
        return sorted(results, key=lambda x: -x["count"])

    # --- Numeros froids : les moins frequents sur les N derniers tirages ---
    def cold_numbers(self, window=50):
        return list(reversed(self.hot_numbers(window)))

    # --- Gap : nombre de tirages depuis la derniere apparition ---
    def gaps(self):
        results = []
        for num in range(1, 50):
            positions = np.where(np.any(self.draws == num, axis=1))[0]
            if len(positions) == 0:
                gap = self.total
                avg_gap = self.total
            else:
                gap = self.total - 1 - positions[-1]
                if len(positions) > 1:
                    diffs = np.diff(positions)
                    avg_gap = round(float(np.mean(diffs)), 1)
                else:
                    avg_gap = float(self.total)
            overdue = round(float(gap / avg_gap), 2) if avg_gap > 0 else 0
            results.append({"num": num, "gap": int(gap), "avg_gap": float(avg_gap), "overdue": float(overdue)})
        return sorted(results, key=lambda x: -x["overdue"])

    # --- Paires les plus frequentes ---
    def frequent_pairs(self, top_n=15):
        pair_counter = Counter()
        for draw in self.draws:
            for pair in combinations(sorted(draw), 2):
                pair_counter[pair] += 1
        top = pair_counter.most_common(top_n)
        return [{"pair": [int(x) for x in p], "count": int(c)} for p, c in top]

    # --- Triplets les plus frequents ---
    def frequent_triplets(self, top_n=10):
        triplet_counter = Counter()
        for draw in self.draws:
            for triplet in combinations(sorted(draw), 3):
                triplet_counter[triplet] += 1
        top = triplet_counter.most_common(top_n)
        return [{"triplet": [int(x) for x in t], "count": int(c)} for t, c in top]

    # --- Distribution pairs/impairs et bas/hauts ---
    def distribution(self):
        all_nums = self.draws.flatten()
        total_nums = len(all_nums)
        odd = int(np.sum(all_nums % 2 == 1))
        even = total_nums - odd
        low = int(np.sum(all_nums <= 24))
        high = total_nums - low
        # Distribution par dizaine
        decades = {}
        for d in range(5):
            lo, hi = d * 10 + 1, (d + 1) * 10
            if d == 4:
                hi = 49
            label = f"{lo}-{hi}"
            decades[label] = int(np.sum((all_nums >= lo) & (all_nums <= hi)))
        return {
            "odd_pct": round(odd / total_nums * 100, 1),
            "even_pct": round(even / total_nums * 100, 1),
            "low_pct": round(low / total_nums * 100, 1),
            "high_pct": round(high / total_nums * 100, 1),
            "decades": decades,
        }

    # --- Frequence globale de chaque numero ---
    def global_frequency(self):
        counter = Counter(self.draws.flatten())
        results = []
        for num in range(1, 50):
            count = int(counter.get(num, 0))
            results.append({
                "num": num,
                "count": count,
                "pct": round(float(count / self.total * 100), 1),
                "expected_pct": round(5 / 49 * 100, 1),
            })
        return sorted(results, key=lambda x: -x["count"])

    # --- Numeros chance les plus frequents ---
    def chance_frequency(self):
        valid = self.chances[~np.isnan(self.chances)].astype(int)
        counter = Counter(valid)
        return [{"num": n, "count": counter.get(n, 0)} for n in range(1, 11)]

    # --- Derniers tirages ---
    def last_draws(self, n=10):
        results = []
        for i in range(max(0, self.total - n), self.total):
            results.append({
                "date": str(self.dates[i])[:10],
                "numbers": sorted([int(x) for x in self.draws[i]]),
                "chance": int(self.chances[i]) if not np.isnan(self.chances[i]) else None,
            })
        return list(reversed(results))

    # --- Score composite : combine toutes les strategies ---
    def composite_scores(self):
        hot = {x["num"]: x["count"] for x in self.hot_numbers(50)}
        gap_data = {x["num"]: x for x in self.gaps()}
        freq = {x["num"]: x["count"] for x in self.global_frequency()}

        scores = []
        for num in range(1, 50):
            # Poids : chaud recent (40%) + retard excessif (35%) + frequence globale (25%)
            hot_score = hot.get(num, 0) / 50  # normalise 0-1
            overdue_score = min(gap_data[num]["overdue"] / 3, 1)  # normalise, cap a 1
            freq_score = freq.get(num, 0) / self.total * 49 / 5  # normalise vs expected
            composite = float(hot_score * 0.4 + overdue_score * 0.35 + freq_score * 0.25)
            scores.append({"num": num, "score": round(composite, 4),
                           "hot": int(hot.get(num, 0)), "gap": int(gap_data[num]["gap"]),
                           "overdue": float(gap_data[num]["overdue"])})
        return sorted(scores, key=lambda x: -x["score"])

    # --- Generation de grille selon strategie ---
    def generate_grid(self, strategy="composite"):
        if strategy == "composite":
            return self._gen_composite()
        elif strategy == "hot":
            return self._gen_hot()
        elif strategy == "cold":
            return self._gen_cold()
        elif strategy == "balanced":
            return self._gen_balanced()
        else:
            return self._gen_composite()

    def _weighted_pick(self, weights, k=5):
        """Tire k numeros (1-49) avec probabilites proportionnelles aux poids."""
        nums = np.arange(1, 50)
        w = np.array([weights.get(n, 0.01) for n in nums], dtype=float)
        w = w / w.sum()
        chosen = np.random.choice(nums, size=k, replace=False, p=w)
        return sorted([int(x) for x in chosen])

    def _gen_composite(self):
        scores = {x["num"]: x["score"] for x in self.composite_scores()}
        grille = self._weighted_pick(scores)
        chance = self._pick_chance()
        return {"grille": grille, "numero_chance": chance,
                "strategy": "composite",
                "explanation": "Combine frequence recente, retard et historique global"}

    def _gen_hot(self):
        hot = {x["num"]: x["count"] + 1 for x in self.hot_numbers(30)}
        grille = self._weighted_pick(hot)
        chance = self._pick_chance()
        return {"grille": grille, "numero_chance": chance,
                "strategy": "hot",
                "explanation": "Favorise les numeros les plus tires recemment"}

    def _gen_cold(self):
        gaps = {x["num"]: x["overdue"] + 0.1 for x in self.gaps()}
        grille = self._weighted_pick(gaps)
        chance = self._pick_chance()
        return {"grille": grille, "numero_chance": chance,
                "strategy": "cold",
                "explanation": "Favorise les numeros en retard excessif"}

    def _gen_balanced(self):
        # Equilibre pairs/impairs (2-3 ou 3-2) et bas/hauts (2-3 ou 3-2)
        scores = {x["num"]: x["score"] for x in self.composite_scores()}
        for _ in range(100):
            grille = self._weighted_pick(scores)
            odd = sum(1 for n in grille if n % 2 == 1)
            low = sum(1 for n in grille if n <= 24)
            if odd in (2, 3) and low in (2, 3):
                break
        chance = self._pick_chance()
        return {"grille": grille, "numero_chance": chance,
                "strategy": "balanced",
                "explanation": "Equilibre pairs/impairs et bas/hauts pour une couverture optimale"}

    def _pick_chance(self):
        freq = self.chance_frequency()
        weights = {x["num"]: x["count"] + 1 for x in freq}
        nums = list(weights.keys())
        w = np.array([weights[n] for n in nums], dtype=float)
        w = w / w.sum()
        return int(np.random.choice(nums, p=w))

    # --- Analyse complete pour l'API ---
    def full_analysis(self):
        return {
            "total_draws": self.total,
            "last_draw_date": str(self.dates[-1])[:10],
            "hot": self.hot_numbers(50),
            "cold": self.cold_numbers(50),
            "gaps": self.gaps()[:15],
            "pairs": self.frequent_pairs(15),
            "triplets": self.frequent_triplets(10),
            "distribution": self.distribution(),
            "global_freq": self.global_frequency(),
            "chance_freq": self.chance_frequency(),
            "last_draws": self.last_draws(10),
            "composite": self.composite_scores(),
        }


class EuroMillionsAnalyzer:
    """Analyse statistique pour EuroMillions (5 numeros 1-50 + 2 etoiles 1-12)."""

    def __init__(self, csv_path="euromillions_cleaned.csv"):
        df = pd.read_csv(csv_path)
        if "date_de_tirage" in df.columns:
            df["date_de_tirage"] = pd.to_datetime(df["date_de_tirage"])
            df = df.sort_values("date_de_tirage").reset_index(drop=True)
            self.dates = df["date_de_tirage"].values
        else:
            self.dates = None
        self.df = df
        self.num_cols = ["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]
        self.star_cols = ["etoile_1", "etoile_2"]
        self.draws = df[self.num_cols].values
        self.stars = df[self.star_cols].values
        self.total = len(df)
        self.max_num = 50
        self.max_star = 12

    def hot_numbers(self, window=50):
        recent = self.draws[-window:]
        counter = Counter(recent.flatten())
        results = []
        for num in range(1, self.max_num + 1):
            count = counter.get(num, 0)
            results.append({"num": num, "count": count, "pct": round(count / window * 100, 1)})
        return sorted(results, key=lambda x: -x["count"])

    def cold_numbers(self, window=50):
        return list(reversed(self.hot_numbers(window)))

    def hot_stars(self, window=50):
        recent = self.stars[-window:]
        counter = Counter(recent.flatten())
        results = []
        for num in range(1, self.max_star + 1):
            count = counter.get(num, 0)
            results.append({"num": num, "count": count, "pct": round(count / window * 100, 1)})
        return sorted(results, key=lambda x: -x["count"])

    def gaps(self):
        results = []
        for num in range(1, self.max_num + 1):
            positions = np.where(np.any(self.draws == num, axis=1))[0]
            if len(positions) == 0:
                gap = self.total
                avg_gap = float(self.total)
            else:
                gap = self.total - 1 - positions[-1]
                avg_gap = round(float(np.mean(np.diff(positions))), 1) if len(positions) > 1 else float(self.total)
            overdue = round(float(gap / avg_gap), 2) if avg_gap > 0 else 0
            results.append({"num": num, "gap": int(gap), "avg_gap": float(avg_gap), "overdue": float(overdue)})
        return sorted(results, key=lambda x: -x["overdue"])

    def star_gaps(self):
        results = []
        for num in range(1, self.max_star + 1):
            positions = np.where(np.any(self.stars == num, axis=1))[0]
            if len(positions) == 0:
                gap = self.total
                avg_gap = float(self.total)
            else:
                gap = self.total - 1 - positions[-1]
                avg_gap = round(float(np.mean(np.diff(positions))), 1) if len(positions) > 1 else float(self.total)
            overdue = round(float(gap / avg_gap), 2) if avg_gap > 0 else 0
            results.append({"num": num, "gap": int(gap), "avg_gap": float(avg_gap), "overdue": float(overdue)})
        return sorted(results, key=lambda x: -x["overdue"])

    def frequent_pairs(self, top_n=15):
        pair_counter = Counter()
        for draw in self.draws:
            for pair in combinations(sorted(draw), 2):
                pair_counter[pair] += 1
        top = pair_counter.most_common(top_n)
        return [{"pair": [int(x) for x in p], "count": int(c)} for p, c in top]

    def distribution(self):
        all_nums = self.draws.flatten()
        total_nums = len(all_nums)
        odd = int(np.sum(all_nums % 2 == 1))
        even = total_nums - odd
        low = int(np.sum(all_nums <= 25))
        high = total_nums - low
        return {
            "odd_pct": round(odd / total_nums * 100, 1),
            "even_pct": round(even / total_nums * 100, 1),
            "low_pct": round(low / total_nums * 100, 1),
            "high_pct": round(high / total_nums * 100, 1),
        }

    def global_frequency(self):
        counter = Counter(self.draws.flatten())
        results = []
        for num in range(1, self.max_num + 1):
            count = int(counter.get(num, 0))
            results.append({"num": num, "count": count, "pct": round(float(count / self.total * 100), 1)})
        return sorted(results, key=lambda x: -x["count"])

    def composite_scores(self):
        hot = {x["num"]: x["count"] for x in self.hot_numbers(50)}
        gap_data = {x["num"]: x for x in self.gaps()}
        freq = {x["num"]: x["count"] for x in self.global_frequency()}
        scores = []
        for num in range(1, self.max_num + 1):
            hot_score = hot.get(num, 0) / 50
            overdue_score = min(gap_data[num]["overdue"] / 3, 1)
            freq_score = freq.get(num, 0) / self.total * 50 / 5
            composite = float(hot_score * 0.4 + overdue_score * 0.35 + freq_score * 0.25)
            scores.append({"num": num, "score": round(composite, 4),
                           "hot": int(hot.get(num, 0)), "gap": int(gap_data[num]["gap"]),
                           "overdue": float(gap_data[num]["overdue"])})
        return sorted(scores, key=lambda x: -x["score"])

    def star_scores(self):
        hot = {x["num"]: x["count"] for x in self.hot_stars(50)}
        gap_data = {x["num"]: x for x in self.star_gaps()}
        scores = []
        for num in range(1, self.max_star + 1):
            hot_score = hot.get(num, 0) / 50
            overdue_score = min(gap_data[num]["overdue"] / 3, 1)
            composite = float(hot_score * 0.5 + overdue_score * 0.5)
            scores.append({"num": num, "score": round(composite, 4)})
        return sorted(scores, key=lambda x: -x["score"])

    def generate_grid(self, strategy="composite"):
        if strategy == "composite":
            scores = {x["num"]: x["score"] for x in self.composite_scores()}
        elif strategy == "hot":
            scores = {x["num"]: x["count"] + 1 for x in self.hot_numbers(30)}
        elif strategy == "cold":
            scores = {x["num"]: x["overdue"] + 0.1 for x in self.gaps()}
        else:
            scores = {x["num"]: x["score"] for x in self.composite_scores()}

        # Pick 5 numbers (1-50)
        nums = np.arange(1, self.max_num + 1)
        w = np.array([scores.get(n, 0.01) for n in nums], dtype=float)
        w = w / w.sum()
        chosen = sorted([int(x) for x in np.random.choice(nums, size=5, replace=False, p=w)])

        # Pick 2 stars (1-12) weighted
        star_sc = {x["num"]: x["score"] for x in self.star_scores()}
        star_nums = np.arange(1, self.max_star + 1)
        sw = np.array([star_sc.get(n, 0.01) for n in star_nums], dtype=float)
        sw = sw / sw.sum()
        stars = sorted([int(x) for x in np.random.choice(star_nums, size=2, replace=False, p=sw)])

        explanations = {
            "composite": "Combine frequence recente, retard et historique global",
            "hot": "Favorise les numeros les plus tires recemment",
            "cold": "Favorise les numeros en retard excessif",
        }
        return {"numeros": chosen, "etoiles": stars, "strategy": strategy,
                "explanation": explanations.get(strategy, explanations["composite"])}

    def full_analysis(self):
        result = {
            "total_draws": self.total,
            "hot": self.hot_numbers(50),
            "cold": self.cold_numbers(50),
            "hot_stars": self.hot_stars(50),
            "gaps": self.gaps()[:15],
            "star_gaps": self.star_gaps(),
            "pairs": self.frequent_pairs(15),
            "distribution": self.distribution(),
            "global_freq": self.global_frequency(),
            "composite": self.composite_scores(),
            "star_scores": self.star_scores(),
        }
        if self.dates is not None:
            result["last_draw_date"] = str(self.dates[-1])[:10]
        return result
