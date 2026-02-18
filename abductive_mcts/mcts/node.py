import chess

class MCTSNode:
    def __init__(self, priors: dict):
        """
        priors: dict of {chess.Move: probability} for moves available at this state.
        """
        self.children = {} # Maps move -> child MCTSNode
        
        # Statistics for moves LEAVING this node
        self.N = {} # Visit count
        self.W = {} # Total value
        self.Q = {} # Mean value
        self.P = {} # Prior probability

        for mv, prob in priors.items():
            self.N[mv] = 0
            self.W[mv] = 0.0
            self.Q[mv] = 0.0
            self.P[mv] = prob