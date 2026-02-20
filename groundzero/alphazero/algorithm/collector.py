import numpy as np
import chess
import torch
import os
import time
from algorithm.evaluator import AlphaZeroEvaluator
from mcts.search import MCTS

class DataCollector:
    def __init__(self, model_path=None, device="cpu"):
        self.evaluator = AlphaZeroEvaluator(model_path=model_path, device=device)
        self.engine = MCTS(self.evaluator)
        self.buffer_path = "data/replay_buffer/"
        os.makedirs(self.buffer_path, exist_ok=True)

    def update_model(self, path):
        """Reloads the model weights if a new file exists."""
        if os.path.exists(path):
            try:
                # Load state dict and ensure model is in eval mode
                self.evaluator.model.load_state_dict(torch.load(path, map_location=self.evaluator.device))
                self.evaluator.model.eval()
            except Exception:
                # Silently fail if trainer is currently writing to the file
                pass 

    def collect_game(self, worker_id=None, stats=None):
        """
        Plays a single game against itself.
        Updates shared stats dictionary if provided for dashboard visualization.
        """
        board = chess.Board()
        game_data = []
        move_count = 0

        while not board.is_game_over():
            # Perform MCTS search
            # We assume your MCTS.search returns the move and the distribution
            best_move, pi_dist = self.engine.search(board, is_training=True)
            
            # 1. LIVE UPDATE: Push progress to the shared dictionary for the dashboard
            if stats is not None and worker_id is not None:
                # We update the dictionary with current board state and stats
                stats[worker_id] = {
                    "status": "Searching",
                    "move_count": move_count,
                    "fen": board.fen(),
                    "turn": "White" if board.turn == chess.WHITE else "Black",
                    # If your MCTS object tracks depth, you can pull it here
                    "last_depth": getattr(self.engine, 'latest_depth', 0), 
                    "start_time": stats[worker_id].get("start_time", time.time())
                }

            # Convert pi_dist dict to a 4096-length numpy array
            pi_array = np.zeros(4096, dtype=np.float32)
            for move, prob in pi_dist.items():
                idx = (move.from_square * 64) + move.to_square
                if idx < 4096: # Safety check
                    pi_array[idx] = prob

            # Save state and the search-improved policy
            state = self.evaluator.encoder.encode(board)
            game_data.append({
                "state": state, 
                "pi": pi_array, 
                "turn": board.turn
            })

            board.push(best_move)
            move_count += 1

        # Assign outcome (z) relative to whose turn it was
        res = board.result()
        outcome = 1.0 if res == "1-0" else -1.0 if res == "0-1" else 0.0
        
        final_samples = []
        for sample in game_data:
            # AlphaZero perspective: z is 1 if that player won, -1 if they lost
            z = outcome if sample["turn"] == chess.WHITE else -outcome
            final_samples.append({
                "state": sample["state"],
                "pi": sample["pi"],
                "z": z
            })
            
        return final_samples

    def save_batch(self, game_data, filename):
        """Saves the collected game data to a compressed .npz file."""
        path = os.path.join(self.buffer_path, filename)
        
        states = np.array([s["state"] for s in game_data])
        pis = np.array([s["pi"] for s in game_data])
        zs = np.array([s["z"] for s in game_data])
        
        np.savez_compressed(path, states=states, pis=pis, zs=zs)