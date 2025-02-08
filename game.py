import math
import random
import copy

class UltimateTTTState:
    def __init__(self):
        self.boards = [[" " for _ in range(9)] for _ in range(9)]
        self.board_winners = [None for _ in range(9)]
        self.current_player = "X"
        self.next_board = None
        self.overall_winner = None
        self.score_x = 0
        self.score_o = 0
        self.draws = 0

    def clone(self):
        clone_state = UltimateTTTState()
        clone_state.boards = copy.deepcopy(self.boards)
        clone_state.board_winners = copy.deepcopy(self.board_winners)
        clone_state.current_player = self.current_player
        clone_state.next_board = self.next_board
        clone_state.overall_winner = self.overall_winner
        clone_state.score_x = self.score_x
        clone_state.score_o = self.score_o
        clone_state.draws = self.draws
        return clone_state

    def get_legal_moves(self):
        moves = []
        if self.next_board is not None and self.board_winners[self.next_board] is None:
            boards_to_consider = [self.next_board]
        else:
            boards_to_consider = [i for i in range(9) if self.board_winners[i] is None]
        
        for b in boards_to_consider:
            for i in range(9):
                if self.boards[b][i] == " ":
                    moves.append((b, i))
        return moves

    def make_move(self, move):
        board_index, cell_index = move
        self.boards[board_index][cell_index] = self.current_player

        if self.board_winners[board_index] is None:
            winner = self.check_small_board_winner(self.boards[board_index])
            if winner is not None:
                self.board_winners[board_index] = winner
                if winner == "X":
                    self.score_x += 1
                elif winner == "O":
                    self.score_o += 1
                elif winner == "D":
                    self.draws += 1
            elif " " not in self.boards[board_index]:
                self.board_winners[board_index] = "D"
                self.draws += 1

        overall = self.check_overall_winner()
        if overall:
            self.overall_winner = overall

        self.next_board = cell_index if self.board_winners[cell_index] is None else None
        self.current_player = "O" if self.current_player == "X" else "X"

    def check_small_board_winner(self, board):
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for a, b, c in wins:
            if board[a] != " " and board[a] == board[b] == board[c]:
                return board[a]
        return None

    def check_overall_winner(self):
        meta = [bw if bw in ["X", "O"] else " " for bw in self.board_winners]
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for a, b, c in wins:
            if meta[a] != " " and meta[a] == meta[b] == meta[c]:
                return meta[a]
        if all(bw is not None for bw in self.board_winners):
            return "D"
        return None

    def is_terminal(self):
        return self.overall_winner is not None or len(self.get_legal_moves()) == 0

class MCTSNode:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.untried_moves = state.get_legal_moves()
        self.visits = 0
        self.wins = 0
        self.player_just_moved = "O" if state.current_player == "X" else "X"

    def uct_select_child(self, exploration=math.sqrt(2)):
        return max(
            self.children,
            key=lambda c: (c.wins / c.visits) + exploration * math.sqrt(math.log(self.visits) / c.visits)
        )

    def add_child(self, move, state):
        child = MCTSNode(state, parent=self, move=move)
        self.untried_moves.remove(move)
        self.children.append(child)
        return child

    def update(self, result):
        self.visits += 1
        if result == self.player_just_moved:
            self.wins += 1

def mcts(root_state, iterations):
    root_node = MCTSNode(root_state)
    
    for _ in range(iterations):
        node = root_node
        state = root_state.clone()

        while not node.untried_moves and node.children:
            node = node.uct_select_child()
            state.make_move(node.move)

        if node.untried_moves:
            move = random.choice(node.untried_moves)
            state.make_move(move)
            node = node.add_child(move, state)

        while not state.is_terminal():
            state.make_move(random.choice(state.get_legal_moves()))

        result = state.overall_winner
        while node is not None:
            node.update(result)
            node = node.parent
    
    return max(root_node.children, key=lambda c: c.visits).move