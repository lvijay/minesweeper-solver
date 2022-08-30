# -*- mode: python; -*-

from collections import (
    defaultdict,
)
from enum import (
    Enum,
)
from itertools import (
    cycle,
)
import random
from typing import (
    Callable,
    DefaultDict,
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
K = TypeVar("K")
V = TypeVar("V")


class Board(Generic[T]):
    def __init__(
        self,
        m: int,
        n: int,
        supplier: Optional[Union[Callable[[], T], Iterable[T], T]] = None,
    ):
        if isinstance(supplier, Iterable):
            repeat = iter(cycle(supplier))
            supplier = lambda: next(repeat)
        elif not (callable(supplier)):
            temp: List[T] = [supplier]
            supplier = lambda: temp[0]
        self.__m = m
        self.__n = n
        self.__grid: Dict[Point, T] = {
            (i, j): supplier() for i in range(m) for j in range(n)
        }

    @property
    def m(self):
        return self.__m

    @property
    def n(self):
        return self.__n

    def __setitem__(self, p: Point, val: T) -> None:
        self[p]  # throw KeyError if missing
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

    def __str__(self) -> str:
        return "\n".join(
            "".join("O#"[1 if self[i, j] else 0] for j in range(self.n))
            for i in range(self.m)
        )


class Action(Enum):
    OPEN = "OPEN"
    MARK = "MARK"
    UNMARK = "UNMARK"
    CHORD = "CHORD"


class Minesweeper:
    MINE = 10  # cell is a mine
    UNOPENED = 11  # cell unopened
    FLAG = 12  # cell marked as flag
    EXPLODED = -1  # this board has exploded

    def __init__(
        self, m: int, n: int, *, minecount: int = 0, mines: Iterable[bool] = []
    ):
        self.__m = m
        self.__n = n
        self.__grid: Board[int] = Board(m, n, lambda: Minesweeper.UNOPENED)

        if isinstance(minecount, int) and minecount > 0:
            positions: List[Point] = random.sample(
                [(i, j) for i in range(m) for j in range(n)], k=minecount
            )
            the_mines: Board[bool] = Board(m, n, lambda: False)
            for xy in positions:
                the_mines[xy] = True
        else:
            the_mines: Board[bool] = Board(m, n, mines)
        self.__mines: Board[bool] = the_mines
        self.__exploded = False

    @property
    def m(self):
        return self.__m

    @property
    def n(self):
        return self.__n

    def __getitem__(self, v: Point) -> int:
        return self.__grid[v]

    def __setitem__(self, v: Point, val: int) -> None:
        self.__grid[v] = val

    def neighbor_xys(self, x: int, y: int) -> List[Point]:
        return self.__grid.neighbor_xys(x, y)

    def value_tos(self, v) -> str:
        if v == Minesweeper.EXPLODED:
            return "%"
        if v is Minesweeper.MINE:
            return "*"
        if v is Minesweeper.UNOPENED:
            return "?"
        if v is Minesweeper.FLAG:
            return "+"
        return str(v)

    def __str__(self) -> str:
        return "\n".join(
            "".join(self.value_tos(self[i, j]) for j in range(self.n))
            for i in range(self.m)
        )

    def __repr__(self) -> str:
        nl = "\n"
        return f"<{type(self).__qualname__} {str(self).replace(nl, ',')}>"

    def click(self, xy: Point, action: Action):
        x, y = xy
        if action == Action.OPEN:
            # Opens cell at (x, y).  No-op if cell already open or flagged.
            # Explodes if the cell is a mine.
            if self.__exploded:
                raise ValueError("Exploded")
            if self.__mines[x, y] is True:
                raise self._explode(x, y)
            if self[x, y] == Minesweeper.FLAG:
                return []
            return self._open(x, y)
        elif action == Action.CHORD:
            raise NotImplementedError(f"CHORD not yet implemented")
        elif action == Action.MARK:
            self[x, y] = Minesweeper.FLAG
        elif action == Action.UNMARK:
            self[x, y] = Minesweeper.UNOPENED
        else:
            raise ValueError(f"Unknown action {action}")

    def _open(self, x, y) -> List[Tuple[Point, int]]:
        "Same as open but does not explode."
        if self.__mines[x, y] is True:
            return []
        if self[x, y] != Minesweeper.UNOPENED:
            return []
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
        return ValueError(f"Exploded at ({x}, {y})")

    def _minecount(self, x, y) -> int:
        "mines in the region surrounding (x, y).  Does not count (x, y)."
        mines = [1 for i, j in self.neighbor_xys(x, y) if self.__mines[i, j]]
        return sum(mines)


class DoubleSidedDict(Generic[K, V]):
    def __init__(self, d: Dict[K, V]):
        self.__kv: Dict[K, V] = {k: v for k, v in d.items()}
        self.__vk: Dict[V, K] = {v: k for k, v in d.items()}

    def kv(self, k: K) -> V:
        return self.__kv[k]

    def vk(self, v: V) -> K:
        return self.__vk[v]

    def keys(self) -> List[K]:
        return list(self.__kv.keys())

    def values(self) -> List[V]:
        return list(self.__vk.keys())


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
    def known(self):
        return self.__known

    @property
    def mines(self):
        return self.__mines

    @property
    def unknowns(self):
        return self.__unknowns

    def add_known(self, x: int, y: int, val: int) -> None:
        self.known[x, y] = val
        try:
            self.unknowns.remove((x, y))
        except KeyError:
            pass

    def add_mine(self, x, y) -> None:
        self.mines[x, y] = True
        try:
            self.unknowns.remove((x, y))
        except KeyError:
            pass

    def play(self, xy: Optional[Point]):
        if xy is None:
            xy = next(iter(set(self.unknowns)))
        elif self.mines[xy] is True:
            return []
        elif self.known[xy] is not None:
            return
        else:
            x, y = xy
        print(f"opening ({xy})")
        opened = self.minesweeper.click(xy, Action.OPEN)
        for (px, py), mc in opened:
            if self.known[px, py] is not None:
                raise ValueError("unexpected value change")
            self.add_known(px, py, mc)
        cells: DoubleSidedDict[Point, z3.Int] = DoubleSidedDict(
            {(ux, uy): z3.Int(f"c<{ux},{uy}>") for ux, uy in self.unknowns}
        )
        kcd: Dict[Point, List[z3.Int]] = self._known_cell_dict(cells)

        solver: z3.Solver = z3.Solver()
        for cell in cells.values():
            solver.add(z3.Or(cell == 0, cell == 1))

        for (ptx, pty), celz in kcd.items():
            count: int = self.minesweeper[ptx, pty]
            solver.add(sum(celz) == count)

        yes_mines: List[z3.Int] = sorted(
            self.sure_mines(cells, solver), key=str
        )
        not_mines: List[z3.Int] = sorted(
            self.sure_non_mines(cells, solver), key=str
        )

        print(f"mines = {yes_mines}")
        for mine in yes_mines:
            pt: Point = cells.vk(mine)
            self.add_mine(*pt)
            self.minesweeper.click(pt, Action.MARK)

        print(f"not_mines = {not_mines}")
        return [cells.vk(cell) for cell in not_mines]

    def _known_cell_dict(
        self, cells: DoubleSidedDict[Point, z3.Int]
    ) -> Dict[Point, List[z3.Int]]:
        known_neighbors = {
            uxy: [
                nxy
                for nxy in s.minesweeper.neighbor_xys(*uxy)
                if nxy not in s.unknowns
            ]
            for uxy in s.unknowns
        }
        inverse_kn: DefaultDict[Point, List[z3.Int]] = defaultdict(list)
        for cxy, oxy in known_neighbors.items():
            for xy in oxy:
                inverse_kn[xy].append(cells.kv(cxy))
        return inverse_kn

    def sure_non_mines(
        self, cells: DoubleSidedDict[Point, z3.Int], solver: z3.Solver
    ) -> List[z3.Int]:
        return [
            cell
            for cell in cells.values()
            if solver.check(cell == 1) == z3.unsat
        ]

    def sure_mines(
        self, cells: DoubleSidedDict[Point, z3.Int], solver: z3.Solver
    ) -> List[z3.Int]:
        return [
            cell
            for cell in cells.values()
            if solver.check(cell == 0) == z3.unsat
        ]

    def __str__(self) -> str:
        l1 = str(self.minesweeper).split("\n")
        l2 = str(self.minesweeper._Minesweeper__mines).split("\n")

        return "---\n" + "\n".join(
            l1r + "\t" + l2r for l1r, l2r in zip(l1, l2)
        )


if __name__ == "__main__":
    ms = """010000000
            010000000
            000000000
            000001100
            000000000
            000000000
            000000000
            101010101
            000000000
            000000111
            000000000""".replace(
        " ", ""
    ).replace(
        "\n", ""
    )
    b = Minesweeper(
        11,
        9,
        mines=([False, True][x == "1"] for x in ms),
    )
    print(b._Minesweeper__mines)
    s = MineSolver(b)

    candidate: Point = next(
        (i, j)
        for i in range(b.m)
        for j in range(b.n)
        if b._minecount(i, j) <= 0 and b._Minesweeper__mines[i, j] is False
    )

    print(f"playing {candidate}")
    non_mines = s.play(candidate)
    not_mines = set(non_mines)
    print(f"not_mines = {not_mines}")
    while len(not_mines) > 0:
        point: Point = not_mines.pop()
        print(f"playing {point}")
        next_set = s.play(point)
        print(s)
        for np in next_set:
            not_mines.add(np)

    print(s)

# minesweeper.py ends here
