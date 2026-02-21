import math
import chess
import numpy as np
import time
import threading
import concurrent.futures
from collections import Counter
from .node import MCTSNode

class MCTS:
    def __init__(self, evaluator):
        self.params = {
            'SIMULATIONS': 400, 
            'C_PUCT': 2.0,      # Increased from 1.5 to encourage more exploration
            'ALPHA': 0.8,       # Increased from 0.3 to spread noise across more moves
            'EPS': 0.3,         # Increased from 0.25 to give noise more weight
            'FPU_REDUCTION': 0.2,
            'VIRTUAL_LOSS': 3.0,
            'PARALLEL_THREADS': 16 
        }
        self.evaluator = evaluator
        self.c_puct = self.params['C_PUCT']
        self.v_loss = self.params['VIRTUAL_LOSS']
        self.latest_depth = 0
        self.latest_heatmap = {}
        self.tree_lock = threading.Lock()

    def search(self, board: chess.Board, is_training=False, root=None):
        self.evaluator.clear_cache()
        
        if root is None:
            priors, _ = self.evaluator.evaluate(board)
            root = MCTSNode(priors)
        
        # Dirichlet Noise (Critical for diversity)
        if is_training and len(root.P) > 0:
            # High Alpha (0.8) creates a flatter distribution, forcing variety
            noise = np.random.dirichlet([self.params['ALPHA']] * len(root.P))
            for i, move in enumerate(root.P):
                root.P[move] = (1 - self.params['EPS']) * root.P[move] + self.params['EPS'] * noise[i]
        
        self.square_visits = Counter() 
        self.max_depth_reached = 0
        sim_count = int(self.params['SIMULATIONS'])
        num_threads = self.params['PARALLEL_THREADS']
        root_fen = board.fen()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(self._run_simulation, root_fen, root) for _ in range(sim_count)]
            concurrent.futures.wait(futures)

        self.latest_depth = self.max_depth_reached
        self.latest_heatmap = {
            chess.SQUARE_NAMES[s]: round(v / sim_count, 3) 
            for s, v in self.square_visits.items()
        }

        total_n = sum(root.N.values())
        if total_n == 0:
            return list(root.P.keys())[0], {m: 1/len(root.P) for m in root.P}, root
            
        pi_dist = {m: n / total_n for m, n in root.N.items()}
        best_move = max(root.N, key=root.N.get)
        
        return best_move, pi_dist, root

    def _run_simulation(self, fen, root):
        node = root
        path = []
        temp_board = chess.BaseBoard(fen)
        current_turn = 'w' in fen.split()[1] 
        depth = 0

        # SELECTION (Using Virtual Loss for Parallelism)
        with self.tree_lock:
            while True:
                move = self._select_child(node)
                path.append((node, move))
                self.square_visits[move.to_square] += 1
                
                node.N[move] += self.v_loss
                node.W[move] -= self.v_loss
                
                temp_board.push(move)
                current_turn = not current_turn
                depth += 1
                
                if move not in node.children:
                    break
                node = node.children[move]

        if depth > self.max_depth_reached:
            self.max_depth_reached = depth

        # EXPANSION & EVALUATION
        full_board_eval = chess.Board(temp_board.fen())
        full_board_eval.turn = current_turn

        if not full_board_eval.is_game_over():
            p_priors, value = self.evaluator.evaluate(full_board_eval)
            with self.tree_lock:
                if move not in node.children:
                    node.children[move] = MCTSNode(p_priors)
        else:
            res = full_board_eval.result()
            # AlphaZero perspective: value is relative to current_turn
            if res == "1-0":
                val = 1.0 if current_turn else -1.0
            elif res == "0-1":
                val = -1.0 if current_turn else 1.0
            else:
                val = 0.0
            value = val

        # BACKPROPAGATION
        with self.tree_lock:
            for n, m in reversed(path):
                n.N[m] = n.N[m] - self.v_loss + 1
                n.W[m] = n.W[m] + self.v_loss + value
                n.Q[m] = n.W[m] / n.N[m]
                value = -value

    def _select_child(self, node):
        total_n = sum(node.N.values())
        total_n_sqrt = math.sqrt(total_n + 1)
        
        if total_n > 0:
            parent_q = -sum(node.W.values()) / total_n
            fpu_val = parent_q - self.params['FPU_REDUCTION']
        else:
            fpu_val = 0.0

        best_score = -float('inf')
        best_move = None

        for move, p_val in node.P.items():
            n_v = node.N[move]
            q_val = node.W[move] / n_v if n_v > 0 else fpu_val
            # Upper Confidence Bound applied to Trees
            u = self.c_puct * p_val * total_n_sqrt / (1 + n_v)
            score = q_val + u
            
            if score > best_score:
                best_score, best_move = score, move
        return best_move