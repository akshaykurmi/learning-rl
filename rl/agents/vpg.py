import numpy as np
import tensorflow as tf

from rl.replay_buffer import OnePassReplayBuffer, ReplayField, EpisodeReturn
from rl.utils import GradientAccumulator, MeanAccumulator, tf_standardize


class VPG:
    def __init__(self, env, policy_fn, lr, replay_buffer_size, policy_update_batch_size):
        self.env = env
        self.policy = policy_fn()
        self.policy_update_batch_size = policy_update_batch_size

        self.replay_buffer = OnePassReplayBuffer(
            buffer_size=replay_buffer_size,
            store_fields=[
                ReplayField('observation', shape=self.env.observation_space.shape,
                            dtype=self.env.observation_space.dtype),
                ReplayField('action', shape=self.env.action_space.shape,
                            dtype=self.env.action_space.dtype),
                ReplayField('reward'),
                ReplayField('done', dtype=np.bool),
            ],
            compute_fields=[
                EpisodeReturn()
            ],
        )
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=lr)

    def variables_to_checkpoint(self):
        return {'policy': self.policy, 'optimizer': self.optimizer}

    def step(self, previous_transition=None, training=False):
        observation = previous_transition['observation_next'] if previous_transition else self.env.reset()
        action = self.policy.sample(tf.expand_dims(observation, axis=0)).numpy()[0]
        observation_next, reward, done, _ = self.env.step(action)
        transition = {'observation': observation, 'observation_next': observation_next,
                      'action': action, 'reward': reward, 'done': done}
        if training:
            self.replay_buffer.store_transition(transition)
        return transition

    def update(self):
        dataset = self.replay_buffer.as_dataset(self.policy_update_batch_size)
        result = {
            'policy_loss': self._update_policy(dataset),
        }
        self.replay_buffer.purge()
        return result

    def _update_policy(self, dataset):
        gradient_acc = GradientAccumulator()
        loss_acc = MeanAccumulator()
        for data in dataset:
            gradients, loss = self._update_policy_step(data)
            gradient_acc.add(gradients, tf.size(loss))
            loss_acc.add(loss)
        self.optimizer.apply_gradients(zip(gradient_acc.gradients(), self.policy.trainable_variables))
        return loss_acc.value()

    @tf.function(experimental_relax_shapes=True)
    def _update_policy_step(self, data):
        observation, action, episode_return = data['observation'], data['action'], data['episode_return']
        episode_return = tf_standardize(episode_return)
        with tf.GradientTape() as tape:
            log_probs = self.policy.log_prob(observation, action)
            loss = -(log_probs * episode_return)
            gradients = tape.gradient(loss, self.policy.trainable_variables)
        return gradients, loss
