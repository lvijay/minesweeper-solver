#!/usr/bin/env python3

from typing import (
    Dict,
    List,
    Iterator,
    Tuple,
)

import cv2
import numpy as np


Image = np.ndarray


def image_read(filename, mode=cv2.IMREAD_ANYCOLOR) -> Image:
    return cv2.imread(filename, mode)


class FindImage:
    IMAGES = {
        "0.N": image_read("find_0n.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.S": image_read("find_0s.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.E": image_read("find_0e.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.W": image_read("find_0w.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.NE": image_read("find_0ne.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.NW": image_read("find_0nw.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.SE": image_read("find_0se.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.SW": image_read("find_0sw.png", cv2.IMREAD_REDUCED_COLOR_2),
        "0.MIDDLE": image_read("find_0.png", cv2.IMREAD_REDUCED_COLOR_2),
        "1": image_read("find_1.png", cv2.IMREAD_REDUCED_COLOR_2),
        "2": image_read("find_2.png", cv2.IMREAD_REDUCED_COLOR_2),
        "3": image_read("find_3.png", cv2.IMREAD_REDUCED_COLOR_2),
        "4": image_read("find_4.png", cv2.IMREAD_REDUCED_COLOR_2),
        "5": image_read("find_5.png", cv2.IMREAD_REDUCED_COLOR_2),
        "6": image_read("find_6.png", cv2.IMREAD_REDUCED_COLOR_2),
        "7": image_read("find_7.png", cv2.IMREAD_REDUCED_COLOR_2),
        "8": image_read("find_8.png", cv2.IMREAD_REDUCED_COLOR_2),
        "MINE": image_read("find_mine.png", cv2.IMREAD_REDUCED_COLOR_2),
        "EXPLODED": image_read("find_exploded.png", cv2.IMREAD_REDUCED_COLOR_2),
        "FINISHED": image_read("find_finished.png", cv2.IMREAD_REDUCED_COLOR_2),
        "FLAG": image_read("find_flag.png", cv2.IMREAD_REDUCED_COLOR_2),
        "UNOPENED.MIDDLE": image_read("find_unopened.png", cv2.IMREAD_REDUCED_COLOR_2),
        "UNOPENED.NE": image_read("find_unopened_ne.png", cv2.IMREAD_REDUCED_COLOR_2),
        "UNOPENED.NW": image_read("find_unopened_nw.png", cv2.IMREAD_REDUCED_COLOR_2),
        "UNOPENED.SE": image_read("find_unopened_se.png", cv2.IMREAD_REDUCED_COLOR_2),
        "UNOPENED.SW": image_read("find_unopened_sw.png", cv2.IMREAD_REDUCED_COLOR_2),
    }

    @staticmethod
    def get(name) -> Image:
        return FindImage.IMAGES[name]


class SubImageNotFoundError(Exception):
    def __init__(self, name=""):
        super().__init__(f"Did not find {name}")


def get_matches(image, template, name) -> Tuple[np.ndarray, np.ndarray]:
    h, w = template.shape[:2]
    match = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.99
    ys, xs = np.asarray(match >= threshold).nonzero()
    if len(ys) == 0 or len(xs) == 0:
        raise SubImageNotFoundError(name)
    return xs, ys


def is_game_ended(image) -> bool:
    "Returns True if the game is over; False otherwise."
    exploded = FindImage.get("EXPLODED")
    finished = FindImage.get("FINISHED")
    try:
        get_matches(image, exploded, "exploded")  # a mine has exploded
        get_matches(image, finished, "finished")  # the game has ended
        return True
    except SubImageNotFoundError:
        return False


def get_unopened_corner(image, corner) -> Tuple[Image, np.ndarray, np.ndarray]:
    template = FindImage.get(f"UNOPENED.{corner}")
    return template, *get_matches(image, template, corner)


class Board:
    def __init__(self, nwxy, board_dims, cell_dims=(48, 48)):
        self.__nwx, self.__nwy = nwxy
        self.__cellwidth = cell_dims[0]
        self.__cellheight = cell_dims[1]
        self.__boardwidth = board_dims[0]
        self.__boardheight = board_dims[1]
        self.__m = self.__boardwidth // self.__cellwidth
        self.__n = self.__boardheight // self.__cellheight

    @property
    def m(self) -> int:
        return self.__m

    @property
    def n(self) -> int:
        return self.__n

    @property
    def nwx(self) -> int:
        return self.__nwx

    @property
    def nwy(self) -> int:
        return self.__nwy

    def cell_image(self, image, i, j) -> Image:
        if i >= self.m or j >= self.n:
            raise IndexError("Bounds exceeded")
        x, y = self.nwx, self.nwy
        w, h = self.__cellwidth, self.__cellheight
        xi, yj = x + (i * w), y + (j * h)
        xi1, yj1 = xi + w, yj + w
        return image[yj:yj1, xi:xi1]

    def cells(self, image) -> Iterator[Image]:
        yield from (
            self.cell_image(image, i, j)
            for i in range(self.m)
            for j in range(self.n)
        )

#def sqxy(i, j):
#    global image, dims
#    x = dims["nw_x"]
#    y = dims["nw_y"]
#    w, h = 48, 48
#    xi, yj = x + i * w, y + j * h
#    xi1, yj1 = xi + w, yj + h
#    return image[yj:yj1, xi:xi1]

def get_new_board(image):
    img_ne, ne_x, ne_y = get_unopened_corner(image, "NE")
    img_nw, nw_x, nw_y = get_unopened_corner(image, "NW")
    img_se, se_x, se_y = get_unopened_corner(image, "SE")
    img_sw, sw_x, sw_y = get_unopened_corner(image, "SW")
    width_extra, height_extra = 5, 5  # FIXME hardcoding
    height, width = img_ne.shape[:2]
    width -= width_extra
    height -= height_extra
    nw_x, nw_y = nw_x[0] + width_extra, nw_y[0] + height_extra
    ne_x, ne_y = ne_x[0], ne_y[0] + height_extra
    sw_x, sw_y = sw_x[0] + width_extra, sw_y[0]
    se_x, se_y = se_x[0], se_y[0]
    board_width = ne_x - nw_x + width - width_extra
    board_height = se_y - ne_y + height - height_extra
    print(f"width, height = {width, height}")
    print(f"nw_xy = {nw_x, nw_y}")
    print(f"ne_xy = {ne_x, ne_y}")
    print(f"sw_xy = {sw_x, se_y}")
    print(f"se_xy = {se_x, se_y}")
    print(f"board_dims = {board_width, board_height}")
    colors = iter(((255, 0, 255), (0, 255, 0), (0, 0, 255), (255, 255, 0)))
    for cx, cy in ((nw_x, nw_y), (ne_x, ne_y), (sw_x, sw_y), (se_x, se_y)):
        cv2.rectangle(
            image, (cx, cy), (cx + width, cy + height), next(colors), 1
        )
    cv2.imwrite("o_out.png", image)
    return Board((nw_x, nw_y), (board_width, board_height))


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    image = image_read(filename)

    if is_game_ended(image):
        print("game over")
        exit(0)
        pass

    get_new_board(image)
