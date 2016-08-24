#!/usr/bin/env sh
# Kill habitjewel if it is running
kill $(pgrep -f habitjewel.py) 2>/dev/null
# Relaunch habitjewel
cd /home/user/src/python/n900/habitjewel/src/opt/habitjewel
./habitjewel.py &
