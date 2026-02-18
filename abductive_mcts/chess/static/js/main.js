let game = new Chess();
let selectedSquare = null;

async function syncState(data) {
    game.load(data.fen);
    UI.updateBoard(data.fen, data.last_move);
    UI.renderMoveTable(data.moves_san, data.move_times, data.view, handleGoto);
}

async function handleGoto(ply) {
    const data = await API.goto(ply);
    syncState(data);
}

function handleSquareClick(e) {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const sqEl = el?.closest(".square-55d63");
    if (!sqEl) return;

    const square = sqEl.getAttribute("data-square");

    // If clicking same square, deselect
    if (selectedSquare === square) {
        selectedSquare = null;
        UI.drawAllHighlights();
        return;
    }

    // Attempting a move
    if (selectedSquare) {
        const uci = selectedSquare + square;
        const moveAttempt = game.move({ from: selectedSquare, to: square, promotion: 'q' });
        
        if (moveAttempt) {
            selectedSquare = null;
            API.move(uci).then(syncState);
            return;
        }
    }

    // Selecting a new square
    selectedSquare = square;
    const legals = game.moves({ square, verbose: true });
    UI.drawAllHighlights(selectedSquare, legals);
}

async function init() {
    UI.initBoard();
    document.getElementById("board").addEventListener("mousedown", handleSquareClick);
    const state = await API.getState();
    syncState(state);
}

init();