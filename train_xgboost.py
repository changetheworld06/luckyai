import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
import os

# 📥 Charger les 2555 tirages gagnants
print("📥 Chargement des données...")
df = pd.read_csv("loto_cleaned.csv")

# 🔍 Vérifier la présence des colonnes nécessaires
required_columns = ["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]
missing_cols = [col for col in required_columns if col not in df.columns]
if missing_cols:
    raise ValueError(f"❌ Colonnes manquantes dans le fichier CSV : {missing_cols}")

# ✅ Extraire les vrais tirages gagnants (X) et les cibles (y)
X_winners = df[required_columns].values
y_winners = X_winners  # Maintenant, y contient bien les 5 numéros gagnants

# 🔹 Générer des faux tirages comme classe 0 (perdants)
num_fake_samples = len(X_winners)
X_fake = np.array([np.random.choice(range(1, 50), 5, replace=False) for _ in range(num_fake_samples)])
y_fake = X_fake  # Les fausses grilles seront aussi des valeurs numériques entre 1 et 49

# 🔹 Concaténer les vrais et faux tirages
X = np.vstack((X_winners, X_fake))
y = np.vstack((y_winners, y_fake))  # y contient bien 5 numéros par ligne

# 🔀 Mélanger les données pour éviter un biais
shuffle_idx = np.random.permutation(len(X))
X, y = X[shuffle_idx], y[shuffle_idx]

# 🏋️‍♂️ Séparer les données en 80% entraînement / 20% test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ✅ Convertir les données en format DMatrix pour XGBoost
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# 🔧 Définition des paramètres du modèle XGBoost (régression)
params = {
    "objective": "reg:squarederror",  # Régression pour prédire 5 numéros
    "eval_metric": "rmse",  # Erreur quadratique moyenne
    "learning_rate": 0.01,
    "max_depth": 10,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "lambda": 2,
    "gamma": 1
}

# 🔄 Entraînement du modèle avec early stopping
print("🔄 Entraînement du modèle XGBoost en cours...")
evals = [(dtrain, "train"), (dtest, "eval")]
model = xgb.train(
    params,
    dtrain,
    num_boost_round=2000,
    evals=evals,
    early_stopping_rounds=50,
    verbose_eval=100
)

# ✅ Sauvegarde du modèle en format JSON
model.save_model("xgboost_model.json")
print("🎉 Modèle XGBoost sauvegardé sous xgboost_model.json")

# Faire une prédiction sur l'ensemble de test
y_pred = model.predict(dtest)

# ✅ Convertir les résultats en nombres entiers valides (1-49)
y_pred = np.clip(np.round(y_pred), 1, 49).astype(int)

# 🔧 Corriger les doublons en forçant l'unicité des numéros
y_pred_unique = [np.unique(row) for row in y_pred]

# 🔧 Si une ligne contient moins de 5 numéros uniques, on complète aléatoirement
for i, row in enumerate(y_pred_unique):
    while len(row) < 5:
        new_num = np.random.randint(1, 50)
        if new_num not in row:
            row = np.append(row, new_num)
    y_pred_unique[i] = np.sort(row)  # Trier les numéros

y_pred = np.array(y_pred_unique)  # Convertir en tableau numpy

# ✅ Affichage de quelques résultats après correction
print("\n🎯 Exemples de prédictions après correction :")
for i in range(5):
    print(f"🎰 Prédit : {y_pred[i]} | 🎯 Réel : {y_test[i]}")