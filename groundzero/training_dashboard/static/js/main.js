let activeWorkerId = "0";

function pieceTheme(piece) {
    return '/static/js/pieces/' + piece.toLowerCase() + '.png';
}

// Initialize the board with the custom piece theme
const config = {
    position: 'start',
    draggable: false,
    pieceTheme: pieceTheme
};

const board = Chessboard('board', config);

async function updateDashboard() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update Global Stats
        const bufferElement = document.getElementById('buffer-count');
        if (bufferElement) bufferElement.innerText = data.buffer_count;

        const workerList = document.getElementById('worker-list');
        workerList.innerHTML = '';

        Object.entries(data.workers).forEach(([id, stats]) => {
            const card = document.createElement('div');
            card.className = `worker-card ${id === activeWorkerId ? 'active' : ''}`;
            
            // Set up click handler to switch the "Live Inspection" view
            card.onclick = () => { 
                activeWorkerId = id; 
                updateDashboard(); // Refresh immediately on click
            };
            
            card.innerHTML = `
                <div class="id">WORKER_0${id} <span style="float:right; color:#ccc;">${stats.status}</span></div>
                <div class="meta">${stats.fen ? stats.fen.substring(0, 30) : 'Initializing...'}...</div>
            `;
            workerList.appendChild(card);

            // If this is the worker we are inspecting, update the main board and stats table
            if (id === activeWorkerId) {
                if (stats.fen && stats.fen !== "-") {
                    board.position(stats.fen);
                }
                
                // Update Sidebar Stats Table
                const activeIdEl = document.getElementById('active-worker-id');
                const turnEl = document.getElementById('stat-turn');
                const movesEl = document.getElementById('stat-moves');
                const depthEl = document.getElementById('stat-depth');

                if (activeIdEl) activeIdEl.innerText = id;
                if (turnEl) turnEl.innerText = stats.turn || "-";
                if (movesEl) movesEl.innerText = stats.move_count || 0;
                if (depthEl) depthEl.innerText = stats.last_depth || 0;
            }
        });

    } catch (e) {
        console.warn("Dashboard Sync: Waiting for worker data...");
    }
}

// Poll every 1 second for a real-time monitor feel
setInterval(updateDashboard, 1000);

// Initial call
updateDashboard();