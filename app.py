from flask import Flask, jsonify, render_template, request, session
from flask_session import Session  # 📌 Importer Flask-Session
import xgboost as xgb
import numpy as np
import pandas as pd
import stripe
from dotenv import load_dotenv
import os
import sqlite3
import json
import socket
from flask import send_from_directory
from flask import Flask, send_from_directory

# 🔹 Charger les variables d'environnement
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
print("🔑 Clé Stripe chargée ?", os.getenv("STRIPE_SECRET_KEY") is not None)

# ✅ Déclarer l'application Flask
app = Flask(__name__, static_url_path='/static', template_folder='templates')

# 📌 Configuration de Flask-Session
app.config["SECRET_KEY"] = "super_secret_key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "./flask_session"
Session(app)

# 🔹 Définir le chemin du modèle XGBoost
model_path = "xgboost_model.json"
if not os.path.exists(model_path):
    raise FileNotFoundError(f"❌ Modèle introuvable : {model_path}. Entraînez-le d'abord avec `train_xgboost.py`.")

# 🔹 Charger le modèle XGBoost
model = xgb.Booster()
model.load_model(model_path)

# 🔹 Charger les anciens tirages
df = pd.read_csv("loto_cleaned.csv")
historique = df[["boule_1", "boule_2", "boule_3", "boule_4", "boule_5"]].values

# 🔹 Définir un chemin absolu pour SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 📌 Chemin absolu du script
DB_PATH = os.path.join(BASE_DIR, "grilles.db")  # 📌 Chemin absolu pour SQLite

# 🔹 Fonction pour stocker une grille en base de données
def save_grille_to_db(jeu, grille):
    conn = sqlite3.connect(DB_PATH)  # 📌 Utilisation du chemin absolu
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS grilles (id INTEGER PRIMARY KEY AUTOINCREMENT, jeu TEXT, grille TEXT)")
    c.execute("INSERT INTO grilles (jeu, grille) VALUES (?, ?)", (jeu, str(grille)))
    conn.commit()
    conn.close()

# 🔹 Fonction pour récupérer la dernière grille enregistrée
def get_last_grille_from_db(jeu):
    conn = sqlite3.connect(DB_PATH)  # 📌 Utilisation du chemin absolu
    c = conn.cursor()
    print("🗄️ Accès à la base SQLite locale")  # 🔥 DEBUG
    c.execute("SELECT grille FROM grilles WHERE jeu = ? ORDER BY id DESC LIMIT 1", (jeu,))
    row = c.fetchone()
    conn.close()
    
    if row:
        print(f"📊 Données récupérées depuis SQLite : {row[0]}")  # 🔥 DEBUG
        try:
            grille_data = json.loads(row[0].replace("'", '"'))  # 🔥 Conversion sécurisée en JSON
            print(f"✅ Grille après conversion : {grille_data}")  # 🔥 DEBUG
            return grille_data
        except json.JSONDecodeError:
            print("❌ Erreur JSON : Impossible de convertir les données.")
            return None
    return None

@app.route('/robots.txt')
def serve_robots():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'robots.txt')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/success')
def success():
    print(f"📂 Chemin actuel : {os.getcwd()}")
    print(f"📂 Fichier SQLite trouvé ? {os.path.exists(DB_PATH)}")  

    jeu = request.args.get('jeu')
    print(f"✅ Jeu reçu : {jeu}")  

    # Vérifier la base de données
    conn = sqlite3.connect(DB_PATH)  
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM grilles WHERE jeu = ?", (jeu,))
    count = c.fetchone()[0]
    conn.close()
    print(f"📂 Nombre de grilles en base après paiement ({jeu}) : {count}")  

    # 🔥 TEST 1 : Récupération depuis la base
    grille_data = get_last_grille_from_db(jeu)  # ✅ Récupération depuis SQLite
    print(f"🔍 TEST 1 - Grille récupérée après paiement depuis SQLite : {grille_data}")   

    # Vérification finale : Affichage sur la page
    if not grille_data:
        print("❌ Erreur : Aucune grille trouvée en base après paiement.")
        return "Erreur : Aucune grille trouvée.", 400

    print(f"🎟️ Grille trouvée après paiement : {grille_data}")  
    return render_template("success.html", grille=grille_data, jeu=jeu)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/create_checkout_session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    if not data or 'jeu' not in data:
        return jsonify({"error": "Paramètre 'jeu' manquant"}), 400

    jeu = data['jeu']

    prix_mapping = {
        "loto": {"price": 100, "name": "Grille Loto"},
        "euromillions": {"price": 150, "name": "Grille EuroMillions"}
    }

    if jeu not in prix_mapping:
        return jsonify({"error": "Jeu inconnu"}), 400

    # 📌 Détecter l'environnement (local ou production)
    host = request.host  # 🔥 Récupération DANS la requête, pas en global
    if "127.0.0.1" in host or "localhost" in host:
        base_url = f"http://{host}"  # 🔥 En local
    else:
        base_url = "https://www.luckyai.fr"  # 🔥 En ligne

    success_url = f"{base_url}/success?jeu={jeu}"

    # 📌 Générer et stocker la grille avant redirection
    if jeu == "loto":
        grille_data = generate_grille().get_json()
    elif jeu == "euromillions":
        grille_data = generate_grille_euromillions().get_json()

    save_grille_to_db(jeu, grille_data)  # 🔥 Enregistrer dans la base de données
    print(f"📌 Grille sauvegardée en base : {grille_data}")

    price = prix_mapping[jeu]["price"]
    name = prix_mapping[jeu]["name"]

    print(f"✅ Grille stockée avant paiement : {grille_data}")
    session["grille"] = grille_data  # 🔥 Vérifier si cette ligne stocke bien la grille
    print(f"🔒 Session enregistrée avant paiement : {session.get('grille')}")

    try:
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {"name": name},
                    'unit_amount': price,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,  # ✅ URL dynamique
            cancel_url=f"{base_url}/cancel",
        )
        return jsonify({"url": session_stripe.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cancel')
def payment_cancel():
    return "❌ Paiement annulé. Reviens quand tu veux !"

# ✅ Routes légales et confidentialité
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
    input_data = np.random.choice(range(1, 50), 5, replace=False).reshape(1, -1)
    dmatrix = xgb.DMatrix(input_data)
    predictions = model.predict(dmatrix)

    y_pred_unique = np.unique(np.round(predictions).astype(int))

    while len(y_pred_unique) < 5:
        new_num = np.random.randint(1, 50)
        if new_num not in y_pred_unique:
            y_pred_unique = np.append(y_pred_unique, new_num)

    grille_finale = sorted([int(num) for num in y_pred_unique])
    numero_chance = int(np.random.randint(1, 11))

    return jsonify({
        "grille": grille_finale,
        "numero_chance": numero_chance
    })

@app.route('/generate_grille_euromillions', methods=['GET'])
def generate_grille_euromillions():
    numeros = sorted([int(num) for num in np.random.choice(range(1, 51), 5, replace=False)])
    etoiles = sorted([int(num) for num in np.random.choice(range(1, 13), 2, replace=False)])

    return jsonify({
        "numeros": numeros,
        "etoiles": etoiles
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)