#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Neural Fitted Q Iteration (NFQ)

A significant consideration when working in continuous spaces is how to
represent the value function. This agent uses a neural network as the solution.

Based on:
http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.67.8356&rep=rep1&type=pdf

The basic idea underlying NFQ is that instead of updating the neural value
function on-line, which can lead to slow learning/divergence, experiences are
collected and the update is performed off-line.

x:-0.846563-0.995918
dx:-2.056612-47.288549
angle:-3.139824-3.140876
dangle:-11.219148-13.838803
"""

import random
import math
import parameters
from sknn.mlp import Regressor, Layer
import numpy as np
from ip_tools import timeit
import pickle
from collections import Counter


# Keeping fixed number of actions to control the cart.
ACTIONS = [-2, 2]
NUM_ACTIONS = len(ACTIONS)

DEBUG = False


class Agent:
    def __init__(self):
        print("Initializing NFQ agent!")
        self.alpha = parameters.ALPHA
        self.epsilon = parameters.EPSILON
        self.lmbda = parameters.LAMBDA  # Because lambda is a keyword.
        self.gamma = 0.9

        self.action = None
        self.state = None

        # sknn-Regressor for representing the value function.
        self.clf = Regressor(
            layers=[
                # 3 units because 3==round(len(inputs) + len(ouputs))
                #Layer("Sigmoid", units=5),
                #Layer("Sigmoid", units=5),
                Layer("Sigmoid", units=5),
                # Single unit linear output.
                Layer("Linear")],
            # This might be too high...
            learning_rate=self.alpha,
            n_iter=10)
        self.network_trained = False
        self.transitions = list()

        # Extra
        self.action_list = list()

    def init_trial(self, *meta):
        exp_num = meta[0]
        print("Sarsa agent initializing for experiment %d" % (exp_num + 1))

        # Reset collected reward stats for the trial.
        self.episode_rewards = []
        self.cum_episode_reward = 0
        try:
            with open("simple_nfq_clf.save", "rb") as f:
                self.clf = pickle.load(f)
            self.network_trained = True
        except:
            print("Can't load neural network.")

    def init_episode(self, *meta):
        _, x, angle, dx, dangle, _ = meta

        # Make an action and save the state and action.
        self.state = [x, angle, dx, dangle]
        self.action = self.egreedy(self.state)

        # Reset episode reward.
        self.cum_episode_reward = 0
        self.action_list = list()

        return ACTIONS[self.action]

    def egreedy(self, state):
        # ε-exploration.
        # If the network isn't trained, then just randomly explore.
        if random.random() < self.epsilon or not self.network_trained:
            return random.randint(0, NUM_ACTIONS - 1)

        # ε-exploitation.
        candidates = [self.state + [a - 0.5] for a in range(NUM_ACTIONS)]
        #candidates = [[self.state[0]] + [a-0.5] for a in range(NUM_ACTIONS)]
        q_values = self.clf.predict(np.array(candidates))
        if DEBUG:
            print(candidates,)
            print(q_values)
            raw_input()
        lowest = [i for i, v in enumerate(q_values)
                  if v < min(q_values) + 0.1]

        # Return the minimum cost action.
        return random.choice(lowest)

    def get_action(self, x, angle, dx, dangle, edge):
        """Main function called from the simulator to run episode."""
        # Track reward.
        #reward = -(angle)**2
        reward = -x**2
        self.cum_episode_reward += reward

        # Determine action.
        action_index = self.agent_step([x, angle, dx, dangle])
        self.action_list.append(action_index)

        return ACTIONS[action_index]

    def agent_step(self, state):
        # Record transition for last action.
        self.transitions.append([self.state, self.action, state])

        # Save current state and action, while determining the next action.
        self.state = state
        self.action = self.egreedy(state)

        return self.action

    def end_episode(self, *meta):
        self.episode_rewards.append(self.cum_episode_reward)
        print("ep_reward: %d, transitions: %d" %
             (self.cum_episode_reward, len(self.transitions)))
        print(Counter(self.action_list))

        self.train_nfq()
        self.network_trained = True

        # Save the network.
        with open("simple_nfq_clf.save", "wb") as f:
            pickle.dump(self.clf, f)

    def end_trial(self, *meta):
        print(self.episode_rewards)

    @timeit
    def train_nfq(self):
        """"""
        #with open("transitions.p", "wb") as f:
        #    pickle.dump(self.transitions, f)
        # Generate the training set from the set of transitions.
        X = np.array([[x, angle, dx, dangle, a-0.5]
                      for [x, angle, dx, dangle], a, _sp in self.transitions])
        y = list()
        for _s, _a, sp in self.transitions:
            # Regulator state: targets - within .03 of 0.
            if sp[0]**2 < 0.001:
                y.append(0)

            # Regulator state: avoid - past 0.8 from 0.
            elif sp[0]**2 > 0.64:
                y.append(10)

            # Other states.
            else:
                if self.network_trained:
                    y.append(
                        min(self.clf.predict(np.array(
                            [sp + [a] for a in [-0.5, 0.5]]))) * self.gamma)
                else:
                    y.append(sp[0]**2)
        y = np.array(y)

        # Train the mlp.
        self.clf.fit(X, y)
