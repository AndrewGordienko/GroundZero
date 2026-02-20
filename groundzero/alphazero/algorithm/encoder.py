import numpy as np
import chess

class AlphaZeroEncoder:
    def __init__(self, history_len=2):
        """
        A balanced encoder. 
        Current board (12) + 1 Past board (12) + 1 Meta (1) = 25 planes.
        """
        self.history_len = history_len
        self.num_planes = (12 * history_len) + 1

    def encode(self, board: chess.Board):
        planes = np.zeros((self.num_planes, 8, 8), dtype=np.float32)
        us = board.turn
        them = not board.turn

        # 1. Encode History
        temp_board = board.copy()
        for i in range(self.history_len):
            if i > 0:
                if len(temp_board.move_stack) > 0:
                    temp_board.pop()
                else:
                    break # Pad with zeros if no more history
            
            offset = i * 12
            self._encode_pieces(temp_board, planes, offset, us, them)

        # 2. Metadata Plane (The last plane)
        meta_idx = self.num_planes - 1
        
        # Castling Rights (Our K/Q, then Theirs)
        if board.has_kingside_castling_rights(us):  planes[meta_idx, 0, 7] = 1.0
        if board.has_queenside_castling_rights(us): planes[meta_idx, 0, 0] = 1.0
        if board.has_kingside_castling_rights(them): planes[meta_idx, 7, 7] = 1.0
        if board.has_queenside_castling_rights(them): planes[meta_idx, 7, 0] = 1.0
        
        # Half-move clock (50-move rule progress)
        planes[meta_idx, 4, 4] = board.halfmove_clock / 100.0

        return planes

    def _encode_pieces(self, board, planes, offset, us, them):
        for piece_type in range(1, 7):
            # Our pieces
            self._fill_plane(board.pieces(piece_type, us), planes[offset + piece_type - 1], us)
            # Their pieces
            self._fill_plane(board.pieces(piece_type, them), planes[offset + piece_type + 5], us)

    def _fill_plane(self, bitset, plane, perspective):
        for square in bitset:
            # Mirror for Black POV
            render_sq = square if perspective == chess.WHITE else chess.square_mirror(square)
            rank, file = divmod(render_sq, 8)
            plane[rank, file] = 1.0