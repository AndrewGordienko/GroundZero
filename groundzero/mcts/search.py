import math
import chess
import os
import numpy as np
from collections import Counter
from .node import MCTSNode

def load_hyperparams():
    """Reads engine parameters from a local text file for live tweaking."""
    params = {}
    # Look for hyperparameters in the alphazero folder or current folder
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'alphazero', 'hyperparameters.txt')
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), 'hyperparameters.txt')
        
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    k, v = line.split('=')
                    params[k.strip()] = float(v.strip())
    except Exception:
        params = {'SIMULATIONS': 400, 'C_PUCT': 1.5, 'ALPHA': 0.3, 'EPS': 0.25}
    return params

class MCTS:
    def __init__(self, evaluator):
        self.params = load_hyperparams()
        self.evaluator = evaluator
        self.c_puct = self.params.get('C_PUCT', 1.5)
        self.alpha = self.params.get('ALPHA', 0.3) # Dirichlet noise parameter
        self.eps = self.params.get('EPS', 0.25)     # Noise weight

    def search(self, board: chess.Board, is_training=False):
        """
        Runs MCTS search. 
        is_training: If True, applies Dirichlet noise and returns the full pi distribution.
        """
        # 1. Initialize root
        priors, _ = self.evaluator.evaluate(board)
        
        # Add Dirichlet Noise to root for exploration during self-play
        if is_training and len(priors) > 0:
            noise = np.random.dirichlet([self.alpha] * len(priors))
            for i, move in enumerate(priors):
                priors[move] = (1 - self.eps) * priors[move] + self.eps * noise[i]
        
        root = MCTSNode(priors)
        
        square_visits = Counter()
        max_depth_reached = 0
        sim_count = int(self.params.get('SIMULATIONS', 400))
        
        # Optimization: Local references for speed in the loop
        select_child = self._select_child
        backprop = self._backpropagate

        for _ in range(sim_count):
            node = root
            temp_board = board.copy(stack=False) # Performance: don't copy the whole move history stack
            path = []
            depth = 0

            # --- 1. SELECTION ---
            while True:
                move = select_child(node)
                path.append((node, move))
                square_visits[move.to_square] += 1
                
                temp_board.push(move)
                depth += 1
                
                if move not in node.children:
                    break
                node = node.children[move]

            if depth > max_depth_reached:
                max_depth_reached = depth

            # --- 2. EXPANSION & EVALUATION ---
            if not temp_board.is_game_over():
                p_priors, value = self.evaluator.evaluate(temp_board)
                node.children[move] = MCTSNode(p_priors)
            else:
                res = temp_board.result()
                value = 1.0 if res == "1-0" else -1.0 if res == "0-1" else 0.0
                if not temp_board.turn: # Align value with perspective
                    value = -value

            # --- 3. BACKPROPAGATION ---
            backprop(path, value)

        # --- 4. EXPORT RESULTS ---
        # Get target policy pi (normalized visit counts)
        total_n = sum(root.N.values())
        pi_dist = {m: n / total_n for m, n in root.N.items()}
        
        # Move Selection: Most visited, not highest Q
        best_move = max(root.N, key=root.N.get)
        
        stats = {
            "win_prob": round(((root.Q[best_move] + 1) / 2) * 100, 1),
            "simulations": sim_count,
            "depth": max_depth_reached,
            "heatmap": {chess.SQUARE_NAMES[s]: round(v/sim_count, 2) for s, v in square_visits.items()},
            "top_lines": self._get_pv(board, root),
            "raw_visits": root.N # Added for the DataCollector
        }

        return (best_move, pi_dist) if is_training else (best_move, stats)

    def _select_child(self, node):
        """PUCT formula for node selection."""
        total_n_sqrt = math.sqrt(sum(node.N.values()) + 1)
        
        best_score = -float('inf')
        best_move = None

        for move in node.N:
            # AlphaZero PUCT: Q + C_puct * P * (sqrt(N_total) / (1 + N_child))
            u = self.c_puct * node.P[move] * total_n_sqrt / (1 + node.N[move])
            score = node.Q[move] + u
            
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    def _backpropagate(self, path, value):
        for node, move in reversed(path):
            node.N[move] += 1
            node.W[move] += value
            node.Q[move] = node.W[move] / node.N[move]
            value = -value # Flip POV for the parent

    def _get_pv(self, board, root):
        """Extracts the Principal Variation for UI display."""
        top_lines = []
        sorted_moves = sorted(root.N.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for m, visits in sorted_moves:
            line = [board.san(m)]
            curr = root.children.get(m)
            temp_b = board.copy(stack=False)
            temp_b.push(m)
            
            for _ in range(3):
                if curr and curr.N:
                    bm = max(curr.N, key=curr.N.get)
                    line.append(temp_b.san(bm))
                    temp_b.push(bm)
                    curr = curr.children.get(bm)
                else: break
            
            top_lines.append({"line": " ".join(line), "visits": visits, "q": round(root.Q[m], 3)})
        return top_lines