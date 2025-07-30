import os
import time
import io
from collections import Counter
import requests
from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE = "https://api.github.com"

# Basit bellek içi cache (TTL + ETag)
CACHE_TTL_SECONDS = 180  # 3 dakika
event_cache = {}  # key: ("events", username) -> {"ts": epoch, "data": [...], "etag": "xyz"}

def gh_headers(etag=None):
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    if etag:
        h["If-None-Match"] = etag
    return h

def fetch_user_events(username, per_page=100, pages=1):
    """
    Kullanıcının public etkinliklerini getirir.
    - TTL cache: 3 dk boyunca bellekte tutar
    - ETag: Değişmediyse 304 ile önceki veriyi kullanır
    """
    key = ("events", username.lower())
    now = time.time()
    cached = event_cache.get(key)

    # TTL kontrolü
    if cached and (now - cached["ts"] < CACHE_TTL_SECONDS):
        return cached["data"]

    url = f"{BASE}/users/{username}/events/public"
    all_events = []
    etag = cached.get("etag") if cached else None

    try:
        for page in range(1, pages + 1):
            params = {"per_page": per_page, "page": page}
            resp = requests.get(url, headers=gh_headers(etag if page == 1 else None), params=params, timeout=15)

            if resp.status_code == 304 and cached:
                # Veri değişmedi; önceki cache
                all_events = cached["data"]
                break

            resp.raise_for_status()

            # İlk sayfada ETag al
            if page == 1 and "ETag" in resp.headers:
                etag = resp.headers["ETag"]

            data = resp.json()
            if not data:
                break
            all_events.extend(data)

            if len(data) < per_page:
                break

        # Cache’i güncelle
        event_cache[key] = {"ts": now, "data": all_events, "etag": etag}
        return all_events

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            abort(404, description="Kullanıcı bulunamadı.")
        elif e.response is not None and e.response.status_code in (403, 429):
            abort(e.response.status_code, description="Rate limit aşıldı veya erişim engellendi.")
        raise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/u")
def user_events():
    username = request.args.get("username", "").strip()
    if not username:
        return render_template("index.html")

    events = fetch_user_events(username, per_page=100, pages=2)
    return render_template("user.html", username=username, events=events)

@app.route("/api/u/<username>/events")
def api_user_events(username):
    events = fetch_user_events(username, per_page=100, pages=2)
    want = request.args.get("type")
    if want:
        events = [e for e in events if e.get("type") == want]
    return jsonify(events)

# Basit healthcheck
@app.route("/healthz")
def health():
    return {"ok": True}

if __name__ == "__main__":
    # Lokal geliştirme
    app.run(debug=True, host="0.0.0.0", port=5001)
