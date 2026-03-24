"""
Mise a jour automatique des tirages Loto et EuroMillions.
Scrape les derniers resultats depuis l'API FDJ ouverte.
Usage: python update_draws.py
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_latest_loto():
    """Recupere les derniers tirages Loto depuis l'API FDJ (data.gouv)."""
    url = "https://data.loteries.api.fdj.fr/loto/tirages"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Fallback: try the open data API
        url2 = "https://www.loto.api.fdj.fr/loto/tirages"
        try:
            resp = requests.get(url2, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Impossible de recuperer les tirages Loto: {e}")
            return None

    rows = []
    for draw in data.get("tirages", data if isinstance(data, list) else []):
        try:
            date = draw.get("date_de_tirage", draw.get("date", ""))
            boules = draw.get("boules", draw.get("combinaison", []))
            chance = draw.get("numero_chance", draw.get("chance", None))
            if len(boules) >= 5 and date:
                rows.append({
                    "date_de_tirage": pd.to_datetime(date).strftime("%Y-%m-%d"),
                    "boule_1": int(boules[0]),
                    "boule_2": int(boules[1]),
                    "boule_3": int(boules[2]),
                    "boule_4": int(boules[3]),
                    "boule_5": int(boules[4]),
                    "numero_chance": int(chance) if chance else 0,
                })
        except (KeyError, IndexError, TypeError):
            continue
    return pd.DataFrame(rows) if rows else None


def update_loto_csv():
    """Met a jour loto_cleaned.csv avec les derniers tirages."""
    csv_path = os.path.join(BASE_DIR, "loto_cleaned.csv")
    existing = pd.read_csv(csv_path)
    existing["date_de_tirage"] = pd.to_datetime(existing["date_de_tirage"])
    last_date = existing["date_de_tirage"].max()
    print(f"Loto: {len(existing)} tirages, dernier: {last_date.strftime('%Y-%m-%d')}")

    new_data = fetch_latest_loto()
    if new_data is not None and len(new_data) > 0:
        new_data["date_de_tirage"] = pd.to_datetime(new_data["date_de_tirage"])
        new_draws = new_data[new_data["date_de_tirage"] > last_date]
        if len(new_draws) > 0:
            merged = pd.concat([existing, new_draws], ignore_index=True)
            merged = merged.sort_values("date_de_tirage").reset_index(drop=True)
            merged.to_csv(csv_path, index=False)
            print(f"  +{len(new_draws)} nouveaux tirages ajoutes (total: {len(merged)})")
        else:
            print("  Aucun nouveau tirage Loto.")
    else:
        print("  Pas de donnees API disponibles.")


def update_euromillions_csv():
    """Met a jour euromillions_cleaned.csv avec les derniers tirages."""
    csv_path = os.path.join(BASE_DIR, "euromillions_cleaned.csv")
    existing = pd.read_csv(csv_path)
    existing["date_de_tirage"] = pd.to_datetime(existing["date_de_tirage"])
    last_date = existing["date_de_tirage"].max()
    print(f"EuroMillions: {len(existing)} tirages, dernier: {last_date.strftime('%Y-%m-%d')}")
    # API EuroMillions - similar structure
    print("  Mise a jour EuroMillions: pas d'API publique disponible actuellement.")
    print("  Pour mettre a jour, telechargez le CSV depuis https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique")


if __name__ == "__main__":
    print("=== Mise a jour des tirages LuckyAI ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    update_loto_csv()
    print()
    update_euromillions_csv()
    print("\nTermine.")
