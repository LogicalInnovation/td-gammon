import os
import sys
import copy
import time
import enum
import random
import numpy as np


class Event(enum.Enum):
    ROLL = 1
    MOVE = 4
    WIN_SINGLE = 14
    WIN_GAMMON = 15
    WIN_BACKGAMMON = 16


class Game:

    LAYOUT = "0-2-o,5-5-x,7-3-x,11-5-o,12-5-x,16-3-o,18-5-o,23-2-x"
    NUMCOLS = 24
    QUAD = 6
    OFF = 'off'
    ON = 'on'
    TOKENS = ['x', 'o']

    def __init__(self, layout=LAYOUT, grid=None, off_pieces=None, bar_pieces=None, num_pieces=None, players=None):
        """
        Define a new game object
        """
        self.die = Game.QUAD
        self.layout = layout
        if grid:
            self.grid = copy.deepcopy(grid)
            self.off_pieces = copy.deepcopy(off_pieces)
            self.bar_pieces = copy.deepcopy(bar_pieces)
            self.num_pieces = copy.deepcopy(num_pieces)
            self.players = players
            return
        self.players = Game.TOKENS
        self.grid = [[] for _ in range(Game.NUMCOLS)]
        self.off_pieces = {}
        self.bar_pieces = {}
        self.num_pieces = {}
        for t in self.players:
            self.bar_pieces[t] = []
            self.off_pieces[t] = []
            self.num_pieces[t] = 0
        self.events = []

    @staticmethod
    def new():
        game = Game()
        game.reset()
        return game

    def add_event(self, player, event, *args):
        assert isinstance(event, Event)
        self.events.append((player, event, args))

    def save_tmg(self, filename, player1=None, player2=None):
        if not self.is_over():
            raise ValueError('Match is not over. Only complete matches can be '
                             'saved to tmg files')
        if player1 is None:
            player1 = 'randomguy1'
        if player2 is None:
            player2 = 'randomguy2'

        with open(filename, 'w') as fout:
            header = """MatchID: 0
                        Player1: 10001 %s 4.00
                        Player2: 10002 %s 4.00
                        wonAmount: 7.8
                        Stake: 2.00
                        RakePct: 0.00
                        MaxRakeAbs: 0.00
                        RakeAbs: 0.00
                        Startdate: 2010-04-05 14:03:36
                        Jacoby: 0
                        AutoDistrib: 0
                        Automatics: 0
                        Beavers: 0
                        Raccons: 0
                        Crawford: 1
                        Cube: 1
                        MaxCube: 512
                        Length: 0
                        MaxGames: 512
                        Variant: 1
                        PlayMoney: 0
                        BuyInAndPrizeType: 1
                        FeeType: 1
                        Game 1: 0-0
                        0 19 4.00 0.0 4.00 0.0 Settlement""" % (player1, player2)

            for line in header.split('\n'):
                fout.write(line.lstrip(' '))
                fout.write('\n')

            turn_nb = 1
            last_p = self.events[1][0]
            half_turn = False
            for i in range(len(self.events)):
                if self.events[i][0] != last_p:
                    if half_turn == True:
                        turn_nb += 1
                    half_turn = not half_turn
                    last_p = self.events[i][0]

                turn = '  ' if self.events[i][0] == 0 else ' -'
                ev_code = self.events[i][1].value
                if ev_code == Event.WIN_SINGLE.value:
                    points = 2
                    player = player1 if self.events[i][0] == 0 else player2
                    args = [points, player, 'wins', points, 'points']
                else:
                    args = self.events[i][2]
                fout.write('%s%d %d' % (turn, turn_nb, ev_code))
                for a in args:
                    fout.write(' %s' % str(a))
                fout.write('\n')

    def extract_features(self, player):
        features = []
        for p in self.players:
            for col in self.grid:
                feats = [0.] * 6
                if len(col) > 0 and col[0] == p:
                    for i in range(len(col)):
                        feats[min(i, 5)] += 1
                features += feats
            features.append(float(len(self.bar_pieces[p])) / 2.)
            features.append(float(len(self.off_pieces[p])) / self.num_pieces[p])
        if player == self.players[0]:
            features += [1., 0.]
        else:
            features += [0., 1.]
        return np.array(features).reshape(1, -1)

    def roll_dice(self):
        return (random.randint(1, self.die), random.randint(1, self.die))

    def play(self, players, draw=False):
        player_num = random.randint(0, 1)
        while not self.is_over():
            self.next_step(players[player_num], player_num, draw=draw)
            player_num = (player_num + 1) % 2
            self.reverse()
        player_num = (player_num + 1) % 2
        self.add_event(player_num, Event.WIN_SINGLE)
        return self.winner()

    def next_step(self, player, player_num, draw=False):
        roll = self.roll_dice()
        self.add_event(player_num, Event.ROLL, roll[0] * 10 + roll[1])

        if draw:
            self.draw()

        move = self.take_turn(player, roll, draw=draw)
        if move:
            inv_pips = list(range(24)[::-1])
            formatted_moves = []
            for mv in move:

                if mv[0] != Game.ON:
                    mv = inv_pips[mv[0]], mv[1]
                if mv[1] != Game.OFF:
                    mv = mv[0], inv_pips[mv[1]]

                if mv[0] == Game.ON:
                    mv = 24, mv[1]
                if mv[1] == Game.OFF:
                    mv = mv[0], -1
                mv = mv[0] + 1, mv[1] + 1
                formatted_moves.append(str(mv[0]) + '/' + str(mv[1]))

            self.add_event(player_num, Event.MOVE, *formatted_moves)
        else:
            self.add_event(player_num, Event.MOVE, '0/0')

    def take_turn(self, player, roll, draw=False):
        if draw:
            print("Player %s rolled <%d, %d>." % (player.player, roll[0], roll[1]))
            time.sleep(1)

        moves = self.get_actions(roll, player.player, nodups=True)
        move = player.get_action(moves, self) if moves else None

        if move:
            self.take_action(move, player.player)

        return move

    def clone(self):
        """
        Return an exact copy of the game. Changes can be made
        to the cloned version without affecting the original.
        """
        return Game(None, self.grid, self.off_pieces,
                    self.bar_pieces, self.num_pieces, self.players)

    def take_action(self, action, token):
        """
        Makes given move for player, assumes move is valid,
        will remove pieces from play
        """
        ateList = [0] * 4
        for i, (s, e) in enumerate(action):
            if s == Game.ON:
                piece = self.bar_pieces[token].pop()
            else:
                piece = self.grid[s].pop()
            if e == Game.OFF:
                self.off_pieces[token].append(piece)
                continue
            if len(self.grid[e]) > 0 and self.grid[e][0] != token:
                bar_piece = self.grid[e].pop()
                self.bar_pieces[bar_piece].append(bar_piece)
                ateList[i] = 1
            self.grid[e].append(piece)
        return ateList

    def undo_action(self, action, player, ateList):
        """
        Reverses given move for player, assumes move is valid,
        will remove pieces from play
        """
        for i, (s, e) in enumerate(reversed(action)):
            if e == Game.OFF:
                piece = self.off_pieces[player].pop()
            else:
                piece = self.grid[e].pop()
                if ateList[len(action) - 1 - i]:
                    bar_piece = self.bar_pieces[self.opponent(player)].pop()
                    self.grid[e].append(bar_piece)
            if s == Game.ON:
                self.bar_pieces[player].append(piece)
            else:
                self.grid[s].append(piece)


    def get_actions(self, roll, player, nodups=False):
        """
        Get set of all possible move tuples
        """
        moves = set()
        if nodups:
            start = 0
        else:
            start = None

        r1, r2 = roll
        if r1 == r2: # doubles
            i = 4
            # keep trying until we find some moves
            while not moves and i > 0:
                self.find_moves(tuple([r1]*i), player, (), moves, start)
                i -= 1
        else:
            self.find_moves(roll, player, (), moves, start)
            self.find_moves((r2, r1), player, (), moves, start)
            # has no moves, try moving only one piece
            if not moves:
                for r in roll:
                    self.find_moves((r, ), player, (), moves, start)

        return moves

    def find_moves(self, rs, player, move, moves, start=None):
        if len(rs)==0:
            moves.add(move)
            return
        r, rs = rs[0], rs[1:]
        # see if we can remove a piece from the bar
        if self.bar_pieces[player]:
            if self.can_onboard(player, r):
                piece = self.bar_pieces[player].pop()
                bar_piece = None
                if len(self.grid[r - 1]) == 1 and self.grid[r - 1][-1]!=player:
                    bar_piece = self.grid[r - 1].pop()

                self.grid[r - 1].append(piece)

                self.find_moves(rs, player, move+((Game.ON, r - 1), ), moves, start)
                self.grid[r - 1].pop()
                self.bar_pieces[player].append(piece)
                if bar_piece:
                    self.grid[r - 1].append(bar_piece)
            return

        # otherwise check each grid location for valid move using r
        offboarding = self.can_offboard(player)

        for i in range(len(self.grid)):
            if start is not None:
                start = i
            if self.is_valid_move(i, i + r, player):

                piece = self.grid[i].pop()
                bar_piece = None
                if len(self.grid[i+r]) == 1 and self.grid[i+r][-1] != player:
                    bar_piece = self.grid[i + r].pop()
                self.grid[i + r].append(piece)
                self.find_moves(rs, player, move + ((i, i + r), ), moves, start)
                self.grid[i + r].pop()
                self.grid[i].append(piece)
                if bar_piece:
                    self.grid[i + r].append(bar_piece)

            # If we can't move on the board can we take the piece off?
            if offboarding and self.remove_piece(player, i, r):
                piece = self.grid[i].pop()
                self.off_pieces[player].append(piece)
                self.find_moves(rs, player, move + ((i, Game.OFF), ), moves, start)
                self.off_pieces[player].pop()
                self.grid[i].append(piece)

    def opponent(self, token):
        """
        Retrieve opponent players token for a given players token.
        """
        for t in self.players:
            if t != token:
                return t

    def is_won(self, player):
        """
        If game is over and player won, return True, else return False
        """
        return self.is_over() and player == self.players[self.winner()]

    def is_lost(self, player):
        """
        If game is over and player lost, return True, else return False
        """
        return self.is_over() and player != self.players[self.winner()]

    def reverse(self):
        """
        Reverses a game allowing it to be seen by the opponent
        from the same perspective
        """
        self.grid.reverse()
        self.players.reverse()

    def reset(self):
        """
        Resets game to original layout.
        """
        for col in self.layout.split(','):
            loc, num, token = col.split('-')
            self.grid[int(loc)] = [token for _ in range(int(num))]
        for col in self.grid:
            for piece in col:
                self.num_pieces[piece] += 1
        self.event = []

    def winner(self):
        """
        Get winner.
        """
        return 0 if len(self.off_pieces[self.players[0]]) == self.num_pieces[self.players[0]] else 1

    def is_over(self):
        """
        Checks if the game is over.
        """
        for t in self.players:
            if len(self.off_pieces[t]) == self.num_pieces[t]:
                return True
        return False

    def can_offboard(self, player):
        count = 0
        for i in range(Game.NUMCOLS - self.die, Game.NUMCOLS):
            if len(self.grid[i]) > 0 and self.grid[i][0] == player:
                count += len(self.grid[i])
        if count+len(self.off_pieces[player]) == self.num_pieces[player]:
            return True
        return False

    def can_onboard(self, player, r):
        """
        Can we take a players piece on the bar to a position
        on the grid given by roll-1?
        """
        if len(self.grid[r - 1]) <= 1 or self.grid[r - 1][0] == player:
            return True
        else:
            return False

    def remove_piece(self, player, start, r):
        """
        Can we remove a piece from location start with roll r ?
        In this function we assume we are cool to offboard,
        i.e. no pieces on the bar and all are in the home quadrant.
        """
        if start < Game.NUMCOLS - self.die:
            return False
        if len(self.grid[start]) == 0 or self.grid[start][0] != player:
            return False
        if start + r == Game.NUMCOLS:
            return True
        if start + r > Game.NUMCOLS:
            for i in range(start - 1, Game.NUMCOLS - self.die - 1, -1):
                if len(self.grid[i]) != 0 and self.grid[i][0] == self.players[0]:
                    return False
            return True
        return False

    def is_valid_move(self, start, end, token):
        if len(self.grid[start]) > 0 and self.grid[start][0] == token:
            if end < 0 or end >= len(self.grid):
                return False
            if len(self.grid[end]) <= 1:
                return True
            if len(self.grid[end]) > 1 and self.grid[end][-1] == token:
                return True
        return False

    def draw_col(self,i,col):
        p = "| "
        if i==-2:
            if col<10:
                p += " "
            p += str(col) + " "
        elif i==-1:
            p += "-- "
        elif len(self.grid[col])>i:
            p += " " + self.grid[col][i] + " "
        else:
            p += "   "
        sys.stdout.write(p)

    def draw(self):
        os.system('clear')
        largest = max([len(self.grid[i]) for i in range(len(self.grid)//2,len(self.grid))])
        for i in range(-2,largest):
            for col in range(len(self.grid)//2,len(self.grid)):
                self.draw_col(i,col)
            print("|")
        print("\n")
        largest = max([len(self.grid[i]) for i in range(len(self.grid)//2)])
        for i in range(largest-1,-3,-1):
            for col in range(len(self.grid)//2-1,-1,-1):
                self.draw_col(i,col)
            print("|")
        for t in self.players:
            sys.stdout.write("<Player %s>  Off Board :  "%(t))
            for piece in self.off_pieces[t]:
                sys.stdout.write(t+' ')
            sys.stdout.write("   Bar :  ")
            for piece in self.bar_pieces[t]:
                sys.stdout.write(t+' ')
            print('')
