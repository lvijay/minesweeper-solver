#!/usr/bin/env python3

from enum import Enum
from typing import (
    Dict,
    List,
    Iterator,
    Tuple,
    TypeVar,
)

import cv2
import numpy as np


Image = np.ndarray
T = TypeVar('T')
Pair = Tuple[T, T]


def image_read(filename, mode=cv2.IMREAD_ANYCOLOR) -> Image:
    image = cv2.imread(filename, mode)
    if image is None:
        raise FileNotFoundError(f'{filename} not found')
    return image


class Cell(Enum):
    C0 = "0"
    C1 = "1"
    C2 = "2"
    C3 = "3"
    C4 = "4"
    C5 = "5"
    C6 = "6"
    C7 = "7"
    C8 = "8"
    UNOPENED = "UNOPENED"
    FLAG = "FLAG"


class FindImage:
    IMAGES = {
        "0": image_read("find_j_0.png"),
        "1": image_read("find_j_1.png"),
        "2": image_read("find_j_2.png"),
        "3": image_read("find_j_3.png"),
        "4": image_read("find_j_4.png"),
        "5": image_read("find_j_5.png"),
        "6": image_read("find_j_6.png"),
        "7": image_read("find_j_7.png"),
        "8": image_read("find_j_8.png"),
        "MINE": image_read("find_mine.png"),
        "EXPLODED": image_read("find_exploded.png"),
        "FINISHED": image_read("find_finished.png"),
        "FLAG": image_read("find_flag.png"),
        "UNOPENED.MIDDLE": image_read("find_j_uo.png"),
        "UNOPENED.NE": image_read("find_j_ne.png"),
        "UNOPENED.NW": image_read("find_j_nw.png"),
        "UNOPENED.SE": image_read("find_j_se.png"),
        "UNOPENED.SW": image_read("find_j_sw.png"),
    }

    CELL_VALUES = {
        "C0": [198, 198, 198],
        "C1": [245, 0, 1],
        "C2": [34, 126, 56],
        "C3": [0, 0, 255],
        "C4": [122, 0, 1],
        "C5": [12, 20, 117],
        "C6": [127, 126, 56],
        "C7": [0, 0, 0],
        "C8": [128, 128, 128],
    }

    @staticmethod
    def get(name) -> Image:
        return FindImage.IMAGES[name]

    @staticmethod
    def is_cell_zero(image: Image) -> bool:
        return (FindImage.get("0")[0][0] == image).all()

    def __init__(self, threshold:float=0.99):
        self.__threshold: float = threshold

    @property
    def threshold(self) -> float:
        return self.__threshold

    def get_matches(self, image, template, name) -> Pair[np.ndarray]:
        h, w = template.shape[:2]
        match = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.asarray(match >= self.threshold).nonzero()
        if len(ys) == 0 or len(xs) == 0:
            raise SubImageNotFoundError(name)
        return xs, ys

    def get_unopened_corner(self, image, corner) -> Tuple[
            Image, np.ndarray, np.ndarray
    ]:
        template = FindImage.get(f"UNOPENED.{corner}")
        return template, *self.get_matches(image, template, corner)

    def is_game_ended(self, image) -> bool:
        "Returns True if the game is over; False otherwise."
        exploded = FindImage.get("EXPLODED")
        finished = FindImage.get("FINISHED")
        try:
            self.get_matches(image, exploded, "exploded") # a mine has exploded
            self.get_matches(image, finished, "finished") # the game has ended
            return True
        except SubImageNotFoundError:
            return False

    def get_new_board(self, image):
        img_ne, ne_x, ne_y = self.get_unopened_corner(image, "NE")
        img_nw, nw_x, nw_y = self.get_unopened_corner(image, "NW")
        img_se, se_x, se_y = self.get_unopened_corner(image, "SE")
        img_sw, sw_x, sw_y = self.get_unopened_corner(image, "SW")
        cell = FindImage.get("UNOPENED.MIDDLE")
        width_extra, height_extra = 5, 5  # FIXME hardcoding
        height, width = cell.shape[:2]
        width, height = min(width, height), min(width, height)
        nw_x, nw_y = nw_x[0] + width_extra, nw_y[0] + height_extra
        ne_x, ne_y = ne_x[0], ne_y[0]
        sw_x, sw_y = sw_x[0], sw_y[0]
        se_x, se_y = se_x[0], se_y[0]
        board_width = ne_x - nw_x + width
        board_height = se_y - nw_y + height
        colors = iter(((255, 0, 255), (0, 255, 0), (0, 0, 255), (255, 255, 0)))
        for cx, cy in ((nw_x, nw_y), (ne_x, ne_y), (sw_x, sw_y), (se_x, se_y)):
            cv2.rectangle(
                image, (cx, cy), (cx + width, cy + height), next(colors), 1
            )
        cv2.imwrite("o_out.png", image)
        return Board((nw_x, nw_y), (board_width, board_height), (width, height))

    def identify_cell(cell: Image) -> Cell:
        pass


class SubImageNotFoundError(Exception):
    def __init__(self, name=""):
        super().__init__(f"Did not find {name}")


class Board:
    def __init__(self, nwxy, board_dims, cell_dims=(48, 48)):
        self.__nwx, self.__nwy = nwxy
        self.__cellwidth = cell_dims[0]
        self.__cellheight = cell_dims[1]
        self.__boardwidth = board_dims[0]
        self.__boardheight = board_dims[1]
        self.__m = round(self.__boardwidth / self.__cellwidth)
        self.__n = round(self.__boardheight / self.__cellheight)

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

    @property
    def width(self) -> int:
        return self.__boardwidth

    @property
    def height(self) -> int:
        return self.__boardheight

    def cell_image(self, image, i, j) -> Image:
        if i >= self.m or j >= self.n:
            raise IndexError("Bounds exceeded")
        slicex, slicey = self.cell_dims(i, j)
        return image[slicex, slicey]

    def cell_dims(self, i, j) -> Pair[int]:
        x, y = self.nwx, self.nwy
        w, h = self.__cellwidth, self.__cellheight
        xi, yj = x + (i * w), y + (j * h)
        xi1, yj1 = xi + w, yj + h
        return slice(yj, yj1), slice(xi, xi1)

    def cells(self, image) -> Iterator[Tuple[int, int, Image]]:
        yield from (
            (i, j, self.cell_image(image, i, j))
            for i in range(self.m)
            for j in range(self.n)
        )

    def __str__(self) -> str:
        v = f"""Board<
cells    : {self.m}x{self.n}
dims     : {self.width}x{self.height}
cell_dims: {self.__cellwidth}x{self.__cellheight}
>"""
        return v


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    threshold = sys.argv[2] if len(sys.argv) >= 3 else '0.99'

    image = image_read(filename)
    finder = FindImage(float(threshold))

    if finder.is_game_ended(image):
        print("game over")
        exit(0)
        pass

    board = finder.get_new_board(image)
    print(board)
    images = [image_read(f'j_minebeg_0{i}.png') for i in '01234']
    for ic, image in enumerate(images):
        for i, j, cell in board.cells(image):
            cv2.imwrite(f"o_{ic}_{i}-{j}.png", board.cell_image(image, i, j))
