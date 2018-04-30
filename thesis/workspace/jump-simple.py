import subprocess
import io
import os
import sys
import math
import time
import random
from PIL import Image, ImageFilter, ImageDraw


def get_screen():
    t = subprocess.run("adb shell screencap -p | sed 's/\r$//'",
                       stdout=subprocess.PIPE, shell=True)
    img = Image.open(io.BytesIO(t.stdout))
    return img


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


def debug_step(k=2, directory='debug', count=0):
    img = get_screen()
    p_img = process(img).convert('RGB')
    p_img_draw = ImageDraw.Draw(p_img)
    i = find_i(img)
    pixel = process(img).load()
    d_top = find_d_top(pixel, img.size, i)
    d_right = find_d_right(pixel, img.size, d_top)
    d = (d_top[0], d_right[1])
    r = 10
    p_img_draw.ellipse([i[0]-r, i[1]-r, i[0]+r, i[1]+r],
                       fill=(0, 0, 255), outline=(0, 0, 0))
    p_img_draw.ellipse([d[0]-r, d[1]-r, d[0]+r, d[1]+r],
                       fill=(255, 0, 0), outline=(0, 0, 0))
    p_img_draw.ellipse([d_top[0]-r, d_top[1]-r,
                        d_top[0]+r, d_top[1]+r],
                       fill=(0, 255, 0), outline=(0, 0, 0))
    p_img_draw.ellipse([d_right[0]-r, d_right[1]-r,
                        d_right[0]+r, d_right[1]+r],
                       fill=(0, 255, 0), outline=(0, 0, 0))
    distance = math.sqrt((i[0] - d[0])**2 + (i[1] - d[1])**2)
    duration = int(k * distance)
    img.save(os.path.join(directory,
                          'img{:04d}_{:04d}.png'.format(count, duration)))
    p_img.save(os.path.join(directory, 'p_img{:04d}.png'.format(count)))
    jump(duration)


def main():
    directory, count = sys.argv[1], int(sys.argv[2])
    while True:
        debug_step(k=2.05, directory=directory,
                   count=count)
        if random.randrange(0, 5) < 1:
            time.sleep(random.randrange(11, 51) / 10)
        else:
            time.sleep(random.randrange(11, 15) / 10)
        count += 1


if __name__ == '__main__':
    main()
