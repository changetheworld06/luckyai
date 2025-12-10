# app.py
import os
import stripe
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import Response, FileResponse
from datetime import datetime
from api.loto import router as loto_router
from api.euromillions import router as euromillions_router
from api.paywall import router as paywall_router
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
print("DEBUG Stripe secret loaded:", stripe.api_key[:10])

app = FastAPI(
    title="LuckyAI API",
    description="API de génération de grilles optimisées Loto / Euromillions",
    version="0.1.0",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Servir les fichiers statiques
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

app.mount(
    "/pages",
    StaticFiles(directory=os.path.join(BASE_DIR, "pages")),
    name="pages",
)

origins = [
    "http://localhost:5500",
    "http://localhost:8000",
    "https://luckyai.fr",
    "https://www.luckyai.fr",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Juste après `app = FastAPI()` et la config Stripe / CORS par exemple
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"


# Servir le blog
@app.get("/blog/")
def blog_index():
    return FileResponse("blog/index.html")

@app.get("/blog/{filename}")
def blog_pages(filename: str):
    # Ex: cycles-loto.html
    path = f"blog/{filename}"
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": "Not Found"}

@app.get("/")
async def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.is_file():
        # aide au debug si jamais le chemin est faux
        return {"error": "index.html introuvable", "path": str(index_path)}
    return FileResponse(str(index_path))

@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    sitemap_path = os.path.join(BASE_DIR, "sitemap.xml")
    return FileResponse(sitemap_path, media_type="application/xml")

@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    robots_path = os.path.join(BASE_DIR, "robots.txt")
    return FileResponse(robots_path, media_type="text/plain")

@app.get("/ads.txt", include_in_schema=False)
def ads_txt():
    return FileResponse("ads.txt", media_type="text/plain; charset=utf-8")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(loto_router, prefix="/api/loto", tags=["loto"])
app.include_router(euromillions_router, prefix="/api/euromillions", tags=["euromillions"])
app.include_router(paywall_router, prefix="/api", tags=["paywall"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)