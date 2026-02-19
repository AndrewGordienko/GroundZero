export class ChessBoard {
    constructor(elementId) {
        this.board = Chessboard(elementId, {
            draggable: false,
            position: "start",
            moveSpeed: 150,
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
        });
        this.lastMove = null;
    }

    render(fen, lastMove) {
        this.board.position(fen);
        this.lastMove = lastMove;
        this.drawHighlights();
    }

    drawHighlights(selectedSq = null, legalMoves = []) {
        this.clearHighlights();
        if (this.lastMove) {
            this.highlight(this.lastMove.from, "sq-last");
            this.highlight(this.lastMove.to, "sq-last");
        }
        if (selectedSq) this.highlight(selectedSq, "sq-sel");
        legalMoves.forEach(m => this.highlight(m.to, "sq-dot"));
    }

    highlight(sq, className) {
        const el = document.querySelector(`.square-${sq}`);
        if (el) el.classList.add(className);
    }

    clearHighlights() {
        document.querySelectorAll(".sq-sel, .sq-last, .sq-dot")
                .forEach(e => e.classList.remove("sq-sel", "sq-last", "sq-dot"));
    }
}