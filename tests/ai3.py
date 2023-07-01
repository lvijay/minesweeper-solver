#!/usr/bin/env python3

import cv2
import numpy as np

import sys
filename = sys.argv[1]

image = cv2.imread(filename)
mask = np.zeros(image.shape, dtype=np.uint8)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
cv2.imwrite("o_gray.png", gray)
ret, thresh = cv2.threshold(
    gray, 127, 255, cv2.THRESH_BINARY)
cv2.imwrite('o_thresh127.png', thresh)
thresh = cv2.threshold(
    gray, 0, 255, cv2.THRESH_BINARY)[1]
cv2.imwrite('o_thresh.png', thresh)

# Detect only grid
contrs, hierarchy = cv2.findContours(
    thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

cv2.drawContours(image, contrs, -1, (0, 255, 0), 2, cv2.LINE_AA)
cv2.imwrite('o_cdraw.png', image)

#print(f"contours = {contrs}")
print(f"len(hierarchy) = {len(hierarchy)}")
print(f"hierarchy = {hierarchy}")

contrs = contrs[0] if len(contrs) == 2 else contrs[1]
for c in contrs:
    area = cv2.contourArea(c)
    if area > 10000:
        cv2.drawContours(mask, [c], -1, (255,255,255), -1)
mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
combined = cv2.bitwise_and(mask, thresh)
