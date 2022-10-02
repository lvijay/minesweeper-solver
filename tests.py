## none of these work
## TODO make them work


def test_find_minesweeper_grid():
    import sys
    from find_minesweeper_grid import *

    filename = sys.argv[1]
    other_images = sys.argv[2:]

    image = image_read(filename)
    finder = FindImage()

    if finder.is_game_ended(image):
        print("game over")
        sys.exit(0)

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
        print(f"image {ic}:")

        array = [[None for j in range(board.cols)] for i in range(board.rows)]
        for i, j, cell in board.cells(image):
            try:
                array[i][j] = finder.identify_cell(cell)
            except SubImageNotFoundError as e:
                print(e)
                print(f"could not identify cell at ({i},{j})")
        for row in array: print("".join(map(str, row)))
        print()


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    other_images = sys.argv[2:]

    image = image_read(filename)
    finder = FindImage()

    if finder.is_game_ended(image):
        print("game over")
        sys.exit(0)

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
        print(f"image {ic}:")

        array = [[None for j in range(board.cols)] for i in range(board.rows)]
        for i, j, cell in board.cells(image):
            try:
                array[i][j] = finder.identify_cell(cell)
            except SubImageNotFoundError as e:
                print(e)
                print(f"could not identify cell at ({i},{j})")
        for row in array: print("".join(map(str, row)))
        print()

def test_minesweeper():
    from minesweeper import *
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
    non_mines = s.play(candidate)
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
            next_set = s.play(point)
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
