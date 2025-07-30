from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/u")
def user_events():
    username = request.args.get("username")
    if not username:
        return render_template("index.html")

    url = f"https://api.github.com/users/{username}/events/public"
    resp = requests.get(url)
    if resp.status_code != 200:
        return render_template("user.html", username=username, events=[])
    return render_template("user.html", username=username, events=resp.json())

# API endpoint önceki haliyle kalabilir
@app.route("/api/u/<username>/events")
def get_events(username):
    url = f"https://api.github.com/users/{username}/events/public"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({"error": "User not found or API error"}), resp.status_code
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
