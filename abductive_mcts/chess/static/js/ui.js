const UI = {
    board: null,
    lastMove: null,
    
    initBoard() {
        this.board = Chessboard("board", {
            draggable: false,
            position: "start",
            moveSpeed: 100, // Faster for "research" feel
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

        if (selectedSq) {
            this.highlight(selectedSq, "sq-sel");
        }

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
    }
};