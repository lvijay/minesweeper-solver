#!/usr/bin/env python3

import cv2
import numpy as np

import sys
filename = sys.argv[1]

image = cv2.imread(filename)
mask = np.zeros(image.shape, dtype=np.uint8)
gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)[1]

cv2.imwrite('o_mask.png', gray)
cv2.imwrite('o_thresh.png', thresh)

def detect_grid(thresh):
    # Detect only grid
    contrs = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contrs = contrs[0] if len(contrs) == 2 else contrs[1]
    for c in contrs:
        area = cv2.contourArea(c)
        if area > 10000:
            cv2.drawContours(mask, [c], -1, (255,255,255), -1)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    combined = cv2.bitwise_and(mask, thresh)
    return combined

# Find horizontal lines
horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (45,1))
detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
cv2.imwrite('o_horiz.png', image)
contrs = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contrs = contrs[0] if len(contrs) == 2 else contrs[1]
for c in contrs:
    cv2.drawContours(image, [c], -1, (0,255,0), 2)

# Find vertical lines
vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,45))
detect_vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
contrs = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contrs = contrs[0] if len(contrs) == 2 else contrs[1]
for c in contrs:
    cv2.drawContours(image, [c], -1, (0,0,255), 2)

cv2.imwrite('o_image.png', image)
