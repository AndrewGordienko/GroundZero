import numpy as np
import chess
import torch
import os
import time
from collections import Counter, deque
from algorithm.evaluator import AlphaZeroEvaluator
from mcts.search import MCTS

class DataCollector:
    def __init__(self, model_path=None, device="cpu"):
        self.evaluator = AlphaZeroEvaluator(model_path=model_path, device=device)
        self.engine = MCTS(self.evaluator)
        self.buffer_path = "data/replay_buffer/"
        os.makedirs(self.buffer_path, exist_ok=True)
        
        # --- Exploration Hyperparameters ---
        self.EXPLORATION_GAMES_THRESHOLD = 500  
        self.FORCE_RANDOM_PLIES = 2             
        
        self.total_games = 0
        self.total_samples = 0
        
        # PERSISTENT STATS
        self.opening_stats = Counter() 
        self.hall_of_fame = [] 
        self.all_time_phase = {"opening": 0.0, "midgame": 0.0, "endgame": 0.0}
        self.recent_phase_window = deque(maxlen=20) 

    def update_model(self, path):
        if os.path.exists(path):
            try:
                self.evaluator.model.load_state_dict(torch.load(path, map_location=self.evaluator.device))
                self.evaluator.model.eval()
            except: pass 

    def collect_game(self, worker_id=None, stats=None):
        board = chess.Board()
        game_data = []
        move_count = 0
        current_game_fens = [board.fen()]
        this_game_phase = {"opening": 0.0, "midgame": 0.0, "endgame": 0.0}
        value_history = []
        root = None 
        
        # Linear decay of forced randomness
        random_prob = max(0.0, 1.0 - (self.total_games / self.EXPLORATION_GAMES_THRESHOLD))
        is_forced_exploration = np.random.random() < random_prob
        temp_threshold = np.random.randint(15, 30)

        while not board.is_game_over() and move_count < 250:
            self.evaluator.clear_cache()
            
            start_search = time.time()
            best_move, pi_dist, root = self.engine.search(board, is_training=True, root=root)
            search_duration = time.time() - start_search

            # Selection Logic
            if is_forced_exploration and move_count < self.FORCE_RANDOM_PLIES:
                legal_moves = list(board.legal_moves)
                selected_move = np.random.choice(legal_moves)
                root = None 
            else:
                if move_count < temp_threshold:
                    moves = list(pi_dist.keys()); probs = list(pi_dist.values())
                    selected_move = np.random.choice(moves, p=probs)
                else:
                    selected_move = max(pi_dist, key=pi_dist.get)

                if root and selected_move in root.children:
                    root = root.children[selected_move]
                else:
                    root = None 

            if move_count == 0:
                self.opening_stats[board.san(selected_move)] += 1

            phase = "opening" if move_count < 20 else "midgame" if move_count < 40 else "endgame"
            this_game_phase[phase] += search_duration
            self.all_time_phase[phase] += search_duration

            # --- VALUE HEAD FIX ---
            # Map Tanh (-1 to 1) to Probability (0 to 1). 
            # 0.0 becomes 0.5 (50%), 1.0 becomes 1.0 (100%), -1.0 becomes 0.0 (0%)
            raw_val = float(self.evaluator.latest_value)
            win_prob = (raw_val + 1) / 2 
            value_history.append(raw_val)

            if stats is not None and worker_id is not None:
                window_sum = {"opening": 0.0, "midgame": 0.0, "endgame": 0.0}
                for g in self.recent_phase_window:
                    for k in window_sum: window_sum[k] += g[k]

                stats[worker_id] = {
                    "status": "Thinking" if not (is_forced_exploration and move_count < self.FORCE_RANDOM_PLIES) else "Exploring",
                    "move_count": move_count,
                    "last_depth": int(self.engine.latest_depth),
                    "value": round(win_prob, 3), # Sends 0.500 instead of 50.0
                    "entropy": float(-np.sum(np.array(list(pi_dist.values())) * np.log2(np.array(list(pi_dist.values())) + 1e-9))),
                    "inference_ms": float(self.evaluator.last_inference_time * 1000),
                    "fen": board.fen(),
                    "history_fens": list(current_game_fens),
                    "phase_times": {"global": self.all_time_phase.copy(), "recent": window_sum},
                    "total_games": self.total_games,
                    "total_samples": self.total_samples,
                    "openings": dict(self.opening_stats),
                    "turn": "White" if board.turn == chess.WHITE else "Black",
                    "recent_gallery": list(self.hall_of_fame)
                }

            state = self.evaluator.encoder.encode(board)
            pi_array = np.zeros(4096, dtype=np.float32)
            for move, prob in pi_dist.items():
                idx = (move.from_square * 64) + move.to_square
                pi_array[idx] = prob
            
            game_data.append({"state": state, "pi": pi_array, "turn": board.turn})
            board.push(selected_move)
            current_game_fens.append(board.fen())
            move_count += 1

        self.recent_phase_window.append(this_game_phase)
        res_str = board.result() if board.is_game_over() else "1/2-1/2"
        outcome = 1.0 if res_str == "1-0" else -1.0 if res_str == "0-1" else 0.0
        
        # Interest score for Hall of Fame
        val_arr = np.array(value_history)
        swings = np.abs(np.diff(val_arr)).sum() if len(val_arr) > 1 else 0
        interest_score = swings + (move_count / 100.0) + (5 if res_str != "1/2-1/2" else 0)
        self.hall_of_fame.append({
            "id": f"G{self.total_games}", 
            "result": res_str, 
            "score": round(interest_score, 2), 
            "moves": move_count, 
            "history": list(current_game_fens)
        })
        self.hall_of_fame = sorted(self.hall_of_fame, key=lambda x: x['score'], reverse=True)[:8]

        self.total_games += 1
        self.total_samples += len(game_data)
        return [{"state": s["state"], "pi": s["pi"], "z": float(outcome if s["turn"] == chess.WHITE else -outcome)} for s in game_data]

    def save_batch(self, game_data, filename):
        path = os.path.join(self.buffer_path, filename)
        np.savez_compressed(
            path, 
            states=np.array([s["state"] for s in game_data], dtype=np.float32), 
            pis=np.array([s["pi"] for s in game_data], dtype=np.float32), 
            zs=np.array([s["z"] for s in game_data], dtype=np.float32)
        )