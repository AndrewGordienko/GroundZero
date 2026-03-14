import os
import time
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Persistent state for the training session
stats = {
    "iterations": [],
    "p_loss": [],
    "v_loss": [],
    "lr": [],
    "buffer_size": 0,
    "last_update": time.time()
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    stats["iterations"].append(len(stats["iterations"]))
    stats["p_loss"].append(data.get("p_loss"))
    stats["v_loss"].append(data.get("v_loss"))
    stats["lr"].append(data.get("lr"))
    stats["buffer_size"] = data.get("buffer_size")
    stats["last_update"] = time.time()
    return jsonify({"status": "ok"})

@app.route('/api/data')
def get_data():
    return jsonify(stats)

if __name__ == '__main__':
    # Use a different port than your actor dashboard (e.g., 5005)
    app.run(host='0.0.0.0', port=5005, debug=False)