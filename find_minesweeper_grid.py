#!/usr/bin/env python3

from enum import Enum
from math import (
    ceil,
    floor,
)
from typing import (
    Any,
    Dict,
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
    UNOPENED = "U_UNOPENED"
    FLAG = "F_FLAG"
    MINE = "*_MINE"
    UNKNOWN = "?_UNKNOWN"

    def __str__(self) -> str: return self.value[0]
    def __repr__(self) -> str: return str(self)


class FindImage:
    IMAGE_NAMES_FILES = [
        ("0", "find_n_0.png"), ("1", "find_n_1.png"),
        ("2", "find_n_2.png"), ("3", "find_n_3.png"),
        ("4", "find_n_4.png"), ("5", "find_n_5.png"),
        ("6", "find_n_6.png"), ("7", "find_n_7.png"),
        ("8", "find_n_8.png"),
        ("EXPLODED", "find_n_mine.png"),
        ("FINISHED", "find_n_finished.png"),
        ("FLAG", "find_n_flag.png"),
        ("UNOPENED", "find_n_uo.png"),
        ("CORNER.NE", "find_n_ne.png"), ("CORNER.NW", "find_n_nw.png"),
        ("CORNER.SE", "find_n_se.png"), ("CORNER.SW", "find_n_sw.png")
    ]
    def __init__(
            self,
            images: Dict[str, Image],
            height: int, width: int,
            extra_x: int, extra_y: int,
    ):
        self.height, self.width = height, width
        self.xtra_x, self.xtra_y = extra_x, extra_y
        image_cells = dict(
            (("0", Cell.C0), ("1", Cell.C1), ("2", Cell.C2), ("3", Cell.C3),
             ("4", Cell.C4), ("5", Cell.C5), ("6", Cell.C6), ("7", Cell.C7),
             ("8", Cell.C8), ("UNOPENED", Cell.UNOPENED), ("FLAG", Cell.FLAG),
             ("EXPLODED", Cell.MINE)
             ))
        cell_images = [
            (n, i)
            for n, i in images.items()
            if n == "UNOPENED"
            or n in "12345678"  # "0" excluded
        ]
        end_images = [
            (n, i)
            for n, i in images.items()
            if "EXPLODED" in n
            or "FINISHED" in n
        ]

        self.__all_images: Dict[str, Image] = images
        self.__end_images: Dict[str, Image] = end_images
        self.__cell_images: Dict[str, Image] = cell_images
        self.__image_cells: Dict[str, Cell] = image_cells

    def get_matches(
            self,
            image: Image,
            template: Image,
            name: str,
            threshold: float,
            algo: int
    ) -> Pair[np.ndarray]:
        match = cv2.matchTemplate(image, template, algo)
        ys, xs = np.asarray(match >= threshold).nonzero()
        if len(ys) == 0 or len(xs) == 0:
            raise SubImageNotFoundError(name)
        return xs, ys

    def get_unopened_corner(self, image, corner) -> Pair[np.ndarray]:
        template = self.__all_images[f"CORNER.{corner}"]
        return self.get_matches(
            image,
            template,
            corner,
            0.95,
            cv2.TM_CCOEFF_NORMED
        )

    def is_game_ended(self, image) -> str:
        "Returns True if the game is over; False otherwise."
        for name, template in self.__end_images:
            try:
                self.get_matches(
                    image,
                    template,
                    name,
                    0.95,
                    cv2.TM_CCOEFF_NORMED
                )
                return name
            except SubImageNotFoundError:
                pass

        return ""

    def get_new_board(self, image) -> Tuple[Tuple[int, int], Any]:
        ne_x, ne_y = self.get_unopened_corner(image, "NE")
        nw_x, nw_y = self.get_unopened_corner(image, "NW")
        se_x, se_y = self.get_unopened_corner(image, "SE")
        sw_x, sw_y = self.get_unopened_corner(image, "SW")
        nwx, nwy = int(nw_x[0] + self.xtra_x), int(nw_y[0] + self.xtra_y)
        board_width = int(ne_x[0] - nwx + self.width)
        board_height = int(se_y[0] - nwy + self.height)
        return (
            (nwx, nwy),
            Board(
                (board_width, board_height),
                (self.width, self.height)
            )
        )

    def identify_cell(self, cell: Image) -> Cell:
        saved_cells = self.__cell_images

        def matches(cell, saved_cell, name, algo=cv2.TM_CCOEFF_NORMED):
            cw, ch = cell.shape[:2]
            tw, th = saved_cell.shape[:2]
            if (cw > tw) and (ch > th) and (cw / ch == tw / th):
                # do an exact cell sized match
                xdf, ydf = (cw - tw) / 2, (ch - th) / 2
                xleft, xright = ceil(xdf), floor(xdf)
                yleft, yright = ceil(ydf), floor(ydf)
                self.get_matches(
                    cell[xleft:-xright, yleft:-yright],
                    saved_cell,
                    name,
                    0.99,
                    algo)
                return name
            return self.get_matches(cell, saved_cell, name, 0.95, algo)
        match_vals = []
        for name, img in saved_cells:
            try:
                match_vals.append(matches(cell, img, name))
            except SubImageNotFoundError:
                pass
        else:
            if len(match_vals) == 0:  # special handling for value=0
                template0 = self.__all_images["0"]
                try:
                    match_vals.append(
                        matches(cell, template0, "0", cv2.TM_CCORR_NORMED
                    ))
                except SubImageNotFoundError:
                    pass
        if len(match_vals) == 0:
            raise SubImageNotFoundError()
        if len(match_vals) > 1:
            raise TooManyMatchesFoundError()
        name = match_vals[0]
        return self.__image_cells[name]


class FindImageMacnative(FindImage):
    def __init__(self):
        super().__init__(
            images={
                name: image_read(f"games/macnative-ms/{filename}")
                for name, filename in FindImage.IMAGE_NAMES_FILES
            },
            height=30, width=30,
            extra_x=11, extra_y=11,
        )


class FindImageMinesweeperOnline(FindImage):
    def __init__(self):
        super().__init__(
            images={
                name: image_read(f"games/minesweeper.online/{filename}")
                for name, filename in FindImage.IMAGE_NAMES_FILES
            },
            height=24, width=24,
            extra_x=4, extra_y=4,
        )


class SubImageNotFoundError(Exception):
    def __init__(self, name="image"):
        super().__init__(f"Did not find {name}")


class TooManyMatchesFoundError(Exception):
    def __init__(self):
        super().__init__("Found too many matches")


class Board:
    def __init__(self, board_dims, cell_dims):
        self.__cellwidth = cell_dims[0]
        self.__cellheight = cell_dims[1]
        self.__boardwidth = board_dims[0]
        self.__boardheight = board_dims[1]
        self.__rows = round(self.__boardheight / self.__cellheight)
        self.__cols = round(self.__boardwidth / self.__cellwidth)

    @property
    def rows(self) -> int: return self.__rows

    @property
    def cols(self) -> int: return self.__cols

    @property
    def boardwidth(self): return self.__boardwidth

    @property
    def boardheight(self): return self.__boardheight

    def cell_dims(self, row, col) -> Pair[slice]:
        h, w = self.__cellheight, self.__cellwidth
        xstart, ystart = col * w, row * h
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
