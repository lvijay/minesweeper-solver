#!/usr/bin/env python3

from typing import (
    List,
    Tuple,
)

from minesweeper import (
    Action,
    Minesweeper,
    MineSolver,
    Point,
)
from find_minesweeper_grid import (
    Board,
    Cell,
    FindImage,
    Image,
    board_cells,
)

import cv2
import numpy as np
import requests

class Robot:
    def __init__(self, port: int):
        self.__port = port
        self.__url = f"http://localhost:{port}"

    def move_to(self, x, y) -> Point:
        rx, ry = -1, -1
        for _ in range(10):
            rj = self.__request("mousemove", {"x": x, "y": y}).json()
            rx, ry = rj["x"], rj["y"]
            if rx == x and ry == y:
                return (x, y)
        return rx, ry

    def click(self) -> Point:
        rj = self.__request("mouseclick").json()
        rx, ry = rj["x"], rj["y"]
        return rx, ry

    def screencap(self) -> Image:
        img = self.__request("screencap").content
        nparr = np.frombuffer(img, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)

    def delay(self, millis: int) -> None:
        import time
        time.sleep(1e-3 * millis)

    def __request(self, path, params={}):
        return requests.get(self.__url + "/" + path, params=params)


class RobotMinesweeper(Minesweeper):
    def __init__(self, robot: Robot, finder: FindImage, board: Board):
        self.robot: Robot = robot
        self.finder: FindImage = finder
        self.board: Board = board
        super().__init__(board.rows, board.cols, minecount=1)

    def location(self, cellx, celly) -> Tuple[int, int]:
        def mid_point(slice_r):
            return slice_r.start + (slice_r.stop - slice_r.start) // 2
        ys, xs = self.board.cell_dims(cellx, celly)
        return (mid_point(xs), mid_point(ys))

    def click(self, xy: Point, action: Action) -> None:
        if action != Action.OPEN:
            raise NotImplementedError(f"{action} not implemented")

        print(f"opening {xy}")

        px, py = self.location(*xy)
        rpx, rpy = self.robot.move_to(px, py)
        if rpx != px or rpy != py:
            raise ValueError(f"Could not move to {px, py}")
        self.robot.click()

    def get_state(self) -> List[Tuple[Point, int]]:
        exploded_pt = None
        for i, j, cellimg in self.board.cells(self.robot.screencap()):
            cell: Cell = self.finder.identify_cell(cellimg)
            count: int = RobotMinesweeper.to_count(cell)
            self[(i, j)] = count
            if count == Minesweeper.MINE:
                exploded_pt = i, j

        if exploded_pt is not None:
            raise self._explode(exploded_pt)

        return [
            ((i, j), self[i, j])
            for i in range(self.m) for j in range(self.n)
            if self[i, j] != Minesweeper.UNOPENED
        ]

    @staticmethod
    def to_count(cell: Cell) -> int:
        return {
            Cell.C0: 0,
            Cell.C1: 1,
            Cell.C2: 2,
            Cell.C3: 3,
            Cell.C4: 4,
            Cell.C5: 5,
            Cell.C6: 6,
            Cell.C7: 7,
            Cell.C8: 8,
            Cell.UNOPENED: Minesweeper.UNOPENED,
            Cell.FLAG: Minesweeper.FLAG,
            Cell.MINE: Minesweeper.MINE
        }[cell]


if __name__ == "__main__":
    robot = Robot(8888)
    finder = FindImage()
    board = finder.get_new_board(robot.screencap())
    rm = RobotMinesweeper(robot, finder, board)
    solver = MineSolver(rm)
    solver.update_board_state()
    point0 = next(solver.unknowns())
    rm.click(point0, Action.OPEN)
    robot.delay(1000)
    while True:
        solver = MineSolver(rm)
        mines, unmines = solver.update_board_state()
        for point in unmines:
            rm.click(point, Action.OPEN)
        else:
            point = next(solver.unknowns(), (-1, -1))
            rm.click(point, Action.OPEN)
            robot.delay(1000)
