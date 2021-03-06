from enum import Enum
from functools import lru_cache

import gym
import numpy as np
import tensorflow as tf
from colr import color

from rl.environments.two_player_game import TwoPlayerGame


class Connect4(TwoPlayerGame):
    GameStatus = Enum('GameStatus', 'BLUE_WON, YELLOW_WON, DRAW, IN_PROGRESS')
    Players = Enum('GameStatus', {'BLUE': 1, 'YELLOW': -1})

    def __init__(self):
        self.metadata = {'render.modes': ['human']}
        self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(6, 7, 1), dtype=np.int8)
        self.action_space = gym.spaces.Discrete(7)
        self.state = np.zeros((6, 7), dtype=np.int8)
        self.turn = Connect4.Players.BLUE

    def reset(self):
        self.state = np.zeros((6, 7), dtype=np.int8)
        self.turn = Connect4.Players.BLUE

    def step(self, action):
        assert action in self.valid_actions()
        col = action
        row = 6 - np.count_nonzero(self.state[:, col]) - 1
        self.state[row, col] = self.turn.value
        self.turn = Connect4.Players(-self.turn.value)

    def valid_actions(self):
        actions = np.count_nonzero(self.state, axis=0)
        actions = np.argwhere(actions < 6).flatten()
        return actions

    def observation(self, canonical=True):
        if canonical:
            return self.state[..., None] * self.turn.value
        return self.state[..., None]

    def score(self):
        status = self._game_status(tuple(map(tuple, self.state)))
        if status in {Connect4.GameStatus.DRAW, Connect4.GameStatus.IN_PROGRESS}:
            return 0
        return {
            Connect4.GameStatus.BLUE_WON: 1,
            Connect4.GameStatus.YELLOW_WON: -1,
        }[status]

    def is_over(self):
        status = self._game_status(tuple(map(tuple, self.state)))
        return status != Connect4.GameStatus.IN_PROGRESS

    def render(self, mode='human'):
        symbols = {0: ' ', 1: color('●', fore='#8e86ff'), -1: color('●', fore='#cfff00')}
        turns = {1: 'BLUE', -1: 'YELLOW'}
        status = self._game_status(tuple(map(tuple, self.state)))
        result = {
            Connect4.GameStatus.IN_PROGRESS: f'TURN : {turns[self.turn.value]}',
            Connect4.GameStatus.DRAW: f'Draw!',
            Connect4.GameStatus.BLUE_WON: f'BLUE Won!',
            Connect4.GameStatus.YELLOW_WON: f'YELLOW Won!',
        }[status]
        result = result.center(29)
        result += '\n┌' + ('───┬' * 7)[:-1] + '┐\n'
        for i, row in enumerate(self.state):
            for v in row:
                result += f'| {symbols[v]} '
            result += '|\n'
            if i < 5:
                result += '├' + ('───┼' * 7)[:-1] + '┤\n'
        result += '└' + ('───┴' * 7)[:-1] + '┘\n'
        result += ''.join([f'  {i} ' for i in range(7)]) + '\n'
        return result

    @staticmethod
    @lru_cache(maxsize=1)
    def _game_status(state):
        def positions_to_check():
            indices = np.reshape(np.arange(6 * 7), (6, 7))
            for i in range(6):
                for j in range(4):
                    yield indices[i, j:j + 4]
            for j in range(7):
                for i in range(3):
                    yield indices[i:i + 4, j]
            for offset in range(-2, 4):
                diagonal = np.diag(indices, offset)
                for i in range(diagonal.size - 3):
                    yield diagonal[i:i + 4]
            for offset in range(-2, 4):
                diagonal = np.diag(np.fliplr(indices), offset)
                for i in range(diagonal.size - 3):
                    yield diagonal[i:i + 4]

        state = np.array(state)
        state = state.flatten()
        for positions in positions_to_check():
            total = np.sum(state[positions])
            if total == 4:
                return Connect4.GameStatus.BLUE_WON
            if total == -4:
                return Connect4.GameStatus.YELLOW_WON
        if np.count_nonzero(state) == 6 * 7:
            return Connect4.GameStatus.DRAW
        return Connect4.GameStatus.IN_PROGRESS


class PolicyAndValueFunctionNetwork(tf.keras.Model):
    def __init__(self, observation_shape, n_actions, l2):
        super().__init__()
        self.entry = tf.keras.layers.InputLayer(input_shape=observation_shape)
        self.conv1 = tf.keras.layers.Conv2D(16, (4, 4), activation='relu',
                                            kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.conv2 = tf.keras.layers.Conv2D(16, (2, 2), activation='relu',
                                            kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.flatten = tf.keras.layers.Flatten()
        self.dense1 = tf.keras.layers.Dense(32, 'relu', kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.dense_pi = tf.keras.layers.Dense(16, 'relu', kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.dense_v = tf.keras.layers.Dense(16, 'relu', kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.pi = tf.keras.layers.Dense(n_actions, 'softmax', kernel_regularizer=tf.keras.regularizers.L2(l2))
        self.v = tf.keras.layers.Dense(1, 'tanh', kernel_regularizer=tf.keras.regularizers.L2(l2))

    def get_config(self):
        super().get_config()

    def call(self, observations, **kwargs):
        x = self.entry(tf.cast(observations, tf.float32))
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.flatten(x)
        x = self.dense1(x)
        pi = self.dense_pi(x)
        v = self.dense_v(x)
        pi = self.pi(pi)
        v = self.v(v)
        return pi, v
