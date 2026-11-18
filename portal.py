# portal.py
import json
import os
import time
from html import escape
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, abort

from box_client import get_box_client
from hubs import list_hub_items

load_dotenv()

EMBED_DOMAIN = os.getenv("BOX_EMBED_DOMAIN") or "app.box.com"
CHAT_BUTTON_SCRIPT = os.getenv("BOX_CHAT_BUTTON_SCRIPT")
SOURCES_CACHE_SECONDS = 300
PORTAL = json.loads(Path("portal-config.json").read_text())
TEMPLATES = Path("templates")

app = Flask(__name__)
client = get_box_client()
sources_cache: dict[str, tuple[float, list[dict]]] = {}

def render(template: str, **values: str) -> str:
    page = (TEMPLATES / template).read_text()
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", value)
    return page

def hub_sources(hub_id: str) -> list[dict]:
    cached = sources_cache.get(hub_id)
    if cached and time.monotonic() - cached[0] < SOURCES_CACHE_SECONDS:
        return cached[1]
    sources = []
    for item in list_hub_items(client, hub_id):
        item_type = item.type.value
        url = f"https://{EMBED_DOMAIN}/{item_type}/{item.id}" if item_type in ("file", "folder") else None
        sources.append({"name": item.name, "url": url})
    sources_cache[hub_id] = (time.monotonic(), sources)
    return sources

@app.get("/")
def home():
    cards = "\n".join(
        f'<li><a href="/services/{escape(service["slug"])}">{escape(service["title"])}</a>'
        f'<p>{escape(service["description"])}</p></li>'
        for service in PORTAL["services"]
    )
    return render(
        "home.html",
        SERVICE_CARDS=cards,
        CHAT_BUTTON_SCRIPT=escape(CHAT_BUTTON_SCRIPT),
        CAMPUS_HUB_ID=escape(PORTAL["campusHubId"]),
        EMBED_DOMAIN=escape(EMBED_DOMAIN),
    )

@app.get("/services/<slug>")
def service(slug: str):
    service = next((s for s in PORTAL["services"] if s["slug"] == slug), None)
    if service is None:
        abort(404)
    sources = "\n".join(
        f'<li><a href="{escape(source["url"])}" target="_blank" rel="noopener">{escape(source["name"])}</a></li>'
        if source["url"]
        else f"<li>{escape(source['name'])}</li>"
        for source in hub_sources(service["hubId"])
    )
    chat_url = f"https://{EMBED_DOMAIN}/ai-chat?hubId={service['hubId']}&showCloseButton=true"
    return render(
        "service.html",
        TITLE=escape(service["title"]),
        DESCRIPTION=escape(service["description"]),
        SOURCES=sources,
        CHAT_URL=escape(chat_url),
    )

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "3000")), debug=True)
