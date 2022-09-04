# -*- mode: python; -*-

from enum import (
    Enum,
)
from itertools import (
    cycle,
)
import random
from typing import (
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
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

    def neighbor_xys(self, xy: Point) -> List[Point]:
        x, y = xy
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

    def __iter__(self) -> Iterator[Tuple[Point, T]]:
        return (
            ((i, j), self[i, j]) for i in range(self.m) for j in range(self.n)
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

        the_mines: Board[bool]
        if isinstance(minecount, int) and minecount > 0:
            positions: List[Point] = random.sample(
                [(i, j) for i in range(m) for j in range(n)], k=minecount
            )
            the_mines = Board(m, n, lambda: False)
            for xy in positions:
                the_mines[xy] = True
        else:
            the_mines = Board(m, n, mines)
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

    def neighbor_xys(self, xy: Point) -> List[Point]:
        return self.__grid.neighbor_xys(xy)

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
        if action == Action.OPEN:
            # Opens cell at (x, y).  No-op if cell already open or flagged.
            # Explodes if the cell is a mine.
            if self.__exploded:
                raise ValueError("Exploded")
            if self.__mines[xy] is True:
                raise self._explode(xy)
            if self[xy] == Minesweeper.FLAG:
                return []
            return self._open(xy)
        elif action == Action.CHORD:
            raise NotImplementedError(f"CHORD not yet implemented")
        elif action == Action.MARK:
            self[xy] = Minesweeper.FLAG
        elif action == Action.UNMARK:
            self[xy] = Minesweeper.UNOPENED
        else:
            raise ValueError(f"Unknown action {action}")

    def _open(self, xy: Point) -> List[Tuple[Point, int]]:
        "Same as open but does not explode."
        if self.__mines[xy] is True:
            return []
        if self[xy] != Minesweeper.UNOPENED:
            return []
        self[xy] = self._minecount(xy)
        if self[xy] > 0:
            return [((xy), self[xy])]
        # when minecount is 0 open neighbors
        pt_count_pairs = [((xy), self[xy])]
        for nij in self.neighbor_xys(xy):
            pt_count_pairs.extend(self._open(nij))
        return pt_count_pairs

    def _explode(self, xy: Point):
        for i in range(self.m):
            for j in range(self.n):
                is_mine_ij = self.__mines[i, j] is True
                self[i, j] = True if is_mine_ij else self._minecount((i, j))
        self[xy] = Minesweeper.EXPLODED
        return ValueError(f"Exploded at ({xy})")

    def _minecount(self, xy: Point) -> int:
        "mines in the region surrounding (x, y).  Does not count (x, y)."
        mines = [1 for ij in self.neighbor_xys(xy) if self.__mines[ij]]
        return sum(mines)


class MineSolver:
    UNKNOWN = 10
    MINE = 11

    def __init__(self, minesweeper: Minesweeper):
        self.minesweeper = minesweeper
        self.m, self.n = self.minesweeper.m, self.minesweeper.n
        self.__known: Board[int] = Board(self.m, self.n, MineSolver.UNKNOWN)

    @property
    def known(self):
        return self.__known

    def unknowns(self) -> Iterable[Point]:
        return (pt for pt, v in self.known if v == MineSolver.UNKNOWN)

    def mines(self) -> Iterable[Point]:
        return (pt for pt, v in self.known if v == MineSolver.MINE)

    def add_known(self, xy: Point, val: int) -> None:
        self.known[xy] = val

    def play(self, xy: Point) -> Tuple[List[Point], List[Point]]:
        if self.known[xy] is not MineSolver.UNKNOWN:
            return [], []
        print(f"opening ({xy})")
        opened = self.minesweeper.click(xy, Action.OPEN)
        for pxy, mc in opened:
            self.add_known(pxy, mc)

        solver: z3.Solver = z3.Solver()
        cells: Dict[Point, z3.Int] = dict()
        for pt, v in self.known:
            cells[pt] = z3.Int(f"c{pt}")
            if v == MineSolver.UNKNOWN:
                solver.add(z3.Or(cells[pt] == 0, cells[pt] == 1))
            elif v == MineSolver.MINE:
                solver.add(cells[pt] == 1)
            else:  # v is a number
                solver.add(cells[pt] == 0)

        print(f"", end="")
        for pt, v in self.known:
            if v not in (MineSolver.MINE, MineSolver.UNKNOWN):
                neighbors = self.known.neighbor_xys(pt)
                ncells = [cells[nxy] for nxy in neighbors]
                solver.add(v == sum(ncells))

        if solver.check() == z3.unsat:
            raise ValueError("solver in unsat state")

        mines, non_mines = self.sure_mines_nonmines(cells, solver)
        print(f"    mines = {mines}")
        print(f"non_mines = {non_mines}")

        for mine_xy in mines:
            self.known[mine_xy] = MineSolver.MINE
            self.minesweeper.click(mine_xy, Action.MARK)

        return mines, non_mines

    def sure_mines_nonmines(
        self, cells: Dict[Point, z3.Int], solver: z3.Solver
    ) -> Tuple[List[Point], List[Point]]:
        def dwim(pt, condition):
            if solver.check(condition) == z3.unsat:
                return pt
            return None

        mines_nonmines: List[Tuple[Optional[Point], Optional[Point]]] = [
            (dwim(pt, cell == 0), dwim(pt, cell == 1))
            for pt, cell in cells.items()
        ]

        mines = [v for v, _ in mines_nonmines if v]
        nonmines = [
            v
            for _, v in mines_nonmines
            if v and self.known[v] == MineSolver.UNKNOWN
        ]

        return mines, nonmines

    def __str__(self) -> str:
        def tos(v):
            if v == MineSolver.MINE:
                return "*"
            if v == MineSolver.UNKNOWN:
                return "@"
            return str(v)

        l1 = str(self.minesweeper).split("\n")
        l2 = [
            "".join(tos(self.known[i, j]) for j in range(self.n))
            for i in range(self.m)
        ]

        return "\n  | " + "\n  | ".join(
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
    b = Minesweeper(11, 9, minecount=41)
    s = MineSolver(b)
    print(s)

    candidate: Point = next(
        (i, j)
        for i in range(b.m)
        for j in range(b.n)
        if b._minecount((i, j)) == 0 and b._Minesweeper__mines[i, j] is False
    )

    print(f"candidate {candidate}")
    mines, non_mines = s.play(candidate)
    non_mines = [n for n in non_mines if s.known[n] == MineSolver.UNKNOWN]
    print(f"len(not_mines) = {len(non_mines)}")
    not_mines: Set[Point] = set(non_mines)
    import time

    start = time.time()
    with open("debug.txt", "w") as out:
        print(s, file=out)
        while True:
            point: Point
            if len(not_mines) > 0:
                point = not_mines.pop()
            else:
                point = next(s.unknowns(), (-1, -1))
            if point == (-1, -1):
                break
            print(f"playing {point}", file=out)
            _, next_set = s.play(point)
            next_set = [
                n for n in next_set if s.known[n] == MineSolver.UNKNOWN
            ]
            print(s, file=out)
            print(f"len(next_set)  = {len(next_set)}")
            not_mines.update(next_set)
        print(s, file=out)
    print(s)
    end = time.time()
    print(f"time taken = {end - start} ms")

# minesweeper.py ends here
