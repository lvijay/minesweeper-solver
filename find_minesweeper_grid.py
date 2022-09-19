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

    @staticmethod
    def to_cell(val: int):
        if val == 0: return Cell.UNOPENED
        if val >= 1 and val <= 8: return Cell.__members__[f"C{val}"]
        return Cell.C0


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
        "EXPLODED": image_read("find_j_exploded.png"),
        "FINISHED": image_read("find_j_finished.png"),
        "UNOPENED.MIDDLE": image_read("find_j_uo.png"),
        "UNOPENED.NE": image_read("find_j_ne.png"),
        "UNOPENED.NW": image_read("find_j_nw.png"),
        "UNOPENED.SE": image_read("find_j_se.png"),
        "UNOPENED.SW": image_read("find_j_sw.png"),
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
            return True
        except SubImageNotFoundError:
            try:
                self.get_matches(image, finished, "finished") # the game has ended
                return True
            except SubImageNotFoundError:
                return False
        return False

    def get_new_board(self, image):
        img_ne, ne_x, ne_y = self.get_unopened_corner(image, "NE")
        img_nw, nw_x, nw_y = self.get_unopened_corner(image, "NW")
        img_se, se_x, se_y = self.get_unopened_corner(image, "SE")
        img_sw, sw_x, sw_y = self.get_unopened_corner(image, "SW")
        width_extra, height_extra = 5, 5  # FIXME hardcoding
        width, height = 24, 24  # FIXME hardcoding
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

    def identify_cell(self, cell: Image) -> Cell:
        domain = list(range(9))
        ideals = [FindImage.get(str(i)) for i in domain]
        ideals[0] = FindImage.get("UNOPENED.MIDDLE")
        def matches(cell, ideals, idx):
            try:
                return self.get_matches(cell, ideals[idx], f'{idx}')
            except Exception:
                return False
        match_vals = [
            i
            for i in domain
            if matches(cell, ideals, i) is not False
        ]
        if match_vals:
            val = match_vals[-1] # preferentially take the last match
            return Cell.to_cell(val)
        return Cell.C0


class SubImageNotFoundError(Exception):
    def __init__(self, name=""):
        super().__init__(f"Did not find {name}")


class Board:
    def __init__(self, nwrowcol, board_dims, cell_dims):
        self.__nw_row, self.__nw_col = nwrowcol
        self.__cellwidth = cell_dims[0]
        self.__cellheight = cell_dims[1]
        self.__boardwidth = board_dims[0]
        self.__boardheight = board_dims[1]
        self.__rows = round(self.__boardheight / self.__cellheight)
        self.__cols = round(self.__boardwidth / self.__cellwidth)

    @property
    def rows(self) -> int:
        return self.__rows

    @property
    def cols(self) -> int:
        return self.__cols

    @property
    def nw_row(self) -> int: return self.__nw_row

    @property
    def nw_col(self) -> int: return self.__nw_col

    @property
    def width(self) -> int:
        return self.__boardwidth

    @property
    def height(self) -> int:
        return self.__boardheight

    @property
    def cellwidth(self) -> int: return self.__cellwidth

    @property
    def cellheight(self) -> int: return self.__cellheight

    def cell_dims(self, row, col) -> Pair[int]:
        x, y = self.nw_row, self.nw_col
        h, w = self.cellheight, self.cellwidth
        xstart, ystart = x + col * w, y + row * h
        xend, yend = xstart + w, ystart + h
        return slice(ystart, yend), slice(xstart, xend)

    def cell_image(self, image, row, col) -> Image:
        if row >= self.rows or col >= self.cols:
            raise IndexError("Bounds exceeded")
        slice_y, slice_x = self.cell_dims(row, col)
        return image[slice_y, slice_x]

    def cells(self, image) -> Iterator[Tuple[int, int, Image]]:
        yield from (
            (rowi, colj, self.cell_image(image, rowi, colj))
            for rowi in range(self.rows)
            for colj in range(self.cols)
        )

    def __str__(self) -> str:
        v = f"""Board<
cells    : {self.rows}x{self.cols}
dims     : {self.nw_row}x{self.nw_col}+{self.width}x{self.height}
cell_dims: {self.cellwidth}x{self.cellheight}
>"""
        return v


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    threshold = sys.argv[2] if len(sys.argv) >= 3 else '0.99'
    other_images = sys.argv[3:]

    image = image_read(filename)
    finder = FindImage(float(threshold))

    if finder.is_game_ended(image):
        print("game over")
        exit(0)
        pass

    board = finder.get_new_board(image)
    print(board)
    images = [image] + [image_read(imgfile) for imgfile in other_images]
    for ic, img in enumerate(images):
        for i, j, cell in board.cells(img):
            try:
                cv2.imwrite(f"o_{ic}_{i:02d}-{j:02d}.png", cell)
            except Exception as e:
                print(f"error at ic,i,j={ic},{i},{j}")
                print(e)
                break

    for ic, img in enumerate(images):
        print("\n".join(
            f"{i,j}_{finder.identify_cell(cell)}"
            for i, j, cell in board.cells(img)
        ))
