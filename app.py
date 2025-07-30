import os
import time
import io
from collections import Counter
import requests
from flask import Flask, jsonify, render_template, request, abort, send_file

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE = "https://api.github.com"

# Simple in-memory cache (TTL + ETag)
CACHE_TTL_SECONDS = 180  # 3 minutes
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
    Fetch public events for a user.
    Uses TTL cache and ETag to reduce API calls.
    """
    key = ("events", username.lower())
    now = time.time()
    cached = event_cache.get(key)

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
                all_events = cached["data"]
                break

            resp.raise_for_status()

            if page == 1 and "ETag" in resp.headers:
                etag = resp.headers["ETag"]

            data = resp.json()
            if not data:
                break
            all_events.extend(data)

            if len(data) < per_page:
                break

        event_cache[key] = {"ts": now, "data": all_events, "etag": etag}
        return all_events

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            abort(404, description="User not found.")
        elif e.response is not None and e.response.status_code in (403, 429):
            abort(e.response.status_code, description="Rate limit exceeded or access denied.")
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

@app.route("/healthz")
def health():
    return {"ok": True}

@app.route("/charts/<username>/events-per-day.png")
def chart_events_per_day(username):
    """Return a PNG line chart of daily event counts for the given user."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        abort(500, description="matplotlib is not installed. Please install it with `pip install matplotlib`.")

    events = fetch_user_events(username, per_page=100, pages=2)

    per_day = Counter()
    for e in events:
        ts = e.get("created_at")
        if not ts:
            continue
        day = ts[:10]
        per_day[day] += 1

    buf = io.BytesIO()
    fig = plt.figure()
    if per_day:
        days = sorted(per_day.keys())
        counts = [per_day[d] for d in days]
        plt.plot(days, counts, marker="o")
        plt.xticks(rotation=45, ha="right")
        plt.title(f"{username} - Events Per Day")
        plt.xlabel("Day")
        plt.ylabel("Event count")
        plt.tight_layout()
    else:
        plt.title(f"{username} - Events Per Day (no data)")
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
