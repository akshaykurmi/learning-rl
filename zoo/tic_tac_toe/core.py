from enum import Enum

import gym
import numpy as np

from rl.environments.two_player_game import TwoPlayerGame


class TicTacToe(TwoPlayerGame):
    GameStatus = Enum('GameStatus', 'PLAYER_1_WON, PLAYER_2_WON, DRAW, IN_PROGRESS')
    Players = Enum('GameStatus', {'PLAYER_1': 1, 'PLAYER_2': -1})

    def __init__(self):
        self.metadata = {'render.modes': ['human']}
        self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(3, 3), dtype=np.int8)
        self.action_space = gym.spaces.Discrete(9)
        self.state = np.zeros((3, 3), dtype=np.int8)
        self.turn = TicTacToe.Players.PLAYER_1

    def reset(self, canonical=True):
        self.state = np.zeros((3, 3), dtype=np.int8)
        return self.observation(canonical)

    def step(self, action, canonical=True):
        assert action in self.valid_actions(canonical)
        col, row = action % 3, action // 3
        self.state[row, col] = self.turn.value
        score = self.score(canonical)
        is_over = self.is_over()
        self.turn = TicTacToe.Players(-self.turn.value)
        observation = self.observation(canonical)
        info = {}
        return observation, score, is_over, info

    def valid_actions(self, canonical=True):
        actions = np.argwhere(self.state == 0)
        actions = actions[:, 0] * 3 + actions[:, 1]
        return actions

    def observation(self, canonical=True):
        if canonical and self.turn == TicTacToe.Players.PLAYER_2:
            return self.state * -1
        return self.state.copy()

    def score(self, canonical=True):
        status = self._game_status(self.state)
        if status in {TicTacToe.GameStatus.DRAW, TicTacToe.GameStatus.IN_PROGRESS}:
            return 0
        win_status = {
            TicTacToe.GameStatus.PLAYER_1_WON: 1,
            TicTacToe.GameStatus.PLAYER_2_WON: -1,
        }[status]
        if canonical and self.turn == TicTacToe.Players.PLAYER_2:
            return -win_status
        return win_status

    def is_over(self):
        status = self._game_status(self.state)
        return status != TicTacToe.GameStatus.IN_PROGRESS

    def render(self, mode='human'):
        symbols = {0: ' ', 1: 'X', -1: 'O'}
        status = self._game_status(self.state)
        result = {
            TicTacToe.GameStatus.IN_PROGRESS: f'TURN : {symbols[self.turn.value]}',
            TicTacToe.GameStatus.DRAW: f'Draw!',
            TicTacToe.GameStatus.PLAYER_1_WON: f'X Won!',
            TicTacToe.GameStatus.PLAYER_2_WON: f'O Won!',
        }[status]
        result = result.center(13)
        result += '\n┌' + ('───┬' * 3)[:-1] + '┐\n'
        for i, row in enumerate(self.state):
            for v in row:
                result += f'| {symbols[v]} '
            result += '|\n'
            if i < 2:
                result += '├' + ('───┼' * 3)[:-1] + '┤\n'
        result += '└' + ('───┴' * 3)[:-1] + '┘\n'
        return result

    @staticmethod
    def _game_status(state):
        def unique_elements_along_positions():
            yield np.unique(np.diagonal(state))
            yield np.unique(np.diagonal(np.fliplr(state)))
            for i in range(3):
                yield np.unique(state[:, i])
                yield np.unique(state[i, :])

        for elements in unique_elements_along_positions():
            if elements.size == 1:
                if elements[0] == 1:
                    return TicTacToe.GameStatus.PLAYER_1_WON
                if elements[0] == -1:
                    return TicTacToe.GameStatus.PLAYER_2_WON
        if np.count_nonzero(state) == 9:
            return TicTacToe.GameStatus.DRAW
        return TicTacToe.GameStatus.IN_PROGRESS