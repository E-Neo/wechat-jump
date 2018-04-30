import io
import os
import math
import random
import subprocess
import numpy as np
from PIL import Image, ImageFilter
from keras.models import Sequential
from keras.layers import Dense, Conv2D, Flatten
from keras.optimizers import Adam


def get_screen():
    t = subprocess.run("adb shell screencap -p | sed 's/\r$//'",
                       stdout=subprocess.PIPE, shell=True)
    img = Image.open(io.BytesIO(t.stdout))
    return img


def game_over_p(img):
    return img.getpixel((122, 1070)) == (4, 154, 255, 255)\
        and img.getpixel((130, 1070)) == (243, 243, 243, 255)\
        and img.getpixel((138, 1070)) == (4, 154, 255, 255)


def jump(duration):
    x = random.randrange(270, 500)
    y = random.randrange(900, 1100)
    subprocess.run("adb shell input swipe {} {} {} {} {}"
                   .format(x, y,
                           x + random.randrange(-2, 3),
                           y + random.randrange(-2, 3),
                           duration),
                   shell=True)


def find_i(img):
    w, h = img.size
    pixel = img.load()
    for i in range(75, w):
        for j in reversed(range(0, h)):
            r, g, b, a = pixel[i, j]
            if r in range(40, 50)\
               and g in range(40, 50)\
               and b in range(70, 80):
                return i + 25, j


def process(img):
    img = img.filter(ImageFilter.CONTOUR).convert('L')
    threshold = 230
    img = img.point(lambda x: 0 if x < threshold else 255, mode='1')
    return img


def find_d_top(pixel, img_size, i_pos):
    w, h = img_size
    l_bound, r_bound, mid = 20, w - 20, w >> 1
    if i_pos[0] < mid:
        l_bound = mid
    else:
        r_bound = mid
    for j in range(300, h):
        for i in range(l_bound, r_bound):
            if pixel[i, j] == 0:
                for k in range(i, w - 20):
                    if pixel[k, j] != 0:
                        return (i + k) >> 1, j


def find_d_right(pixel, img_size, d_top):
    def check_right(pixel, i, j, steps=5):
        for k in range(i, i + steps):
            if pixel[k, j] == 0:
                return True
        return False

    def check_down(pixel, i, j, steps=10):
        for k in range(j, j + steps):
            if pixel[i, k] == 0:
                return True
        return False

    w, h = img_size
    i, j = d_top
    while True:
        if i < w - 1 and check_right(pixel, i, j):
            i = i + 1
        elif j < h - 1 and check_down(pixel, i, j):
            j = j + 1
        else:
            while pixel[i, j] != 0:
                i = i - 1
            k = j
            while pixel[i, k] == 0:
                k = k + 1
            if k - j > 10:
                k = j + 2
            return i, (j + k) >> 1


def find_d(img, i_pos):
    pixel = process(img).load()
    d_top = find_d_top(pixel, img.size, i_pos)
    d_right = find_d_right(pixel, img.size, d_top)
    return d_top[0], d_right[1]


def calc_duration(img):
    i = find_i(img)
    d = find_d(img, i)
    distance = math.sqrt((i[0] - d[0])**2 + (i[1] - d[1])**2)
    return int(2.05 * distance)


def _get_img_duration(filepath):
    img = Image.open(filepath)
    duration = calc_duration(img)
    return img, duration


def _update_filenames(gamepath):  # gamepath ends with /
    for f in os.listdir(gamepath):
        if f[0] == 'i':
            img, duration = _get_img_duration(gamepath + f)
            os.rename(gamepath + f,
                      gamepath + f.replace('.', '_{:04d}.'.format(duration)))


def get_img_duration(filepath):
    img = Image.open(filepath)
    duration = int(filepath[-8:-4])
    return img, duration


def preprocess(img):
    img = img.crop((0, 400, 720, 1120))
    img = img.convert('L')
    img.thumbnail((64, 64))
    return img


def get_imgpaths(directory):
    imgpaths = []
    for f in os.listdir(directory):
        if f[0] == 'i':
            imgpaths.append(f)
    random.shuffle(imgpaths)
    return imgpaths


def build_model():
    model = Sequential()
    model.add(Conv2D(32, (8, 8), strides=4, padding='same',
                     activation='relu',
                     input_shape=(64, 64, 1)))
    model.add(Conv2D(64, (4, 4), strides=2, padding='same',
                     activation='relu'))
    model.add(Conv2D(64, (3, 3), strides=1, padding='same',
                     activation='relu'))
    model.add(Flatten())
    model.add(Dense(512, activation='relu'))
    model.add(Dense(1, activation='relu'))
    model.compile(loss='mse', optimizer=Adam())
    return model


def pretrain_model(model):
    games = ['00', '01', '02', '03', '04',
             '05', '06', '07', '08', '09']
    for game in games:
        imgpaths = get_imgpaths('debug/' + game)
        x, y = [], []
        for filename in imgpaths:
            img, duration = get_img_duration('debug/{}/{}'
                                             .format(game, filename))
            x.append(np.array(preprocess(img)).reshape(64, 64, 1))
            y.append(duration)
        model.fit(np.array(x), np.array(y), verbose=1)
    return model


def step(model):
    img = get_screen()
    obs = np.array(preprocess(img)).reshape(1, 64, 64, 1)
    duration = int(model.predict(obs)[0][0])
    duration_ref = calc_duration(img)
    print(duration_ref, duration)
    return img, obs, duration, duration_ref


def main():
    modelpath = 'jump-dqn.h5'
    model = build_model()
    try:
        model.load_weights(modelpath)
    except Exception as e:
        model = pretrain_model(model)
        model.save_weights(modelpath)
    games = ['10', '11']
    for game in games:
        imgpaths = get_imgpaths('debug/' + game)
        x, y = [], []
        for filename in imgpaths:
            img, duration = get_img_duration('debug/{}/{}'
                                             .format(game, filename))
            x.append(np.array(preprocess(img)).reshape(64, 64, 1))
            y.append(duration)
        model.predict(np.array(x))


if __name__ == '__main__':
    main()
