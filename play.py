#!/usr/bin/env python3

from random import choice
import time
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
    SubImageNotFoundError,
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

        px, py = self.location(*xy)
        rpx, rpy = self.robot.move_to(px, py)
        if rpx != px or rpy != py:
            raise ValueError(f"Could not move to {px, py}")
        self.robot.click()

    def get_state(self) -> List[Tuple[Point, int]]:
        exploded_pt = None
        image = self.robot.screencap()
        for i, j, cellimg in self.board.cells(image):
            try:
                cell: Cell = self.finder.identify_cell(cellimg)
            except SubImageNotFoundError as e:
                identifier = int(time.time())
                cellimage = f"o_{identifier}_{i},{j}.png"
                boardimage = f"o_{identifier}_board.png"
                print(f"cell identification error at {i,j}"
                    f" saving cell to {cellimage},"
                    f" saving board to {boardimage}")
                cv2.imwrite(cellimage, cellimg)
                cv2.imwrite(boardimage, image)
                raise ValueError("cell identification error")

            count: int = RobotMinesweeper.to_count(cell)
            self[i, j] = count
            if count == Minesweeper.MINE:
                exploded_pt = i, j
                break

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


def play(robot):
    finder = FindImage()
    board = finder.get_new_board(robot.screencap())
    rm = RobotMinesweeper(robot, finder, board)
    solver = MineSolver(rm)
    while True:
        unmines = solver.update_board_state()
        if len(unmines) == 0:
            unknowns = list(solver.unknowns())
            if len(unknowns) == 0:
                raise ValueError("solved")
            point = choice(unknowns)
            print(f"guessing... {point}")
            rm.click(point, Action.OPEN)
        else:
            print(f"opening...  {unmines}")
            for point in unmines:
                rm.click(point, Action.OPEN)


if __name__ == "__main__":
    import sys
    import datetime
    robot = Robot(8888)
    p = print
    print = lambda *args: p(*args, file=sys.stderr)
    start_time_ns = time.time_ns()
    def result(solved, start):
        timetaken_ms = int((time.time_ns() - start) // 1e6)
        result = 'solved' if solved else 'exploded'
        p(f"Game {result} in {timetaken_ms} ms")
    try:
        play(robot)
    except ValueError as e:
        end = time.time()
        if "Exploded" in e.args[0]:
            result(False, start_time_ns)
        elif "solved" in e.args[0]:
            result(True, start_time_ns)
        elif "cell identification error" in e.args[0]:
            print(f"Could not identify cell")
        sys.exit(0)
    except SubImageNotFoundError:
        result(True, start_time_ns)
        sys.exit(0)
    except requests.exceptions.ConnectionError:
        p("Robot server failure")
        sys.exit(1)
