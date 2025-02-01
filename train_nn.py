import tensorflow as tf
import numpy as np
import pandas as pd
import os
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM, Reshape

# 🔹 Charger les données
data_path = "loto_cleaned.csv"
if not os.path.exists(data_path):
    raise FileNotFoundError(f"❌ Fichier des tirages non trouvé : {data_path}")

df = pd.read_csv(data_path)

# 🔹 Vérifier et nettoyer les colonnes
required_columns = ["boule_1", "boule_2", "boule_3", "boule_4", "boule_5", "numero_chance"]
for col in required_columns:
    if col not in df.columns:
        raise ValueError(f"❌ Colonne manquante dans le fichier CSV : {col}")

# 🔹 S'assurer que les numéros sont bien des entiers et sans valeurs manquantes
df = df.dropna()  # Supprimer les lignes vides
df[required_columns] = df[required_columns].astype(int)  # Convertir en entiers

# 🔹 Extraire les données
X = df[["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]].values
y = df["numero_chance"].values

# 🔹 Vérification des valeurs de `numero_chance`
if not all(1 <= num <= 10 for num in y):
    raise ValueError(f"❌ Valeurs incorrectes trouvées dans 'numero_chance'. Vérifiez le fichier CSV.")

# 🔹 Générer 100x plus de fausses grilles (évite les grilles trop similaires)
num_fake_samples = len(df) * 100  # Générer 100x plus de perdants que de gagnants
X_fake = np.array([np.random.choice(range(1, 50), 5, replace=False) for _ in range(num_fake_samples)])
X_fake = np.hstack((X_fake, np.random.randint(1, 11, (num_fake_samples, 1))))  # Ajouter numéro chance

# 🔹 Assigner les labels : 1 = gagnant, 0 = perdant
y_fake = np.zeros(len(X_fake))  # Classe 0 pour les faux tirages
y_winners = np.ones(len(df))    # Classe 1 pour les vrais tirages

# 🔹 Fusionner les données
X = np.vstack((df[["boule_1", "boule_2", "boule_3", "boule_4", "boule_5", "numero_chance"]].values, X_fake))
y = np.hstack((y_winners, y_fake))

# 🔹 Encodage one-hot des numéros gagnants (0-48 pour 49 numéros possibles)
y_numbers = np.zeros((len(X), 49))
for i, row in enumerate(X):
    y_numbers[i, np.array(row) - 1] = 1  # Décalage de -1 pour indexation

# 🔹 Encodage one-hot du numéro chance (0-9 pour 10 numéros possibles)
y_chance = np.zeros((len(y), 10))
for i, num in enumerate(y):
    y_chance[i, int(num) - 1] = 1  # Assurer que num est bien un entier

# 🔹 Normalisation des entrées (mettre entre 0 et 1)
X = X / 49.0  

# 🔹 Séparation en train/test
X_train, X_test, y_train_numbers, y_test_numbers = train_test_split(X, y_numbers, test_size=0.2, random_state=42)
_, _, y_train_chance, y_test_chance = train_test_split(X, y_chance, test_size=0.2, random_state=42)

# 🔹 Réseau amélioré avec LSTM
model = Sequential([
    Reshape((5, 1), input_shape=(5,)),  # Adapter l'entrée pour LSTM
    LSTM(128, return_sequences=True),
    Dropout(0.3),
    LSTM(64, return_sequences=False),
    Dropout(0.3),
    Dense(49, activation="softmax")  # Prédictions des 49 numéros
])

# 🔹 Réseau pour le numéro chance
model_chance = Sequential([
    Reshape((5, 1), input_shape=(5,)),  # Adapter l'entrée
    LSTM(64, return_sequences=True),
    Dropout(0.3),
    LSTM(32, return_sequences=False),
    Dropout(0.3),
    Dense(10, activation="softmax")  # Prédiction du numéro chance
])

# 🔹 Compilation des modèles
model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
model_chance.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

# 🔄 Entraînement
print("🔄 Entraînement du modèle (grilles)...")
model.fit(X_train, y_train_numbers, epochs=5000, batch_size=64, validation_data=(X_test, y_test_numbers))

print("🔄 Entraînement du modèle (numéro chance)...")
model_chance.fit(X_train, y_train_chance, epochs=5000, batch_size=64, validation_data=(X_test, y_test_chance))

# ✅ Évaluation
loss, accuracy = model.evaluate(X_test, y_test_numbers)
print(f"✅ Précision pour les grilles : {accuracy:.4f}")

loss_chance, accuracy_chance = model_chance.evaluate(X_test, y_test_chance)
print(f"✅ Précision pour le numéro chance : {accuracy_chance:.4f}")

# 🎉 Sauvegarde du modèle
model.save("lucky_ai_nn.keras")
model_chance.save("lucky_ai_nn_chance.keras")
print("🎉 Modèles sauvegardés !")