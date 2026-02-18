from flask import Flask, request, jsonify, render_template
import chess

app = Flask(__name__)

# Single-user simple state (fine for local dev).
# If you want multi-user later, move this into sessions or a DB.
STATE = {
    "moves_uci": [],
    "view": 0,  # number of moves applied from moves_uci
}

def rebuild_board():
    b = chess.Board()
    for u in STATE["moves_uci"][:STATE["view"]]:
        b.push_uci(u)
    return b

def san_list():
    # SAN list for entire moves_uci, independent of view
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
    return jsonify({
        "fen": b.fen(),
        "turn": "w" if b.turn else "b",
        "moves_san": san_list(),
        "view": STATE["view"],
        "len": len(STATE["moves_uci"]),
    })

@app.post("/goto")
def goto():
    data = request.get_json(force=True)
    view = int(data.get("view", 0))
    view = max(0, min(view, len(STATE["moves_uci"])))
    STATE["view"] = view
    b = rebuild_board()
    return jsonify({"ok": True, "fen": b.fen(), "view": STATE["view"]})

@app.post("/move")
def make_move():
    data = request.get_json(force=True)
    uci = data.get("uci", "")

    b = rebuild_board()

    try:
        mv = chess.Move.from_uci(uci)
    except ValueError:
        return jsonify({"ok": False, "error": "bad uci"}), 400

    if mv not in b.legal_moves:
        return jsonify({"ok": False, "error": "illegal"}), 400

    # If we're in the past, erase future and branch from here
    if STATE["view"] < len(STATE["moves_uci"]):
        STATE["moves_uci"] = STATE["moves_uci"][:STATE["view"]]

    b.push(mv)
    STATE["moves_uci"].append(uci)
    STATE["view"] = len(STATE["moves_uci"])

    return jsonify({
        "ok": True,
        "fen": b.fen(),
        "turn": "w" if b.turn else "b",
        "moves_san": san_list(),
        "view": STATE["view"],
        "len": len(STATE["moves_uci"]),
    })

if __name__ == "__main__":
    app.run(debug=True)
