#!/usr/bin/env python3

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
    @staticmethod
    def _distance(p1, p2) -> int:
        p1x, p1y = p1
        p2x, p2y = p2
        return int(((p1x - p2x) ** 2 + (p1y - p2y) ** 2) ** 0.5)

    def __init__(self, port: int):
        self.__port = port
        self.__url = f"http://localhost:{port}"
        self.lastpos: Tuple[int, int] = (-1, -1)
        self.total_distance: int = 0
        self.total_clicks = 0

    def move_to(self, x, y) -> Point:
        rx, ry = -1, -1
        for _ in range(10):
            rj = self.__request("mousemove", {"x": x, "y": y}).json()
            rx, ry = rj["x"], rj["y"]
            if rx == x and ry == y:
                break
        if self.lastpos == (-1, -1): self.lastpos = x, y
        self.total_distance += Robot._distance(self.lastpos, (rx, ry))
        self.lastpos = rx, ry
        return rx, ry

    def click(self) -> Point:
        rj = self.__request("mouseclick").json()
        rx, ry = rj["x"], rj["y"]
        self.total_clicks += 1
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
                raise ValueError("cell identification error", e)
            count: int = RobotMinesweeper.to_count(cell)
            self[i, j] = count
            if count == Minesweeper.MINE:
                raise self._explode((i, j))

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


def play(robot, selector, actions):
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
            point = selector(unknowns)
            print(f"guessing... {point}")
            actions.append(0)
            rm.click(point, Action.OPEN)
        else:
            print(f"opening...  {unmines}")
            actions.append(len(unmines))
            for point in unmines:
                rm.click(point, Action.OPEN)


if __name__ == "__main__":
    import sys
    from random import choice

    default_args = '8888 first'.split()
    args = sys.argv[1:] + default_args[len(sys.argv) - 1:]
    port = int(args[0])
    selector = (lambda lst: lst[0]) if args[1] == 'first' else choice

    robot = Robot(port)
    p = print
    print = lambda *args: p(*args, file=sys.stderr)
    actions = []
    start_time_ns = time.time_ns()

    def result(solved, start):
        timetaken_ms = int((time.time_ns() - start) // 1e6)
        result = 'solved' if solved else 'exploded'
        clicks = robot.total_clicks
        distance = robot.total_distance
        guesses = sum((1 for c in actions if c == 0))
        knowns = "|".join((str(c) for c in actions if c != 0))
        p(f"Game {result} {timetaken_ms}ms {clicks} {distance}px {guesses} {knowns}")

    try:
        play(robot, selector, actions)
    except ValueError as e:
        end = time.time()
        if "Exploded" in e.args[0]:
            result(solved=False, start=start_time_ns)
        elif "solved" in e.args[0]:
            result(solved=True, start=start_time_ns)
        elif "cell identification error" in e.args[0]:
            p(f"Could not identify cell {e}")
        else:
            p(f"unknown error {e}")
        sys.exit(0)
    except SubImageNotFoundError:
        result(solved=True, start=start_time_ns)
        sys.exit(0)
    except requests.exceptions.ConnectionError:
        p("Robot server failure")
        sys.exit(1)
