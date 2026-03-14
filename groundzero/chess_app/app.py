import sys, os, chess, time, torch
from flask import Flask, request, jsonify, render_template

# --- ROBUST PATH SETUP ---
current_file_path = os.path.abspath(__file__)
chess_app_dir = os.path.dirname(current_file_path)         # groundzero/chess_app
inner_gz_dir = os.path.dirname(chess_app_dir)             # groundzero/groundzero
project_root = os.path.dirname(inner_gz_dir)              # groundzero (root)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# We need the inner directory for the package imports to resolve correctly
if inner_gz_dir not in sys.path:
    sys.path.insert(0, inner_gz_dir)

from groundzero.mcts.search import MCTS
from groundzero.alphazero.algorithm.evaluator import AlphaZeroEvaluator 

app = Flask(__name__)

# --- ENGINE INITIALIZATION ---
device = "mps" if torch.backends.mps.is_available() else "cpu"

# ALIGNMENT FIX: Pointing to the specific models folder inside the package
MODEL_PATH = os.path.join(inner_gz_dir, "models", "best_model.pth")

print(f"\n" + "="*50)
print(f"  CHESS INTERFACE STARTUP")
print(f"="*50)
print(f"[*] Target Model: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    print(f"[!] WARNING: {MODEL_PATH} not found.")
    print(f"    Ensure you have run the trainer.py at least once!")
else:
    print(f"[*] Model detected. Initializing AlphaZero Evaluator on {device}...")

# Initialize Engine
evaluator = AlphaZeroEvaluator(model_path=MODEL_PATH, device=device) 
engine = MCTS(evaluator)
print(f"[*] Engine Ready to Play.\n")

# -------------------------------------
# REST OF YOUR FLASK LOGIC
# -------------------------------------

GLOBAL_BOARD = chess.Board()

STATE = {
    "move_times": [],
    "history_evals": [0.5], 
    "history_depths": [0],   
    "view": 0,
    "last_ts": None,
    "last_stats": {
        "win_prob": 50.0, "simulations": 0, "depth": 0, "top_lines": []
    } 
}

def get_san_list():
    temp_b = chess.Board()
    out = []
    for m in GLOBAL_BOARD.move_stack:
        out.append(temp_b.san(m))
        temp_b.push(m)
    return out

def get_common_state():
    u = GLOBAL_BOARD.move_stack[STATE["view"]-1] if STATE["view"] > 0 else None
    return {
        "fen": GLOBAL_BOARD.fen(),
        "turn": "w" if GLOBAL_BOARD.turn else "b",
        "moves_san": get_san_list(),
        "move_times": STATE["move_times"],
        "history_evals": STATE["history_evals"],
        "history_depths": STATE["history_depths"],
        "last_move": {"from": u.uci()[:2], "to": u.uci()[2:4]} if u else None,
        "view": STATE["view"],
        "engine_stats": STATE["last_stats"]
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/state")
def get_state():
    return jsonify(get_common_state())

@app.post("/move")
def make_move():
    data = request.get_json(force=True)
    return process_move(data.get("uci", ""))

@app.post("/engine_move")
def engine_move():
    if GLOBAL_BOARD.is_game_over():
        return jsonify({"ok": False}), 400
    
    # MCTS returns (best_move, pi_dist, root)
    best_move, pi_dist, root = engine.search(GLOBAL_BOARD)
    
    total_n = sum(root.N.values())
    chosen_q = root.Q.get(best_move, 0.0)
    win_prob = (chosen_q + 1) / 2 * 100 

    stats = {
        "win_prob": round(float(win_prob), 1),
        "simulations": int(total_n),
        "depth": int(engine.latest_depth),
        "top_lines": [] 
    }
    
    STATE["last_stats"] = stats
    return process_move(best_move.uci(), 
                        engine_eval=stats["win_prob"] / 100.0, 
                        engine_depth=stats["depth"])

def process_move(uci, engine_eval=None, engine_depth=None):
    try:
        mv = chess.Move.from_uci(uci)
    except: return jsonify({"ok": False}), 400
        
    if mv not in GLOBAL_BOARD.legal_moves:
        return jsonify({"ok": False}), 400

    now = time.time()
    dt = max(0.1, now - STATE["last_ts"]) if STATE["last_ts"] else 0.5
    STATE["last_ts"] = now

    if STATE["view"] < len(GLOBAL_BOARD.move_stack):
        while len(GLOBAL_BOARD.move_stack) > STATE["view"]:
            GLOBAL_BOARD.pop()
        STATE["move_times"] = STATE["move_times"][:STATE["view"]]
        STATE["history_evals"] = STATE["history_evals"][:STATE["view"] + 1]
        STATE["history_depths"] = STATE["history_depths"][:STATE["view"] + 1]

    GLOBAL_BOARD.push(mv)
    STATE["move_times"].append(dt)
    
    val = engine_eval if engine_eval is not None else (STATE["last_stats"]["win_prob"] / 100.0)
    dep = engine_depth if engine_depth is not None else STATE["last_stats"]["depth"]
    
    STATE["history_evals"].append(val)
    STATE["history_depths"].append(dep)
    STATE["view"] = len(GLOBAL_BOARD.move_stack)
    
    res = get_common_state()
    res["ok"] = True
    return jsonify(res)

@app.post("/goto")
def goto():
    data = request.get_json(force=True)
    target = max(0, min(int(data.get("view", 0)), len(GLOBAL_BOARD.move_stack)))
    
    STATE["view"] = target
    temp_board = chess.Board()
    for m in GLOBAL_BOARD.move_stack[:target]:
        temp_board.push(m)
    
    res = get_common_state()
    res["fen"] = temp_board.fen()
    res["ok"] = True
    return jsonify(res)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)