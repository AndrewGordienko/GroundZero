import os
import glob
import logging
from flask import Flask, render_template, jsonify

# ==============================================================
# 1. GHOST MODE: Silence the Flask/Werkzeug API Logs
# ==============================================================
os.environ['WERKZEUG_RUN_MAIN'] = 'true'
log = logging.getLogger('werkzeug')
log.disabled = True 

app = Flask(__name__)
shared_state = {}

# Path setup relative to this file
current_file = os.path.abspath(__file__)
PACKAGE_ROOT = os.path.dirname(os.path.dirname(current_file))
BUFFER_PATH = os.path.join(PACKAGE_ROOT, "data", "replay_buffer")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    """Returns the current buffer size and the status of all active workers."""
    if not os.path.exists(BUFFER_PATH):
        return jsonify({"buffer_count": 0, "workers": {}})
        
    files = glob.glob(os.path.join(BUFFER_PATH, "*.npz"))
    workers_data = {str(k): v for k, v in shared_state.items()}
    
    return jsonify({
        "buffer_count": len(files),
        "workers": workers_data
    })

def run_dashboard_server(stats_dict):
    """Entry point used by run_actors.py"""
    global shared_state
    shared_state = stats_dict
    print(f"\n[*] Dashboard UI ready at: http://localhost:5003")
    app.run(host="0.0.0.0", port=5003, debug=False, use_reloader=False)

if __name__ == "__main__":
    app.run(port=5003)