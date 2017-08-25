import numpy as np


def raw_board(game):
    features = []
    for p in game.players:
        for col in game.grid:
            feats = [0.] * 6
            if len(col) > 0 and col[0] == p:
                for i in range(len(col)):
                    feats[min(i, 5)] += 1
            features += feats
        features.append(float(len(game.bar_pieces[p])) / 2.)
        features.append(float(len(game.off_pieces[p])) / game.num_pieces[p])
    return features


def player(player, game):
    if player == game.players[0]:
        features = [1., 0.]
    else:
        features = [0., 1.]
    return features


def inner_board(game):
    count = 0
    for i in range(18, 24):
        count += 1 if len(game.grid[i]) > 0 else 0
    count /= 6
    return [count]


def pip_count(game):
    player = game.players[0].player
    count = 0
    for i in range(24):
        if len(game.grid[i]) > 0 and game.grid[i][0] == player:
            count += len(game.grid[i]) * (24 - i)
    return [count]


def opponent_inner_board(game):
    count = 0
    for i in range(6):
        count += 1 if len(game.grid[i]) > 0 else 0
    count /= 6
    return [count]


def opponent_inner_board_men(game):
    count = 0
    for i in range(6):
        count += len(game.grid[i])
    return [count]


def prime(game, prime_size=6):
    streak = 0
    longest_streak = 0
    last_player = None
    for i in range(24):
        if len(game.grid[i]) > 0:
            if game.grid[i][0] == last_player:
                streak += 1
            else:
                if streak > longest_streak:
                    longest_streak = streak
                streak = 1
        else:
            if streak > longest_streak:
                longest_streak = streak
            streak = 0
    r = 1 if streak >= prime_size else 0
    return [r]


def blot_exposure(game):
    possible_rolls = [(i, j) for i in range(1, 7) for j in range(1, 7)]

    game.reverse()
    can_hit = 0
    for roll in possible_rolls:
        moves = game.get_actions(roll, game.players[0], nodups=True)
        for move in moves:
            ateList = game.take_action(move, game.players[0].player)
            can_hit += 1 if sum(ateList) > 0 else 0
            game.undo_action(move, game.players[0].player)
    game.reverse()

    return can_hit / len(possible_rolls)


def blockade_strength(game):
    ...
