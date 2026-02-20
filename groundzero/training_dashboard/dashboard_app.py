import os
import glob
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# This will be populated by run_actors.py
shared_state = {}
BUFFER_PATH = "data/replay_buffer/"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    """Returns the current buffer size and the status of all active workers."""
    files = glob.glob(os.path.join(BUFFER_PATH, "*.npz"))
    
    # Convert the Manager Dict to a standard dict for JSON serialization
    workers_data = {str(k): v for k, v in shared_state.items()}
    
    return jsonify({
        "buffer_count": len(files),
        "workers": workers_data
    })

def run_dashboard_server(stats_dict):
    """Entry point used by run_actors.py"""
    global shared_state
    shared_state = stats_dict
    print("[*] Dashboard UI: http://localhost:5003")
    app.run(host="0.0.0.0", port=5003, debug=False, use_reloader=False)

if __name__ == "__main__":
    # For standalone testing
    app.run(port=5003, debug=True)