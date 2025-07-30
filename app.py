from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, GitHub Activity Dashboard!"

@app.route("/api/u/<username>/events")
def get_events(username):
    url = f"https://api.github.com/users/{username}/events/public"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({"error": "User not found or API error"}), resp.status_code
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
