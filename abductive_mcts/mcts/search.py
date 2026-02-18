import math
import chess
import os
from collections import Counter
from .node import MCTSNode

def load_hyperparams():
    """Reads engine parameters from a local text file for live tweaking."""
    params = {}
    path = os.path.join(os.path.dirname(__file__), 'hyperparameters.txt')
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=')
                    params[k.strip()] = float(v.strip())
    except FileNotFoundError:
        # Robust defaults if file is missing
        params = {'SIMULATIONS': 400, 'C_PUCT': 1.75}
    return params

class MCTS:
    def __init__(self, evaluator):
        self.params = load_hyperparams()
        self.evaluator = evaluator
        # C_PUCT: Higher = more exploration, Lower = more depth/greed
        self.c_puct = self.params.get('C_PUCT', 1.75)

    def search(self, board: chess.Board):
        # 1. Initialize root
        priors, _ = self.evaluator.evaluate(board)
        root = MCTSNode(priors)
        
        # Tracking metrics for UI transparency
        square_visits = Counter()
        max_depth_reached = 0

        sim_count = int(self.params.get('SIMULATIONS', 400))
        
        for _ in range(sim_count):
            node = root
            temp_board = board.copy()
            path = []
            current_depth = 0

            # --- 1. SELECTION ---
            # Traverse until we hit a leaf or a move not yet expanded
            while True:
                move = self._select_child(node)
                path.append((node, move))
                
                # Track square focus for the heatmap
                square_visits[move.to_square] += 1
                
                temp_board.push(move)
                current_depth += 1
                
                if move not in node.children:
                    break
                node = node.children[move]

            # Update maximum search depth for the UI
            if current_depth > max_depth_reached:
                max_depth_reached = current_depth

            # --- 2. EXPANSION & EVALUATION ---
            if not temp_board.is_game_over():
                priors, value = self.evaluator.evaluate(temp_board)
                node.children[move] = MCTSNode(priors)
            else:
                # Terminal state evaluation
                res = temp_board.result()
                if res == "1-0": value = 1.0
                elif res == "0-1": value = -1.0
                else: value = 0.0
                
                # Align value with the side-to-move
                if not temp_board.turn:
                    value = -value

            # --- 3. BACKPROPAGATION ---
            # Climb back up the tree, flipping the value sign at each step
            self._backpropagate(path, value)

        # --- 4. ANALYTICS EXPORT ---
        best_move = max(root.N, key=root.N.get)
        
        # Extract Principal Variation (PV): The most likely future path
        top_lines = []
        # Sort moves at root by visit count (N)
        sorted_root_moves = sorted(root.N.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for m, visits in sorted_root_moves:
            line = [board.san(m)]
            curr_node = root.children.get(m)
            temp_b = board.copy()
            temp_b.push(m)
            
            # Follow the most-visited path 3 plies deeper (4 total)
            for _ in range(3):
                if curr_node and curr_node.N:
                    # Pick most visited child
                    best_next = max(curr_node.N, key=curr_node.N.get)
                    line.append(temp_b.san(best_next))
                    temp_b.push(best_next)
                    curr_node = curr_node.children.get(best_next)
                else:
                    break
            
            top_lines.append({
                "line": " ".join(line),
                "visits": visits,
                "q": round(root.Q[m], 3)
            })

        # Final bundle for the UI
        stats = {
            "win_prob": round(((root.Q[best_move] + 1) / 2) * 100, 1),
            "simulations": sim_count,
            "depth": max_depth_reached,
            "heatmap": {chess.SQUARE_NAMES[s]: round(v/sim_count, 2) for s, v in square_visits.items()},
            "top_lines": top_lines
        }

        return best_move, stats

    def _select_child(self, node):
        """Uses the PUCT formula to balance exploration and exploitation."""
        total_n = sum(node.N.values())
        best_score = -float('inf')
        best_move = None

        for move in node.N:
            q = node.Q[move]
            # Predictor + Uncertainty
            u = self.c_puct * node.P[move] * math.sqrt(total_n + 1) / (1 + node.N[move])
            score = q + u
            
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    def _backpropagate(self, path, value):
        """Propagates the leaf value back up to the root, flipping POV."""
        for node, move in reversed(path):
            node.N[move] += 1
            node.W[move] += value
            node.Q[move] = node.W[move] / node.N[move]
            # Flip sign: if it's good for White, it's bad for Black
            value = -value