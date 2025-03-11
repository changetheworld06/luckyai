import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
import os

# Charger et préparer les données de l'EuroMillions
df = pd.read_csv("euromillions_cleaned.csv", sep='\t')  # Utiliser le bon séparateur

# Afficher les colonnes pour vérification
print("Colonnes présentes dans le fichier CSV :", df.columns)

# Vérification et préparation des données
required_columns = ["boule_1", "boule_2", "boule_3", "boule_4", "boule_5", "etoile_1", "etoile_2"]
missing_cols = [col for col in required_columns if col not in df.columns]
if missing_cols:
    raise ValueError(f"Colonnes manquantes dans le fichier CSV : {missing_cols}")

# Convertir les colonnes en nombres
for col in required_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Extraire les numéros principaux et les étoiles
X_numbers = df[["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]].values
X_stars = df[["etoile_1", "etoile_2"]].values

# Générer des faux tirages
num_fake_samples = len(df)
X_fake_numbers = np.array([np.random.choice(range(1, 51), 5, replace=False) for _ in range(num_fake_samples)])
X_fake_stars = np.array([np.random.choice(range(1, 13), 2, replace=False) for _ in range(num_fake_samples)])

# Concaténer et mélanger les données
X_numbers = np.vstack((X_numbers, X_fake_numbers))
X_stars = np.vstack((X_stars, X_fake_stars))
shuffle_idx = np.random.permutation(len(X_numbers))
X_numbers, X_stars = X_numbers[shuffle_idx], X_stars[shuffle_idx]

# Séparer les données
X_train_numbers, X_test_numbers, X_train_stars, X_test_stars = train_test_split(
    X_numbers, X_stars, test_size=0.2, random_state=42)

# Créer des étiquettes factices pour l'entraînement (par exemple, utiliser les mêmes valeurs que les données)
y_train_numbers = X_train_numbers.copy()
y_test_numbers = X_test_numbers.copy()
y_train_stars = X_train_stars.copy()
y_test_stars = X_test_stars.copy()

# Convertir en DMatrix
dtrain_numbers = xgb.DMatrix(X_train_numbers, label=y_train_numbers)
dtest_numbers = xgb.DMatrix(X_test_numbers, label=y_test_numbers)
dtrain_stars = xgb.DMatrix(X_train_stars, label=y_train_stars)
dtest_stars = xgb.DMatrix(X_test_stars, label=y_test_stars)

# Paramètres et entraînement des modèles
params = {
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "learning_rate": 0.01,
    "max_depth": 10,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "lambda": 2,
    "gamma": 1
}

model_numbers = xgb.train(
    params,
    dtrain_numbers,
    num_boost_round=2000,
    evals=[(dtrain_numbers, "train"), (dtest_numbers, "eval")],
    early_stopping_rounds=50,
    verbose_eval=100
)

model_stars = xgb.train(
    params,
    dtrain_stars,
    num_boost_round=2000,
    evals=[(dtrain_stars, "train"), (dtest_stars, "eval")],
    early_stopping_rounds=50,
    verbose_eval=100
)

# Sauvegarder les modèles
model_numbers.save_model("xgboost_euromillions_numbers_model.json")
model_stars.save_model("xgboost_euromillions_stars_model.json")
print("Modèles EuroMillions sauvegardés !")
