# -*- mode: python; -*-

from collections import (
    defaultdict,
)
from enum import Enum
from itertools import (
    cycle,
)
import random
from typing import (
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)
import z3


Point = Tuple[int, int]
T = TypeVar("T")


class Board(Generic[T]):
    def __init__(
            self,
            m: int,
            n: int,
            supplier: Optional[Union[Callable[[], T], Iterable[T]]] = None
    ):
        if isinstance(supplier, Iterable):
            repeat = iter(cycle(supplier))
            supplier = lambda: next(repeat)
        elif not(callable(supplier)):
            temp = [supplier]
            supplier = lambda: temp[0]
        self.__m = m
        self.__n = n
        self.__grid: Dict[Point, T] = {
            (i, j): supplier()
            for i in range(m)
            for j in range(n)
        }

    @property
    def m(self): return self.__m

    @property
    def n(self): return self.__n

    def __setitem__(self, p: Point, val: T) -> None:
        self[p]                 # throw KeyError if missing
        self.__grid[p] = val

    def __getitem__(self, p: Point) -> T:
        return self.__grid[p]

    def neighbor_xys(self, x: int, y: int) -> List[Point]:
        nbrs: List[Point] = [
            (rx, ry)
            for xi in (-1, 0, +1)
            for yj in (-1, 0, +1)
            if (xi, yj) != (0, 0)
            and (rx := x + xi, ry := y + yj) in self.__grid
        ]
        return nbrs


class Minesweeper:
    MINE = 10                 # is a mine
    UNNO = 11                 # unknown
    EXPLODED = -1             # this board has exploded

    def __init__(
            self,
            m: int,
            n: int,
            *,
            minecount: int = 0):
        self.__m = m
        self.__n = n
        self.__grid: Board[int] = Board(m, n, lambda: Minesweeper.UNNO)
        self.__mines: Board[bool] = Board(m, n, lambda: False)
        positions: List[int] = random.sample(
            [(i, j) for i in range(m) for j in range(n)],
            k=minecount)
        for xy in positions: self.__mines[xy] = True
        self.__exploded = False

    @property
    def m(self): return self.__m

    @property
    def n(self): return self.__n

    def __getitem__(self, v: Point) -> int:
        return self.__grid[v]

    def __setitem__(self, v: Point, val: int) -> None:
        self.__grid[v] = val

    def neighbor_xys(self, x: int, y: int) -> List[Point]:
        return self.__grid.neighbor_xys(x, y)

    def value_tos(self, v) -> str:
        if v == Minesweeper.EXPLODED: return "#"
        if v is Minesweeper.MINE: return "*"
        if v is Minesweeper.UNNO: return "?"
        return str(v)

    def __str__(self) -> str:
        return "\n".join(
            "".join(self.value_tos(self[i, j]) for j in range(self.n))
            for i in range(self.m)
        )

    def __repr__(self) -> str:
        nl = "\n"
        return f"<{type(self).__qualname__} {str(self).replace(nl, ',')}>"

    def open(self, x, y) -> List[Tuple[Point, int]]:
        """Opens cell at (x, y).  No-op if cell already open.  Explodes if the
cell is a mine."""
        if self.__exploded: raise ValueError("Exploded")
        if self.__mines[x, y] is True:
            self._explode(x, y)
        return self._open(x, y)

    def _open(self, x, y) -> List[Tuple[Point, int]]:
        "Same as open but does not explode."
        if self.__mines[x, y] is True: return []
        if self[x, y] != Minesweeper.UNNO: return []
        self[x, y] = self._minecount(x, y)
        if self[x, y] > 0:
            return [((x, y), self[x, y])]
        # when minecount is 0 open neighbors
        pt_count_pairs = [((x, y), self[x, y])]
        for ni, nj in self.neighbor_xys(x, y):
            pt_count_pairs.extend(self._open(ni, nj))
        return pt_count_pairs

    def _explode(self, x, y):
        for i in range(self.m):
            for j in range(self.n):
                is_mine_ij = self.__mines[i, j] is True
                self[i, j] = True if is_mine_ij else self._minecount(i, j)
        self[x, y] = Minesweeper.EXPLODED
        raise ValueError(f"Exploded at ({x}, {y})")

    def _minecount(self, x, y) -> int:
        "mines in the region surrounding (x, y).  Does not count (x, y)."
        mines = [1 for i, j in self.neighbor_xys(x, y) if self.__mines[i, j]]
        return sum(mines)


class MineSolver:
    def __init__(self, minesweeper: Minesweeper):
        self.minesweeper = minesweeper
        self.m, self.n = self.minesweeper.m, self.minesweeper.n
        self.__known: Board[int] = Board(self.m, self.n, None)
        self.__mines: Board[bool] = Board(self.m, self.n, False)
        self.__unknowns: Set[Point] = {
            (i, j) for i in range(self.m) for j in range(self.n)
        }

    @property
    def known(self): return self.__known

    @property
    def mines(self): return self.__mines

    @property
    def unknowns(self): return self.__unknowns

    def add_known(self, x: int, y: int, val: int) -> None:
        self.known[x, y] = val
        self.unknowns.remove((x, y))

    def add_mine(self, x, y) -> None:
        self.mines[x, y] = True
        self.unknowns.remove((x, y))

    def play(self, xy: Optional[Point]):
        if xy is None:
            xy = next(iter(set(self.unknowns)))
        elif self.known[xy] is not None:
            return
        else:
            x, y = xy
        print(f"opening ({x}, {y})")
        position_vals: List[Tuple[Point, int]] = self.minesweeper.open(x, y)
        for (px, py), mc in position_vals:
            if self.known[px, py] is not None:
                raise ValueError("unexpected value change")
            self.add_known(px, py, mc)
        cells: Dict[Point, z3.Int] = {
            (ux, uy): z3.Int(f"c<{ux},{uy}>")
            for ux, uy in self.unknowns
        }
        known_neighbors = {
            uxy: [
                nxy
                for nxy in s.minesweeper.neighbor_xys(*uxy)
                if nxy not in s.unknowns
            ]
            for uxy in s.unknowns
        }
        icells = {pt: cl for cl, pt in cells.items()}
        inverse_kn = defaultdict(lambda: [])
        for cxy, oxy in known_neighbors.items():
            for xy in oxy:
                inverse_kn[xy].append(cells[cxy])
        def_mines = self._initial_analysis(inverse_kn, icells)

        return def_mines

    def _initial_analysis(self, inverse_kn, icells):
        inverse_kn = inverse_kn
        definite_mines = {
            cells[0]
            for known_xy, cells in inverse_kn.items()
            if len(cells) == 1
        }

        print(f"definite_mines = {definite_mines}")

        for cell in definite_mines:
            keys = {kxy for kxy, cells in inverse_kn.items() if cell in cells}
            for kxy in keys: inverse_kn[kxy].remove(cell)

        empty_kxys = [kxy for kxy, cells in inverse_kn.items() if not cells]
        for kxy in empty_kxys:
            del inverse_kn[kxy]

        print(f"empty_kxys = {empty_kxys}")

        return definite_mines

    def __str__(self) -> str:
        pt = self.known
        mrows = str(self.minesweeper).split("\n")
        prows = [
            "".join("%d" % (pt[i, j] or 9) for j in range(self.n))
            for i in range(self.m)
        ]
        return "\n".join(pr + "    " + mr for pr, mr in zip(prows, mrows))


def dwim():
    c00, c10, c20 = z3.Ints('c00 c10 20')
    so = z3.Solver()
    so.add(c00 + c10 + c20 == 1)
    so.add(c00 + c10 == 1)
    so.add(c00 >= 0, c00 <= 1)
    so.add(c10 >= 0, c10 <= 1)
    so.add(c20 >= 0, c20 <= 1)
    so.set("sat.pb.solver", "solver")


if __name__ == "__main__":
    b = Minesweeper(9, 11, minecount=3)
    s = MineSolver(b)
    print(s)
    l1mines = s.play()
    print(s)
    print(l1mines)

# minesweeper.py ends here
