/**
 * UI Controller for the Chess Research Dashboard
 * Minimalist, borderless design with Engine-only history tracking.
 */
const UI = {
    board: null,
    evalChart: null,
    depthChart: null,
    lastMove: null,

    initBoard() {
        this.board = Chessboard("board", {
            draggable: false, 
            position: "start", 
            moveSpeed: 150, 
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
        });
        return this.board;
    },

    updateBoard(fen, lastMove) {
        this.board.position(fen);
        this.lastMove = lastMove;
        this.drawAllHighlights();
    },

    drawAllHighlights(selectedSq = null, legalMoves = []) {
        this.clearHighlights();
        if (this.lastMove) {
            this.highlight(this.lastMove.from, "sq-last");
            this.highlight(this.lastMove.to, "sq-last");
        }
        if (selectedSq) this.highlight(selectedSq, "sq-sel");
        legalMoves.forEach(m => this.highlight(m.to, "sq-dot"));
    },

    highlight(sq, className) {
        const el = document.querySelector(`.square-${sq}`);
        if (el) el.classList.add(className);
    },

    clearHighlights() {
        document.querySelectorAll(".sq-sel, .sq-last, .sq-dot")
                .forEach(e => e.classList.remove("sq-sel", "sq-last", "sq-dot"));
    },

    renderMoveTable(moves, times, currentView, onGoto) {
        const container = document.getElementById("moves-table");
        if (!container) return;
        
        container.innerHTML = "";
        const maxT = Math.max(...times, 0.5);

        for (let i = 0; i < moves.length; i += 2) {
            const row = document.createElement("div");
            row.className = "move-row";
            const num = document.createElement("div");
            num.className = "m-num";
            num.textContent = Math.floor(i / 2) + 1 + ".";

            row.append(
                num, 
                this.createMoveCell(moves[i], times[i], maxT, i + 1, currentView, onGoto),
                this.createMoveCell(moves[i + 1], times[i + 1], maxT, i + 2, currentView, onGoto)
            );
            container.appendChild(row);
        }
        container.scrollTop = container.scrollHeight;
    },

    createMoveCell(san, time, maxT, ply, current, onGoto) {
        const cell = document.createElement("div");
        cell.className = `m-cell ${current === ply ? 'active' : ''}`;
        if (!san) return cell;

        cell.onclick = () => onGoto(ply);
        const sanText = document.createElement("span");
        sanText.textContent = san;
        
        const barBg = document.createElement("div");
        barBg.className = "time-bar-bg";
        const barFill = document.createElement("div");
        barFill.className = "time-bar-fill";
        barFill.style.width = `${Math.min(100, (time / maxT) * 100)}%`;
        barBg.appendChild(barFill);

        cell.append(sanText, barBg);
        return cell;
    },

    /**
     * historyDepths should now be passed from main.js/app.py 
     */
    renderEngineStats(stats, historyEvals, historyDepths) {
        if (!stats) return;

        // 1. Update Numerical Stat Table (Sidebar)
        const wr = document.getElementById("win-rate");
        const sc = document.getElementById("sim-count");
        const dv = document.getElementById("depth-val");

        if (wr) wr.textContent = stats.win_prob + "%";
        if (sc) sc.textContent = stats.simulations;
        if (dv) dv.textContent = stats.depth;
        
        // 2. Filter Logic: Only show Engine Turns (Ply 2, 4, 6...)
        const engineIndices = (historyEvals || []).reduce((acc, val, idx) => {
            // idx 0 is start. idx 1 is human. idx 2 is engine...
            if (idx > 0 && idx % 2 === 0) acc.push(idx);
            return acc;
        }, []);

        const engineEvals = engineIndices.map(idx => historyEvals[idx] * 100);
        const engineDepths = engineIndices.map(idx => (historyDepths ? historyDepths[idx] : 0));
        const labels = engineIndices.map(idx => `Move ${idx / 2}`);

        // 3. Render PV Lines
        const pvTable = document.getElementById("pv-table");
        if (pvTable && stats.top_lines) {
            pvTable.innerHTML = stats.top_lines.map((l, i) => `
                <div class="pv-row" style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #f9f9f9; font-size:11px;">
                    <span style="font-family:monospace; font-weight:700;">${l.line}</span>
                    <span style="color:#999; font-size:10px;">Q: ${l.q.toFixed(2)} | ${l.visits}s</span>
                </div>
            `).join('');
        }

        // 4. Update Visualizations
        this.drawHeatmap(stats.heatmap || {});
        
        this.updateLineChart('evalChart', engineEvals, '#312e2b', 'Win %', labels);
        this.updateLineChart('depthChart', engineDepths, '#2196f3', 'Depth', labels);
    },

    updateLineChart(chartId, data, color, label, labels) {
        const ctx = document.getElementById(chartId)?.getContext('2d');
        if (!ctx) return;

        const chartKey = chartId === 'evalChart' ? 'evalChart' : 'depthChart';

        if (this[chartKey]) {
            this[chartKey].data.labels = labels;
            this[chartKey].data.datasets[0].data = data;
            this[chartKey].update('none'); 
        } else {
            this[chartKey] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label,
                        data: data,
                        borderColor: color,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: color,
                        tension: 0.2,
                        spanGaps: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            max: chartId === 'evalChart' ? 100 : undefined,
                            grid: { display: false }, 
                            ticks: { font: { size: 9 } } 
                        },
                        x: { 
                            grid: { display: false },
                            ticks: { font: { size: 9 }, maxRotation: 0, maxTicksLimit: 10 }
                        }
                    }
                }
            });
        }
    },

    drawHeatmap(heatmap) {
        const grid = document.getElementById("heatmap-grid");
        if (!grid) return;
        grid.innerHTML = "";
        
        const data = heatmap || {};
        const files = ['a','b','c','d','e','f','g','h'];
        
        for (let r = 8; r >= 1; r--) {
            for (let f = 0; f < 8; f++) {
                const sq = files[f] + r;
                const cell = document.createElement("div");
                cell.className = "h-cell";
                const intensity = (data[sq] !== undefined) ? data[sq] * 1.5 : 0;
                cell.style.background = `rgba(255, 87, 34, ${Math.min(0.8, intensity)})`; 
                grid.appendChild(cell);
            }
        }
    }
};