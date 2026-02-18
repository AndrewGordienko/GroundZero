from flask import Flask, request, jsonify, render_template
import chess
import time

app = Flask(__name__)

STATE = {
    "moves_uci": [],
    "move_times": [],
    "view": 0,
    "last_ts": None
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
        mv = chess.Move.from_uci(u)
        out.append(b.san(mv))
        b.push(mv)
    return out

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/state")
def get_state():
    b = rebuild_board()
    last_move = None
    if STATE["moves_uci"]:
        u = STATE["moves_uci"][-1]
        last_move = {"from": u[:2], "to": u[2:4]}
    return jsonify({
        "fen": b.fen(),
        "turn": "w" if b.turn else "b",
        "moves_san": san_list(),
        "move_times": STATE["move_times"],
        "last_move": last_move,
        "view": STATE["view"],
    })

@app.post("/goto")
def goto():
    data = request.get_json(force=True)
    view = max(0, min(int(data.get("view", 0)), len(STATE["moves_uci"])))
    STATE["view"] = view
    b = rebuild_board()
    last_move = None
    if view > 0:
        u = STATE["moves_uci"][view-1]
        last_move = {"from": u[:2], "to": u[2:4]}
    return jsonify({"ok": True, "fen": b.fen(), "view": STATE["view"], "moves_san": san_list(), "move_times": STATE["move_times"], "last_move": last_move})

@app.post("/move")
def make_move():
    data = request.get_json(force=True)
    uci = data.get("uci", "")
    b = rebuild_board()
    try:
        mv = chess.Move.from_uci(uci)
    except:
        return jsonify({"ok": False}), 400
    if mv not in b.legal_moves:
        return jsonify({"ok": False}), 400

    now = time.time()
    dt = max(0.1, now - STATE["last_ts"]) if STATE["last_ts"] else 0.5
    STATE["last_ts"] = now

    if STATE["view"] < len(STATE["moves_uci"]):
        STATE["moves_uci"] = STATE["moves_uci"][:STATE["view"]]
        STATE["move_times"] = STATE["move_times"][:STATE["view"]]

    b.push(mv)
    STATE["moves_uci"].append(uci)
    STATE["move_times"].append(dt)
    STATE["view"] = len(STATE["moves_uci"])
    
    return jsonify({"ok": True, "fen": b.fen(), "moves_san": san_list(), "move_times": STATE["move_times"], "last_move": {"from": uci[:2], "to": uci[2:4]}, "view": STATE["view"]})

if __name__ == "__main__":
    app.run(debug=True, port=5000)