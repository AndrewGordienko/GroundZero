import chess

# Piece-Square Tables (PST)
# Values represent the bonus/penalty for a piece being on a specific square.
# Perspective is for White; we flip for Black.
PST = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    chess.KING: [
        # Middle game: Stay tucked in the corner
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20
    ]
}

class MaterialEvaluator:
    def __init__(self):
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }

    def evaluate(self, board: chess.Board):
        # 1. Policy (Priors)
        # For transparency, we could eventually weight this by moves that 
        # lead to better board states, but for pure MCTS we use uniform priors.
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return {}, 0
        priors = {mv: 1.0 / len(legal_moves) for mv in legal_moves}

        # 2. Positional Value
        if board.is_checkmate():
            # If it's currently our turn and we are in checkmate, value is -1
            return priors, -1.0
        
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue
            
            # Material value
            val = self.piece_values.get(piece.piece_type, 0)
            
            # PST value
            pst_val = 0
            if piece.piece_type in PST:
                # If black, flip the square index to use the same table
                idx = square if piece.color == chess.WHITE else chess.SQUARE_NAMES.index(chess.square_name(square ^ 56))
                pst_val = PST[piece.piece_type][idx]
            
            total_val = val + pst_val
            if piece.color == chess.WHITE:
                score += total_val
            else:
                score -= total_val
        
        # Mobility Bonus: reward having more options
        mobility = board.legal_moves.count()
        score += (mobility * 10) if board.turn == chess.WHITE else -(mobility * 10)

        # Normalize to [-1, 1]
        # A 1000 point lead (approx. one Queen) is mapped to 0.8 win prob
        value = max(-1.0, min(1.0, score / 1200.0))
        
        # Adjust for Point of View (Side to move)
        # MCTS expects value relative to the player whose turn it is
        if not board.turn:
            value = -value
            
        return priors, value