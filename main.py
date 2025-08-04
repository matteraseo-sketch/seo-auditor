from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_PAGESPEED_API_KEY = "AIzaSyC95tS1OPYz0i4kBgMBxDNlmFqejH7vdMY"

class URLRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/audit")
def audit_seo(data: URLRequest):
    url = data.url if data.url.startswith("http") else "http://" + data.url
    results = {
        "url": url,
        "https": url.startswith("https"),
        "meta_title": None,
        "meta_description": None,
        "headings": {},
        "alt_issues": 0,
        "canonical": None,
        "robots": False,
        "sitemap": False,
        "pagespeed_score": None
    }

    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        title = soup.find("title")
        desc = soup.find("meta", {"name": "description"})
        canonical = soup.find("link", {"rel": "canonical"})

        results["meta_title"] = title.text.strip() if title else None
        results["meta_description"] = desc["content"] if desc and "content" in desc.attrs else None
        results["canonical"] = canonical["href"] if canonical and "href" in canonical.attrs else None

        for tag in ["h1", "h2", "h3"]:
            results["headings"][tag] = len(soup.find_all(tag))

        images = soup.find_all("img")
        results["alt_issues"] = sum(1 for img in images if not img.get("alt"))

        robots_url = urljoin(url, "/robots.txt")
        results["robots"] = requests.get(robots_url).status_code == 200

        sitemap_url = urljoin(url, "/sitemap.xml")
        results["sitemap"] = requests.get(sitemap_url).status_code == 200

        if GOOGLE_PAGESPEED_API_KEY:
            psi_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={GOOGLE_PAGESPEED_API_KEY}"
            psi_data = requests.get(psi_url).json()
            results["pagespeed_score"] = psi_data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) * 100

    except Exception as e:
        results["error"] = str(e)

    return results