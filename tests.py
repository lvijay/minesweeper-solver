## none of these work
## TODO make them work


def find_minesweeper_grid_test():
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
