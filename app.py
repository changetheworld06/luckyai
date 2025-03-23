from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_session import Session  # 📌 Importer Flask-Session
import xgboost as xgb
import numpy as np
import pandas as pd
import os
import sqlite3
import json

# ✅ Déclarer l'application Flask
app = Flask(__name__, static_url_path='/static', template_folder='templates')

# 📌 Configuration de Flask-Session
app.config["SECRET_KEY"] = "super_secret_key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "./flask_session"
Session(app)

# ✅ Route pour servir ads.txt
@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(os.getcwd(), 'ads.txt')

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grilles.db")

# 🔹 Fonction pour stocker une grille en base de données
def save_grille_to_db(jeu, grille):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS grilles (id INTEGER PRIMARY KEY AUTOINCREMENT, jeu TEXT, grille TEXT)")
    c.execute("INSERT INTO grilles (jeu, grille) VALUES (?, ?)", (jeu, str(grille)))
    conn.commit()
    conn.close()

# ✅ Route d'accueil
@app.route('/')
def home():
    return render_template("index.html")

# ✅ Nouvelle route pour obtenir une grille gratuite directement
@app.route('/get_grille', methods=['GET'])
def get_grille():
    jeu = request.args.get('jeu', 'loto')

    if jeu == "loto":
        grille_data = generate_grille().get_json()
    elif jeu == "euromillions":
        grille_data = generate_grille_euromillions().get_json()
    else:
        return jsonify({"error": "Jeu inconnu"}), 400

    save_grille_to_db(jeu, grille_data)  # 🔥 Enregistrer dans la base de données
    return jsonify(grille_data)

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

@app.route('/blog/ia-et-loto')
def ia_et_loto():
    return render_template("articles/ia_loto.html")

@app.route('/blog/strategie-gains-loterie')
def strategie_gains_loterie():
    return render_template("articles/strategie-gains-loterie.html")

@app.route('/blog/psychologie-et-argent')
def psychologie_et_argent():
    return render_template("articles/psychologie-et-argent.html")

@app.route('/blog/ia-et-probabilites')
def ia_et_probabilites():
    return render_template("articles/ia-et-probabilites.html")

@app.route('/blog/optimiser-chances-loto')
def optimiser_chances_loto():
    return render_template("articles/optimiser-chances-loto.html")

@app.route('/blog/<slug>')
def article(slug):
    return render_template(f"articles/{slug}.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/blog')
def blog():
    return render_template("blog.html")

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

@app.route("/blog/entrainer-la-chance")
def entrainer_la_chance():
    return render_template("articles/entrainer-la-chance.html")

# ✅ Lancer l'application Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)