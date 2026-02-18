import sys
import os
import chess
import time
from flask import Flask, request, jsonify, render_template

# Ensure MCTS modules are discoverable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcts.evaluator import MaterialEvaluator
from mcts.search import MCTS

app = Flask(__name__)

evaluator = MaterialEvaluator() 
engine = MCTS(evaluator)

STATE = {
    "moves_uci": [],
    "move_times": [],
    "history_evals": [0.5], # Start at 50%
    "history_depths": [0],   # Track depth for every move
    "view": 0,
    "last_ts": None,
    "last_stats": {
        "win_prob": 50.0,
        "simulations": 0,
        "depth": 0,
        "top_lines": []
    } 
}

def rebuild_board():
    b = chess.Board()
    for u in STATE["moves_uci"][:STATE["view"]]:
        b.push_uci(u)
    return b

def san_list():
    b = chess.Board()
    out = []
    for u in STATE["moves_uci"]:
        try:
            mv = chess.Move.from_uci(u)
            out.append(b.san(mv))
            b.push(mv)
        except: continue
    return out

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/state")
def get_state():
    b = rebuild_board()
    u = STATE["moves_uci"][STATE["view"]-1] if STATE["view"] > 0 else None
    return jsonify({
        "fen": b.fen(),
        "turn": "w" if b.turn else "b",
        "moves_san": san_list(),
        "move_times": STATE["move_times"],
        "history_evals": STATE["history_evals"],
        "history_depths": STATE["history_depths"],
        "last_move": {"from": u[:2], "to": u[2:4]} if u else None,
        "view": STATE["view"],
        "engine_stats": STATE["last_stats"]
    })

@app.post("/move")
def make_move():
    data = request.get_json(force=True)
    return process_move(data.get("uci", ""))

@app.post("/engine_move")
def engine_move():
    b = rebuild_board()
    if b.is_game_over():
        return jsonify({"ok": False}), 400

    best_move, stats = engine.search(b)
    STATE["last_stats"] = stats
    return process_move(best_move.uci(), engine_eval=stats["win_prob"] / 100.0, engine_depth=stats["depth"])

def process_move(uci, engine_eval=None, engine_depth=None):
    b = rebuild_board()
    try:
        mv = chess.Move.from_uci(uci)
    except: return jsonify({"ok": False}), 400
        
    if mv not in b.legal_moves:
        return jsonify({"ok": False}), 400

    now = time.time()
    dt = max(0.1, now - STATE["last_ts"]) if STATE["last_ts"] else 0.5
    STATE["last_ts"] = now

    # Handle branching
    if STATE["view"] < len(STATE["moves_uci"]):
        STATE["moves_uci"] = STATE["moves_uci"][:STATE["view"]]
        STATE["move_times"] = STATE["move_times"][:STATE["view"]]
        STATE["history_evals"] = STATE["history_evals"][:STATE["view"] + 1]
        STATE["history_depths"] = STATE["history_depths"][:STATE["view"] + 1]

    b.push(mv)
    STATE["moves_uci"].append(uci)
    STATE["move_times"].append(dt)
    
    # Store Eval & Depth
    val = engine_eval if engine_eval is not None else (STATE["last_stats"]["win_prob"] / 100.0)
    dep = engine_depth if engine_depth is not None else STATE["last_stats"]["depth"]
    
    STATE["history_evals"].append(val)
    STATE["history_depths"].append(dep)
    STATE["view"] = len(STATE["moves_uci"])
    
    return jsonify({
        "ok": True, "fen": b.fen(), "moves_san": san_list(), 
        "move_times": STATE["move_times"], "history_evals": STATE["history_evals"],
        "history_depths": STATE["history_depths"],
        "last_move": {"from": uci[:2], "to": uci[2:4]}, "view": STATE["view"],
        "engine_stats": STATE["last_stats"]
    })

@app.post("/goto")
def goto():
    data = request.get_json(force=True)
    view = max(0, min(int(data.get("view", 0)), len(STATE["moves_uci"])))
    STATE["view"] = view
    b = rebuild_board()
    u = STATE["moves_uci"][view-1] if view > 0 else None
    return jsonify({
        "ok": True, "fen": b.fen(), "view": STATE["view"], 
        "moves_san": san_list(), "move_times": STATE["move_times"],
        "history_evals": STATE["history_evals"],
        "history_depths": STATE["history_depths"],
        "last_move": {"from": u[:2], "to": u[2:4]} if u else None,
        "engine_stats": STATE["last_stats"]
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)