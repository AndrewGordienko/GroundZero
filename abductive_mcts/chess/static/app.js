// static/app.js

let boardUI = null;
let game = new Chess();

let selected = null;
let lastMove = null;

// current viewed ply (0 = start)
let view = null;

// ---------------- Inject UI CSS ----------------

(function () {
  const css = `
  #board .square-55d63 { position: relative; }

  /* selected square (neutral dark) */
  .sq-sel {
    background: rgba(0,0,0,.22) !important;
  }

  /* last move (subtle brown/orange like chess.com) */
  .sq-last {
    background: rgba(210,160,60,.55) !important;
  }

  /* legal move dots */
  .sq-dot {
    background-image:
      radial-gradient(circle at center,
        rgba(90,90,90,.6) 18%,
        transparent 20%);
  }

  /* responsive layout */
  .page {
    display: flex;
    width: 100vw;
    height: 100vh;
  }

  .board-wrap {
    width: 50%;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 24px;
  }

  #board {
    width: min(90%, 90vh);
  }

  .panel {
    width: 50%;
    padding: 24px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
  }

  .movesbox {
    flex: 1;
    border: 1px solid #ddd;
    border-radius: 6px;
    overflow-y: auto;
  }

  .moverow {
    display: grid;
    grid-template-columns: 40px 1fr 1fr;
    padding: 6px 8px;
    cursor: pointer;
  }

  .moverow:hover {
    background: #f2f2f2;
  }

  .moverow:nth-child(even) {
    background: #fafafa;
  }

  .move-num {
    color: #777;
  }

  .move.current {
    background: #e6e6e6;
  }

  .turnrow {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .turnbox {
    width: 20px;
    height: 20px;
    border: 1px solid #999;
  }
  `;
  const s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);
})();

// ---------------- Helpers ----------------

function squareEl(sq) {
  return document.querySelector(`#board .square-${sq}`);
}

function clearHighlights() {
  document.querySelectorAll(".sq-sel").forEach(e => e.classList.remove("sq-sel"));
  document.querySelectorAll(".sq-last").forEach(e => e.classList.remove("sq-last"));
  document.querySelectorAll(".sq-dot").forEach(e => e.classList.remove("sq-dot"));
}

function drawHighlights() {
  clearHighlights();

  if (lastMove && view === game.history().length) {
    squareEl(lastMove.from)?.classList.add("sq-last");
    squareEl(lastMove.to)?.classList.add("sq-last");
  }

  if (selected) {
    squareEl(selected)?.classList.add("sq-sel");

    game.moves({ square: selected, verbose: true }).forEach(m => {
      squareEl(m.to)?.classList.add("sq-dot");
    });
  }
}

// ---------------- API ----------------

async function apiState() {
  const r = await fetch("/state");
  return r.json();
}

async function apiMove(uci) {
  const r = await fetch("/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uci })
  });
  return r.json();
}

async function apiGoto(ply) {
  const r = await fetch("/goto", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ view: ply })
  });
  return r.json();
}

// ---------------- Moves table ----------------

function renderMoves(movesSAN, currentView) {
  const box = document.getElementById("moves");
  box.innerHTML = "";

  for (let i = 0; i < movesSAN.length; i += 2) {
    const row = document.createElement("div");
    row.className = "moverow";

    const num = document.createElement("div");
    num.className = "move-num";
    num.textContent = i / 2 + 1 + ".";

    const w = document.createElement("div");
    w.className = "move";
    w.textContent = movesSAN[i] || "";

    const b = document.createElement("div");
    b.className = "move";
    b.textContent = movesSAN[i + 1] || "";

    if (currentView - 1 === i) w.classList.add("current");
    if (currentView - 1 === i + 1) b.classList.add("current");

    // click jump
    w.onclick = () => gotoPly(i + 1);
    b.onclick = () => gotoPly(i + 2);

    row.appendChild(num);
    row.appendChild(w);
    row.appendChild(b);

    box.appendChild(row);
  }
}

// ---------------- Turn ----------------

function renderTurn(turn) {
  const box = document.getElementById("turnbox");
  const text = document.getElementById("turntext");

  if (turn === "w") {
    box.style.background = "#fff";
    text.textContent = "White to move";
  } else {
    box.style.background = "#000";
    text.textContent = "Black to move";
  }
}

// ---------------- Navigation ----------------

async function gotoPly(ply) {
  const res = await apiGoto(ply);
  game.load(res.fen);
  boardUI.position(res.fen, false);

  view = ply;
  lastMove = null;
  selected = null;

  renderMoves(res.moves_san, res.view);
  renderTurn(res.turn);
  drawHighlights();
}

// ---------------- Legality ----------------

function isLegal(from, to) {
  return game.moves({ square: from, verbose: true }).some(m => m.to === to);
}

function localMove(from, to) {
  const p = game.get(from);
  if (!p) return null;

  let promo;
  if (p.type === "p") {
    if ((p.color === "w" && to[1] === "8") ||
        (p.color === "b" && to[1] === "1")) promo = "q";
  }

  return game.move({ from, to, promotion: promo });
}

// ---------------- Click play ----------------

function attachClicks() {
  document.getElementById("board").addEventListener("mousedown", e => {
    const sq = e.target.closest(".square-55d63");
    if (!sq) return;

    const cls = [...sq.classList].find(c => c.startsWith("square-") && c.length === 9);
    if (!cls) return;

    const square = cls.replace("square-", "");
    const piece = game.get(square);

    if (!selected) {
      if (!piece || piece.color !== game.turn()) return;
      selected = square;
      drawHighlights();
      return;
    }

    if (square === selected) {
      selected = null;
      drawHighlights();
      return;
    }

    if (piece && piece.color === game.turn()) {
      selected = square;
      drawHighlights();
      return;
    }

    if (!isLegal(selected, square)) return;

    const mv = localMove(selected, square);
    if (!mv) return;

    boardUI.position(game.fen(), false);

    lastMove = { from: selected, to: square };
    selected = null;
    drawHighlights();

    // IMPORTANT:
    // backend should truncate future history when move is made
    apiMove(mv.from + mv.to).then(res => {
      game.load(res.fen);
      boardUI.position(res.fen, false);

      view = res.view;
      renderMoves(res.moves_san, res.view);
      renderTurn(res.turn);
      drawHighlights();
    });
  });
}

// ---------------- Init ----------------

function init() {
  boardUI = Chessboard("board", {
    draggable: false,
    position: "start",
    moveSpeed: 0,
    snapSpeed: 0,
    appearSpeed: 0,
    pieceTheme: p => "/static/pieces/" + p.toLowerCase() + ".png"
  });

  attachClicks();

  apiState().then(s => {
    game.load(s.fen);
    boardUI.position(s.fen, false);

    view = s.view;

    renderMoves(s.moves_san, s.view);
    renderTurn(s.turn);
    drawHighlights();
  });
}

init();
