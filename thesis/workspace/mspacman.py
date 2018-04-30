import gym
import numpy as np
from collections import deque
from keras.models import Sequential
from keras.layers import Dense, Conv2D, Flatten
from keras.optimizers import Adam


def preprocess_observation(obs):
    mspacman_color = 210 + 164 + 74
    img = obs[1:176:2, ::2]  # crop and downsize
    img = img.sum(axis=2)  # to greyscale
    img[img == mspacman_color] = 0  # Improve contrast
    img = (img // 3 - 128).astype(np.int8)  # normalize from -128 to 127
    return img.reshape(1, 88, 80, 1)


class Agent:
    def __init__(self):
        self.observation_shape = (88, 80, 1)
        self.action_size = 9
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()

    def _build_model(self):
        model = Sequential()
        model.add(Conv2D(32, (8, 8), strides=4, padding='same',
                         activation='relu',
                         input_shape=self.observation_shape))
        model.add(Conv2D(64, (4, 4), strides=2, padding='same',
                         activation='relu'))
        model.add(Conv2D(64, (3, 3), strides=1, padding='same',
                         activation='relu'))
        model.add(Flatten())
        model.add(Dense(512, activation='relu'))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model

    def remember(self, observation, action, reward, next_observation, done):
        self.memory.append((observation, action, reward, next_observation,
                            done))

    def act(self, observation):
        if np.random.rand() <= self.epsilon:
            return np.random.randint(self.action_size)
        act_values = self.model.predict(observation)
        return np.argmax(act_values[0])

    def replay(self, batch_size):
        minibatch = [self.memory[i] for i in
                     np.random.choice(len(self.memory), batch_size,
                                      replace=False)]
        for observation, action, reward, next_observation, done in minibatch:
            target = reward
            if not done:
                target = reward + self.gamma *\
                         np.amax(self.model.predict(next_observation)[0])
            target_f = self.model.predict(observation)
            target_f[0][action] = target
            self.model.fit(observation, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def load(self, filepath):
        self.model.load_weights(filepath)

    def save(self, filepath):
        self.model.save_weights(filepath)


def main():
    skip_start = 85
    batch_size = 32
    episodes = 50000
    filepath = 'mspacman-dqn.h5'

    env = gym.make('MsPacman-v0')
    agent = Agent()
    try:
        agent.load(filepath)
    except Exception as e:
        print(e)
    for e in range(episodes):
        score = 0.0
        done = False
        obs = env.reset()
        for skip in range(skip_start):
            obs, reward, done, _ = env.step(0)
        while not done:
            p_obs = preprocess_observation(obs)
            action = agent.act(p_obs)
            next_obs, reward, done, _ = env.step(action)
            score += reward
            p_next_obs = preprocess_observation(next_obs)
            agent.remember(p_obs, action, reward, p_next_obs, done)
            obs = next_obs
        print('{}/{}, {:.0f}, {:.3f}'
              .format(e, episodes, score, agent.epsilon), flush=True)
        if len(agent.memory) > batch_size:
            agent.replay(batch_size)
        if e % 10 == 0:
            agent.save(filepath)
    env.close()


if __name__ == '__main__':
    main()
