import torch
import chess
from .model import AlphaNet
from .encoder import AlphaZeroEncoder

class AlphaZeroEvaluator:
    def __init__(self, model_path=None, device="cpu"):
        self.device = device
        self.encoder = AlphaZeroEncoder(history_len=2) # Our 25-plane lite version
        self.model = AlphaNet(num_res_blocks=10, channels=128).to(self.device)
        
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.eval()

    @torch.no_grad()
    def evaluate(self, board: chess.Board):
        # 1. Neural Forward Pass
        # Encoder handles the board -> (25, 8, 8) tensor
        encoded = self.encoder.encode(board)
        tensor = torch.from_numpy(encoded).unsqueeze(0).to(self.device)
        
        logits, value = self.model(tensor)
        
        # 2. Policy Mapping (Mapping 4096 logits to legal moves)
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        legal_moves = list(board.legal_moves)
        priors = {}
        
        for move in legal_moves:
            # Simple indexing: (from_sq * 64) + to_sq
            idx = (move.from_square * 64) + move.to_square
            priors[move] = float(probs[idx])

        # Re-normalize priors over legal moves only
        total_p = sum(priors.values())
        if total_p > 1e-8:
            priors = {m: p / total_p for m, p in priors.items()}
        else:
            # Fallback to uniform if the model is untrained/junk
            priors = {m: 1.0/len(legal_moves) for m in legal_moves}

        return priors, float(value.item())