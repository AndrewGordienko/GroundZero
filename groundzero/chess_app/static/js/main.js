import { API } from './api.js';
import { ChessBoard } from './components/board.js';
import { MoveHistory } from './components/history.js';
import { EngineStats } from './components/stats.js';
import { SearchHeatmap } from './components/charts/heatmap.js';
import { EvalChart } from './components/charts/eval.js';
import { DepthChart } from './components/charts/depth.js';

// Global Game State
let game = new Chess();
let selectedSquare = null;

// Initialize Components
const components = {
    board: new ChessBoard('board'),
    history: new MoveHistory('moves-table', handleGoto),
    stats: new EngineStats(),
    heatmap: new SearchHeatmap('heatmap-grid'),
    evalChart: new EvalChart('evalChart'),
    depthChart: new DepthChart('depthChart')
};

async function syncState(data) {
    if (!data) return;
    game.load(data.fen);

    // Filter engine-only turns for the charts
    const engineIndices = (data.history_evals || []).reduce((acc, _, i) => {
        if (i > 0 && i % 2 === 0) acc.push(i);
        return acc;
    }, []);
    const labels = engineIndices.map(idx => `M ${idx / 2}`);

    // Update all UI Components
    components.board.render(data.fen, data.last_move);
    components.history.render(data.moves_san, data.move_times, data.view);
    components.stats.update(data.engine_stats);
    components.heatmap.render(data.engine_stats.heatmap);
    
    components.evalChart.update(labels, engineIndices.map(i => data.history_evals[i] * 100));
    components.depthChart.update(labels, engineIndices.map(i => data.history_depths[i]));
}

async function handleGoto(ply) {
    const data = await API.goto(ply);
    syncState(data);
}

async function handleSquareClick(e) {
    const sqEl = e.target.closest(".square-55d63");
    if (!sqEl) return;

    const square = sqEl.getAttribute("data-square");

    if (selectedSquare === square) {
        selectedSquare = null;
        components.board.drawHighlights();
        return;
    }

    if (selectedSquare) {
        const uci = selectedSquare + square;
        const moveAttempt = game.move({ from: selectedSquare, to: square, promotion: 'q' });
        
        if (moveAttempt) {
            selectedSquare = null;
            const response = await API.move(uci);
            if (response.ok) {
                syncState(response);
                const engineData = await API.engineMove();
                if (engineData && engineData.ok) syncState(engineData);
            }
            return;
        }
    }

    selectedSquare = square;
    const legals = game.moves({ square, verbose: true });
    components.board.drawHighlights(selectedSquare, legals);
}

async function init() {
    const boardEl = document.getElementById("board");
    if (boardEl) boardEl.addEventListener("mousedown", handleSquareClick);
    
    const state = await API.getState();
    syncState(state);
}

init();