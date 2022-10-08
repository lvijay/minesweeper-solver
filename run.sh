#!/bin/bash

COUNT=${1:-5}

function expert() {
    echo '
import static java.awt.event.InputEvent.BUTTON1_DOWN_MASK;

var robot = new java.awt.Robot();

void click(int x, int y) {
    robot.mouseMove(x, y);
    robot.mousePress(BUTTON1_DOWN_MASK);
    robot.delay(20);
    robot.mouseRelease(BUTTON1_DOWN_MASK);
}

click(770, 246)
click(770, 246)
robot.delay(1000);
click(800, 346);
' | jshell -s >/dev/null 2>&1
}

function restart_robot_server() {
    curl --silent 'localhost:8888/stop' -o /dev/null 2>/dev/null
    jps | awk '/Minesweeper/{print $1}' | xargs -n1 kill -s HUP >/dev/null 2>&1
    lsof -i:8888 | awk '/java/{print $2}' | xargs -n1 kill -s HUP >/dev/null 2>&1
    java MinesweeperPlayer 2>&1 >> roboserver.log &
    while ! curl --silent 'localhost:8888/mousemove?x=800&y=180' -o /dev/null 2>/dev/null; do
        sleep 0.1
    done
}

date >> "log_first.log"
date >> "log_random.log"

echo '| result   | time ms | clicks | guesses | # matchTemplate |'
for i in `seq 1 $COUNT`; do
    if ! jps | grep -q Minesweeper; then
        java MinesweeperPlayer 2>&1 >> roboserver.log &
    fi
    osascript -e '
tell application "System Events"
  launch application "Minesweeper"
  activate application "Minesweeper"
end tell'
    expert
    say "game $i"
    sleep 0.5
    if [[ "$((i % 2))" -eq "0" ]]; then
        MODE=random
    else
        MODE=first
    fi
    ## move cursor away from the board
    curl --silent 'localhost:8888/mousemove?x=170&y=246' -o /dev/null 2>/dev/null
    echo "game $i" >> debug_${MODE}.log
    ./play.py 8888 $MODE 2>> debug_${MODE}.log | tee -a "log_${MODE}.log"
    if [[ "$((i % 10))" -eq "0" ]]; then
        restart_robot_server
    fi
    tail -1 "log_${MODE}.log" | awk '/solved/{system("say game solved")}/exploded/{system("say game exploded")}'
    osascript -e 'quit application "Minesweeper"'
done

## stop the recording
sleep 1

jps | awk '/Minesweeper/{print $1}' | xargs -n1 kill -s HUP > /dev/null 2>&1
lsof -i:8888 | awk '/java/{print $2}' | xargs -n1 kill -s HUP > /dev/null 2>&1

echo '
import static java.awt.event.InputEvent.BUTTON1_DOWN_MASK;

var robot = new java.awt.Robot();

void click(int x, int y) {
    robot.mouseMove(x, y);
    robot.mousePress(BUTTON1_DOWN_MASK);
    robot.delay(20);
    robot.mouseRelease(BUTTON1_DOWN_MASK);
}

click(1217, 22)
click(1217, 22)
' | jshell -s >/dev/null 2>&1

## run.sh ends here
