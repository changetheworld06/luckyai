from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_session import Session
import numpy as np
import os
import sqlite3
from analyzer import LotoAnalyzer, EuroMillionsAnalyzer

app = Flask(__name__, static_url_path='/static', template_folder='templates')

app.config["SECRET_KEY"] = "super_secret_key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "./flask_session"
Session(app)

# Analyseurs
loto_analyzer = LotoAnalyzer("loto_cleaned.csv")
euro_analyzer = EuroMillionsAnalyzer("euromillions_cleaned.csv")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grilles.db")

# Liste des articles du blog
ARTICLES = [
    {"slug": "ia-et-loto", "template": "articles/ia_loto.html",
     "title": "L'IA peut-elle ameliorer vos chances au Loto ?",
     "desc": "Decouvrez comment l'intelligence artificielle analyse les tirages pour optimiser vos grilles.",
     "date": "2025-01-15", "category": "IA & Loto"},
    {"slug": "ia-et-probabilites", "template": "articles/ia-et-probabilites.html",
     "title": "IA et probabilites : peut-on predire le hasard ?",
     "desc": "Exploration des limites de l'IA face au hasard et aux probabilites.",
     "date": "2025-02-10", "category": "Science"},
    {"slug": "optimiser-chances-loto", "template": "articles/optimiser-chances-loto.html",
     "title": "Comment maximiser ses chances au Loto et EuroMillions",
     "desc": "Strategies concretes pour jouer plus intelligemment sans depenser plus.",
     "date": "2025-03-05", "category": "Strategie"},
    {"slug": "entrainer-la-chance", "template": "articles/entrainer-la-chance.html",
     "title": "Peut-on s'entrainer a avoir de la chance ?",
     "desc": "Ce que la psychologie et les neurosciences nous apprennent sur la chance.",
     "date": "2025-03-20", "category": "Psychologie"},
    {"slug": "strategie-gains-loterie", "template": "articles/strategie-gains-loterie.html",
     "title": "Que faire si vous gagnez a la loterie ?",
     "desc": "Guide complet pour gerer un gain important et eviter les pieges.",
     "date": "2025-04-01", "category": "Finance"},
    {"slug": "psychologie-et-argent", "template": "articles/psychologie-et-argent.html",
     "title": "Psychologie de l'argent : emotions et decisions financieres",
     "desc": "Comment nos biais cognitifs influencent notre rapport a l'argent.",
     "date": "2025-04-15", "category": "Psychologie"},
    {"slug": "numeros-les-plus-tires", "template": "articles/numeros-les-plus-tires.html",
     "title": "Les numeros les plus tires au Loto : mythe ou realite ?",
     "desc": "Analyse statistique des numeros qui sortent le plus souvent et ce que cela signifie vraiment.",
     "date": "2025-05-01", "category": "Statistiques"},
    {"slug": "erreurs-joueurs-loto", "template": "articles/erreurs-joueurs-loto.html",
     "title": "Les 10 erreurs les plus courantes des joueurs de Loto",
     "desc": "Evitez ces pieges classiques qui reduisent vos gains potentiels.",
     "date": "2025-05-15", "category": "Strategie"},
    {"slug": "loto-vs-euromillions", "template": "articles/loto-vs-euromillions.html",
     "title": "Loto vs EuroMillions : lequel choisir ?",
     "desc": "Comparaison detaillee des probabilites, gains et strategies pour chaque jeu.",
     "date": "2025-06-01", "category": "Strategie"},
    {"slug": "mathematiques-du-hasard", "template": "articles/mathematiques-du-hasard.html",
     "title": "Les mathematiques du hasard expliquees simplement",
     "desc": "Combinaisons, probabilites et loi des grands nombres : tout comprendre.",
     "date": "2025-06-15", "category": "Science"},
    {"slug": "histoire-du-loto", "template": "articles/histoire-du-loto.html",
     "title": "L'histoire du Loto en France depuis 1976",
     "desc": "Retour sur 50 ans de Loto : regles, evolutions et records.",
     "date": "2025-07-01", "category": "Culture"},
    {"slug": "astuces-jeu-groupe", "template": "articles/astuces-jeu-groupe.html",
     "title": "Jouer en groupe : astuces pour maximiser ses chances",
     "desc": "Tout savoir sur le jeu en syndic : organisation, partage et strategies.",
     "date": "2025-07-15", "category": "Strategie"},
    {"slug": "gagnants-celebres", "template": "articles/gagnants-celebres.html",
     "title": "Ces gagnants celebres du Loto et ce qu'ils sont devenus",
     "desc": "Histoires fascinantes de gagnants et lecons a en tirer.",
     "date": "2025-08-01", "category": "Culture"},
    {"slug": "biais-cognitifs-jeu", "template": "articles/biais-cognitifs-jeu.html",
     "title": "Les biais cognitifs qui influencent vos choix de numeros",
     "desc": "Pourquoi votre cerveau vous pousse a mal choisir et comment y remedier.",
     "date": "2025-08-15", "category": "Psychologie"},
]


def save_grille_to_db(jeu, grille):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS grilles (id INTEGER PRIMARY KEY AUTOINCREMENT, jeu TEXT, grille TEXT)")
    c.execute("INSERT INTO grilles (jeu, grille) VALUES (?, ?)", (jeu, str(grille)))
    conn.commit()
    conn.close()


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(os.getcwd(), 'ads.txt')

@app.after_request
def add_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# --- Pages principales ---

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/mentions-legales')
def mentions_legales():
    return render_template("mentions_legales.html")

@app.route('/cgv')
def cgv():
    return render_template("cgv.html")

@app.route('/confidentialite')
def confidentialite():
    return render_template("confidentialite.html")


# --- Blog ---

@app.route('/blog')
def blog():
    return render_template("blog.html", articles=ARTICLES)

@app.route('/blog/<slug>')
def article(slug):
    art = next((a for a in ARTICLES if a["slug"] == slug), None)
    if art:
        return render_template(art["template"], article=art)
    return render_template(f"articles/{slug}.html")


# --- API Loto ---

@app.route('/api/analysis')
def api_analysis():
    return jsonify(loto_analyzer.full_analysis())

@app.route('/api/history')
def api_history():
    n = request.args.get('n', 20, type=int)
    return jsonify(loto_analyzer.last_draws(n))

@app.route('/api/generate')
def api_generate():
    strategy = request.args.get('strategy', 'composite')
    jeu = request.args.get('jeu', 'loto')
    if jeu == "euromillions":
        data = euro_analyzer.generate_grid(strategy)
    else:
        data = loto_analyzer.generate_grid(strategy)
    save_grille_to_db(jeu, data)
    return jsonify(data)


# --- API EuroMillions ---

@app.route('/api/euro/analysis')
def api_euro_analysis():
    return jsonify(euro_analyzer.full_analysis())


# --- Backward compat ---

@app.route('/get_grille', methods=['GET'])
def get_grille():
    jeu = request.args.get('jeu', 'loto')
    if jeu == "euromillions":
        data = euro_analyzer.generate_grid("composite")
    else:
        data = loto_analyzer.generate_grid("composite")
    save_grille_to_db(jeu, data)
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
