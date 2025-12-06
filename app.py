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

# 🔁 Charge le .env
load_dotenv()

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
print("DEBUG Stripe secret loaded:", stripe.api_key[:10])

app = FastAPI(
    title="LuckyAI API",
    description="API de génération de grilles optimisées Loto / Euromillions",
    version="0.1.0",
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


@app.get("/")
async def serve_frontend():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.is_file():
        # aide au debug si jamais le chemin est faux
        return {"error": "index.html introuvable", "path": str(index_path)}
    return FileResponse(str(index_path))


@app.get("/ads.txt", include_in_schema=False)
def ads_txt():
    return FileResponse("ads.txt", media_type="text/plain; charset=utf-8")

@app.get("/sitemap.xml", response_class=Response)
def sitemap():
    # À adapter si tu ajoutes d'autres pages
    base_url = "https://www.luckyai.fr"
    lastmod = datetime.utcnow().date().isoformat()

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=xml, media_type="application/xml")

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