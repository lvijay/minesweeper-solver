#!/usr/bin/env python3

## search for specific images in the given screenshot

from random import randrange
from itertools import chain, count, cycle
import sys

import cv2
import numpy as np

filename = sys.argv[1]
search_filename = sys.argv[2]

image = cv2.imread(filename, cv2.IMREAD_ANYCOLOR)
#img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#cv2.imwrite("o_gray.png", img_gray)
template = cv2.imread(search_filename, cv2.IMREAD_ANYCOLOR)
w, h = template.shape[:2]

res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
threshold = 0.99
#loc = np.where(res >= threshold)
loc_y, loc_x = np.asarray(res >= threshold).nonzero()

if len(loc_x) == 0:
    print(f"sub-image not found in larger image")
    exit(1)

print(f"loc_x = {len(loc_x)} {len(loc_y)}")
print(f"loc_x = {loc_x}")

colors = cycle(
    ((randrange(100, 256)), (randrange(0, 256)), (randrange(0, 256)))
    for _ in count(0))

for i, color, x, y in zip(count(1), colors, loc_x, loc_y):
    b, g, r = color
    print(f'{i} color=({r}, {g}, {b}); dims={(x, y)},{(w, h)}')
    if i > 500: break
    cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)

cv2.imwrite('o_result.png', image)
