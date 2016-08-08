#!/usr/bin/env sh
echo $DISPLAY
kill $(pgrep -f habitjewel.py)
cd /home/user/src/python/habitjewel/src/opt/habitjewel
/usr/bin/nohup ./habitjewel.py
