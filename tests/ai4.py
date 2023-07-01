#!/usr/bin/env python3

from collections import defaultdict
from itertools import count, cycle
from random import randrange

import cv2
import numpy as np

import sys

filename = sys.argv[1]
image = cv2.imread(filename)

gray = cv2.cvtColor(image,cv2.COLOR_BGRA2GRAY)
canny = cv2.Canny(gray, 44, 47, apertureSize = 3)
cv2.imwrite('o_canny.png', canny)
edges = cv2.dilate(canny, np.ones((6, 6), np.uint8), iterations=1)
cv2.imwrite('o_dilate2.png', edges)
edges = cv2.dilate(edges, np.ones((1, 1), np.uint8), iterations=4)
cv2.imwrite('o_dilate.png',edges)

contours, hierarchyT = cv2.findContours(
    edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
hierarchy = hierarchyT[0]

parent_counter = defaultdict(lambda: 0)
## find the most common parent
for _, _, child, parent in hierarchy:
    if parent == -1: continue
    if child != -1: continue
    parent_counter[parent] += 1

many_children = [(k, v) for k, v in parent_counter.items() if v > 20]

parent_areas = {k: [] for k, _ in many_children}
parent_contours = {p: [] for p, _ in many_children}
for c, (nxt, prv, first_child, parent) in zip(contours, hierarchy):
    if parent in parent_areas:
        parent_areas[parent].append(cv2.contourArea(c))
        parent_contours[parent].append(c)

# find with the same parent that are closest in area to each other
std_parent_len = sorted([
    (np.std(area), p, len(area))
    for p, area in parent_areas.items()
])

colors = cycle(
    ((randrange(100, 256)), (randrange(0, 256)), (randrange(0, 256)))
    for _ in count(0))

for (parent, child_contours), color in zip(parent_contours.items(), colors):
    b, g, r = color
    print(f'color = ({r}, {g}, {b}); children = {len(child_contours)}')
    cv2.drawContours(image, child_contours, -1, color, 2, cv2.LINE_AA)

cv2.imwrite('o_cdraw.png', image)

exit()

found = 0
for c, h in zip(contours, hierarchy):
    nxt, prv, first_child, parent = h
    area = cv2.contourArea(c)
    if (parent != -1
            and first_child == -1
            and area > 1000 and area < 1600):
        cv2.drawContours(image, [c], -1, next(color), 2, cv2.LINE_AA)
        found += 1
        contour_str = str(c).replace("\n", " ").replace("  ", " ")
        hierarc_str = str(h).replace("\n", " ").replace("  ", " ")
        #print(f"contour = {contour_str}")
        parent_area = cv2.contourArea(contours[parent])
        print(f"area    = {area}, parent_area = {parent_area}")
        print(f"hierarc = {hierarc_str}")

print(f"total contours = {len(contours)}")
print(f"found contours = {found}")
cv2.imwrite('o_cdraw.png', image)
