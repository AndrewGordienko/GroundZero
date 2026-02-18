/**
 * Main Controller for the Chess Research Lab
 * Handles game state synchronization and user interaction.
 */
let game = new Chess();
let selectedSquare = null;

async function syncState(data) {
    if (!data) return;
    
    // Update local chess.js instance
    game.load(data.fen);
    
    // Update the Board UI and Highlights
    UI.updateBoard(data.fen, data.last_move);
    
    // Render the Sidebar Move History
    UI.renderMoveTable(data.moves_san, data.move_times, data.view, handleGoto);
    
    // Update Research Stats (Heatmap, Charts, Depth)
    UI.renderEngineStats(data.engine_stats, data.history_evals);
}

async function handleGoto(ply) {
    const data = await API.goto(ply);
    syncState(data);
}

async function handleSquareClick(e) {
    // Robustly find the square element even if clicking the piece image
    const sqEl = e.target.closest(".square-55d63");
    if (!sqEl) return;

    const square = sqEl.getAttribute("data-square");

    // 1. Handle Deselection
    if (selectedSquare === square) {
        selectedSquare = null;
        UI.drawAllHighlights();
        return;
    }

    // 2. Handle Move Attempt
    if (selectedSquare) {
        const uci = selectedSquare + square;
        const moveAttempt = game.move({ from: selectedSquare, to: square, promotion: 'q' });
        
        if (moveAttempt) {
            selectedSquare = null;
            
            // Visual feedback: Start thinking
            const progress = document.getElementById("thinking-progress");
            if (progress) progress.style.width = "100%";
            
            const response = await API.move(uci);
            if (response.ok) {
                syncState(response);
                
                // Automatically trigger MCTS Engine Move
                const engineData = await API.engineMove();
                if (engineData && engineData.ok) {
                    syncState(engineData);
                }
            }
            
            if (progress) progress.style.width = "0%";
            return;
        }
    }

    // 3. Handle Selection
    selectedSquare = square;
    const legals = game.moves({ square, verbose: true });
    
    // If we clicked a square with no legal moves, don't highlight it as selection
    if (legals.length === 0 && !game.get(square)) {
        selectedSquare = null;
        UI.drawAllHighlights();
    } else {
        UI.drawAllHighlights(selectedSquare, legals);
    }
}

async function init() {
    // Initialize Chessboard.js
    UI.initBoard();
    
    // Attach click listener to the board wrapper
    const boardEl = document.getElementById("board");
    if (boardEl) {
        boardEl.addEventListener("mousedown", handleSquareClick);
    }
    
    // Initial state sync
    const state = await API.getState();
    syncState(state);
}

// Start the app
init();