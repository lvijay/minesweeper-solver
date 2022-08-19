# -*- mode: python; -*-

from collections import (
    defaultdict,
)
from fractions import (
    Fraction,
)
from itertools import (
    chain,
)
import random
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)
import z3


Point = Tuple[int, int]


def flatten(list_of_lists):
    "Flatten one level of nesting"
    return chain.from_iterable(list_of_lists)


class Board:
    def __init__(self, m, n):
        self.__m = m
        self.__n = n
        self.__grid: List[bool] = [False for _ in range(m * n)]

    @property
    def m(self): return self.__m

    @property
    def n(self): return self.__n

    def idx(self, x, y) -> int:
        if (x < 0 or x >= self.m) or (y < 0 or y >= self.n):
            raise IndexError(f"Invalid index ({x}, {y})")
        return x * self.n + y

    def xy(self, idx) -> Point:
        x, y = idx // self.n, idx % self.n
        if x >= self.m: raise IndexError(f"invalid index {idx}")
        return x, y

    def __getitem__(self, v: Point) -> int:
        x, y = v
        return self.__grid[self.idx(x, y)]

    def __setitem__(self, v: Point, val: int) -> None:
        x, y = v
        self.__grid[self.idx(x, y)] = val

    def value_tos(self, v) -> str:
        return '?*'[v]

    def __str__(self) -> str:
        return "\n".join(
            "".join(self.value_tos(self[i, j]) for j in range(self.n))
            for i in range(self.m)
        )

    def __repr__(self) -> str:
        nl = "\n"
        return f"<{self.__class__.__qualname__} {str(self).replace(nl, ',')}>"


class Minesweeper(Board):
    MINE = True
    NOMI = False

    def __init__(
            self,
            m: int,
            n: int,
            *,
            minecount: Optional[int] = None,
            mines: Optional[List[Point]] = None):
        super().__init__(m, n)
        self.__mines: Dict[Point, bool] = defaultdict(
            lambda: False)
        if not minecount and not mines:
            raise ValueError("must specify one of minecount or mines")
        if minecount and mines:
            raise ValueError("can only specify one of minecount or mines")
        if minecount or minecount == 0:
            positions: List[int] = random.sample(
                range(self.m * self.n),
                k=minecount)
            xys: List[Point] = [self.xy(v) for v in positions]
            for xy in xys: self.__mines[xy] = Minesweeper.MINE
        else:
            for i, v in enumerate(mines): self.__mines[self.idx(i)] = v
        self.__pstate: Dict[Point, Fraction] = {}
        self.__exploded = False

    def neighbor_xys(self, x: int, y: int) -> List[Point]:
        nbrs: List[Point] = [
            (x + xi, y + yj)
            for xi in (-1, 0, +1)
            for yj in (-1, 0, +1)
            if (xi, yj) != (0, 0)
            and (rx := x + xi) >= 0
            and rx < self.m
            and (ry := y + yj) >= 0
            and ry < self.n
        ]
        return nbrs

    def value_tos(self, v) -> str:
        if v == -1: return '#'
        return super().value_tos(v) if isinstance(v, bool) else str(v)

    def open(self, x, y) -> List[Tuple[Point, int]]:
        """Opens cell at (x, y).  No-op if cell already open.  Explodes if the
cell is a mine."""
        if self.__exploded: raise ValueError("Exploded")
        if self.__mines[x, y] == Minesweeper.MINE:
            self._explode(x, y)
        return self._open(x, y)

    def _open(self, x, y) -> List[Tuple[Point, int]]:
        "Same as open but does not explode."
        if self.__mines[x, y] == Minesweeper.MINE: return []
        if self[x, y] is not False: return []
        self[x, y] = self._minecount(x, y)
        if self[x, y] > 0:
            return [[(x, y), self[x, y]]]
        # when minecount is 0 open neighbors
        neighbors: List[Point] = self.neighbor_xys(x, y)
        pt_count_pairs = [self._open(i, j) for i, j in neighbors]
        return list(flatten(pt_count_pairs))

    def _explode(self, x, y):
        for i in range(self.m):
            for j in range(self.n):
                is_mine_ij = self.__mines[i, j] is True
                self[i, j] = True if is_mine_ij else self._minecount(i, j)
        self[x, y] = -1
        raise ValueError(f"Exploded at ({x}, {y})")

    def _minecount(self, x, y) -> int:
        "mines in the region surrounding (x, y).  Does not count (x, y)."
        mines = [1 for i, j in self.neighbor_xys(x, y) if self.__mines[i, j]]
        return sum(mines)


if __name__ == "__main__":
    b = Minesweeper(6, 6, minecount=5); print(b._Minesweeper__mines)
    for i in range(b.m):
        for j in range(b.n):
            if not b._Minesweeper__mines.get((i, j), False):
                print(f"opening ({i},{j})")
                b.open(i, j)
                print(b)

# minesweeper.py ends here
