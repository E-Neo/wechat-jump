import subprocess
import io
import math
import time
from PIL import Image, ImageFilter


def get_screen():
    t = subprocess.run("adb shell screencap -p | sed 's/\r$//'",
                       stdout=subprocess.PIPE, shell=True)
    img = Image.open(io.BytesIO(t.stdout))
    return img


def jump(duration):
    subprocess.run("adb shell input swipe 0 0 0 0 " + str(duration),
                   shell=True)


def find_i(img):
    w, h = img.size
    pixel = img.load()
    for i in range(0, w):
        for j in reversed(range(0, h)):
            r, g, b, a = pixel[i, j]
            if r in range(40, 50)\
               and g in range(40, 50)\
               and b in range(70, 80):
                return i + 25, j


def process(img):
    img = img.convert('L').filter(ImageFilter.CONTOUR)
    threshold = 230
    img = img.point(lambda x: 0 if x < threshold else 255, mode='1')
    return img


def find_d_top(pixel, img_size):
    w, h = img_size
    for j in range(300, h):
        for i in range(20, w - 20):
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
        if check_right(pixel, i, j):
            i = i + 1
        elif check_down(pixel, i, j):
            j = j + 1
        else:
            while pixel[i, j] != 0:
                i = i - 1
            k = j
            while pixel[i, k] == 0:
                k = k + 1
            return i, (j + k) >> 1


def find_d(img):
    pixel = process(img).load()
    d_top = find_d_top(pixel, img.size)
    d_right = find_d_right(pixel, img.size, d_top)
    return d_top[0], d_right[1]


def calc_duration(img):
    i = find_i(img)
    d = find_d(img)
    distance = math.sqrt((i[0] - d[0])**2 + (i[1] - d[1])**2)
    return int(60 / 29 * distance)


def step():
    img = get_screen()
    duration = calc_duration(img)
    jump(duration)


def auto():
    while True:
        step()
        time.sleep(3)
