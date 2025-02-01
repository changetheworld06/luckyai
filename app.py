from flask import Flask, jsonify, render_template
import xgboost as xgb
import numpy as np
import pandas as pd
import stripe
from dotenv import load_dotenv
import os
from random import shuffle

# 🔹 Charger les variables d'environnement
load_dotenv()  # Charger les variables d'environnement
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # Charger la clé Live

# 🔹 Définir le chemin du modèle XGBoost
model_path = "xgboost_model.json"

if not os.path.exists(model_path):
    raise FileNotFoundError(f"❌ Modèle introuvable : {model_path}. Entraînez-le d'abord avec `train_xgboost.py`.")

# 🔹 Charger le modèle XGBoost
model = xgb.Booster()
model.load_model(model_path)

# 🔹 Charger les anciens tirages pour éviter de répéter les mêmes combinaisons
df = pd.read_csv("loto_cleaned.csv")
historique = df[["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]].values

app = Flask(__name__, static_url_path='/static', template_folder='templates')

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/create_checkout_session', methods=['POST'])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Grille Optimisée Loto'
                    },
                    'unit_amount': 100,  # 1€ en centimes
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="http://127.0.0.1:5000/success",
            cancel_url="http://127.0.0.1:5000/cancel",
        )
        return jsonify({"url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cancel')
def payment_cancel():
    return "❌ Paiement annulé. Reviens quand tu veux !"

@app.route('/success')
def payment_success():
    return render_template("success.html", grille=generate_grille().json)

@app.route('/mentions-legales')
def mentions_legales():
    return render_template("mentions_legales.html")

@app.route('/cgv')
def cgv():
    return render_template("cgv.html")

@app.route('/confidentialite')
def confidentialite():
    return render_template("confidentialite.html")

@app.route('/generate_grille', methods=['GET'])
def generate_grille():
    # ✅ Générer une entrée aléatoire pour la prédiction
    input_data = np.random.choice(range(1, 50), 5, replace=False).reshape(1, -1)

    # ✅ Prédire les probabilités des numéros
    dmatrix = xgb.DMatrix(input_data)
    predictions = model.predict(dmatrix)

    # ✅ Convertir les prédictions en 5 numéros distincts
    y_pred_unique = np.unique(np.round(predictions).astype(int))

    # ✅ Si moins de 5 numéros, compléter aléatoirement
    while len(y_pred_unique) < 5:
        new_num = np.random.randint(1, 50)
        if new_num not in y_pred_unique:
            y_pred_unique = np.append(y_pred_unique, new_num)

    # ✅ Trier les numéros pour une meilleure lisibilité
    grille_finale = sorted([int(num) for num in y_pred_unique])  # Convertir en int Python

    # ✅ Générer un numéro chance aléatoire entre 1 et 10
    numero_chance = int(np.random.randint(1, 11))  # Convertir en int Python

    return jsonify({
        "grille": grille_finale,
        "numero_chance": numero_chance
    })

if __name__ == '__main__':
    app.run(debug=True)