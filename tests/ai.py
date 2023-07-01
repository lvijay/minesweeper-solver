#!/usr/bin/env python3

import cv2
import numpy as np

import sys

filename = sys.argv[1]
image = cv2.imread(filename)

gray = cv2.cvtColor(image,cv2.COLOR_BGRA2GRAY)
edges = cv2.Canny(gray, 40, 50, apertureSize = 7)
cv2.imwrite('o_canny.png',edges)
edges = cv2.dilate(edges, np.ones((4,4), np.uint8), iterations=1)
cv2.imwrite('o_dilate2.png',edges)
edges = cv2.dilate(edges, np.ones((1,1), np.uint8), iterations=4)
cv2.imwrite('o_dilate.png',edges)

exit()

lines = cv2.HoughLines(edges,1,np.pi/180,150)

if not lines.any():
    print('No lines were found')
    fail_here

if filter:
    rho_threshold = 15
    theta_threshold = 0.1
    # how many lines are similar to a given one
    similar_lines = {i : [] for i in range(len(lines))}
    for i in range(len(lines)):
        for j in range(len(lines)):
            if i == j:
                continue
            rho_i,theta_i = lines[i][0]
            rho_j,theta_j = lines[j][0]
            if abs(rho_i - rho_j) < rho_threshold and abs(theta_i - theta_j) < theta_threshold:
                similar_lines[i].append(j)
    # ordering the INDECES of the lines by how many are similar to them
    indices = [i for i in range(len(lines))]
    indices.sort(key=lambda x : len(similar_lines[x]))
    # line flags is the base for the filtering
    line_flags = len(lines)*[True]
    for i in range(len(lines) - 1):
        if not line_flags[indices[i]]: # if we already disregarded the ith element in the ordered list then we don't care (we will not delete anything based on it and we will never reconsider using this line again)
            continue
        for j in range(i + 1, len(lines)): # we are only considering those elements that had less similar line
            if not line_flags[indices[j]]: # and only if we have not disregarded them already
                continue
            rho_i,theta_i = lines[indices[i]][0]
            rho_j,theta_j = lines[indices[j]][0]
            if abs(rho_i - rho_j) < rho_threshold and abs(theta_i - theta_j) < theta_threshold:
                line_flags[indices[j]] = False # if it is similar and have not been disregarded yet then drop it now

filtered_lines = [line for i, line in enumerate(lines) if line_flags[i]]

for line in filtered_lines:
    rho,theta = line[0]
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 1000*(-b))
    y1 = int(y0 + 1000*(a))
    x2 = int(x0 - 1000*(-b))
    y2 = int(y0 - 1000*(a))
    hlines = cv2.line(image,(x1,y1),(x2,y2),(0,0,255),2)

cv2.imwrite('hough.png',hlines)
