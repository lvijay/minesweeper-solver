#!/bin/bash

COUNT=${1:-5}

alias curl='curl --silent'

function expert() {             # switch game to expert mode
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
    curl 'localhost:8888/stop' -o /dev/null 2>/dev/null
    jps | awk '/Minesweeper/{print $1}' | xargs -n1 kill -s HUP >/dev/null 2>&1
    lsof -i:8888 | awk '/java/{print $2}' | xargs -n1 kill -s HUP >/dev/null 2>&1
    java MinesweeperPlayer 2>&1 >> roboserver.log &
    while ! curl 'localhost:8888/mousemove?x=800&y=180' -o /dev/null 2>/dev/null; do
        sleep 0.1
    done
}

LOGFILE="runlog.log"
DEBUGFILE="debug.log"

date >> $LOGFILE

echo '| game mode   | result   | time ms | clicks | guesses | imgMatches | bandwidth |'
i=1
while true; do
for MODE in first random; do
    restart_robot_server
    for SCREENCAP in fullscreen board; do
        for REFRESH_BOARD in False True; do
            if [[ $i -gt $COUNT ]]; then
                break 4
            fi
            osascript -e '
tell application "System Events"
  launch application "Minesweeper"
  activate application "Minesweeper"
end tell'
            expert
            say "game $i"
            sleep 0.2
            ## move cursor away from the board
            curl 'localhost:8888/mousemove?x=864&y=183' -o /dev/null 2>/dev/null
            echo "game $i" >> ${DEBUGFILE}
            ./play.py 8888 $MODE $SCREENCAP 500 $REFRESH_BOARD native 2>> ${DEBUGFILE} | tee -a "${LOGFILE}"
            tail -1 "${LOGFILE}" | awk '/solved/{system("say game solved")}/exploded/{system("say game exploded")}'
            osascript -e 'quit application "Minesweeper"'
            sleep 0.2
            i="$((i + 1))"
        done
    done
done
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

click(1217, 22);
click(1217, 22);
click(1217, 22);
click(1255, 21);
click(1255, 21);
click(1255, 21);
' | jshell -s >/dev/null 2>&1

## run.sh ends here
