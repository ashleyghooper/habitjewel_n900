#!/bin/sh

# Script to auto-deploy source code to N900 when files are created/updated

# get the current path
current_path=`pwd`

# set the project path
local_project_path=$HOME/src/python/n900/habitjewel/
remote_project_path=/home/user/src/python/habitjewel/

# change to the project path
cd $local_project_path

inotifywait -mq --timefmt '%d/%m/%y %H:%M' --format '%T %w %f' \
    -e modify . --exclude '.*.swp' | while read date time dir file
do

    file_update_event=${dir}${file}
    scp $file_update_event n900-usb:/home/user/src/python/habitjewel/
    ssh n900-usb "/bin/sh -l $remote_project_path/auto_restart.sh"
    echo "At ${time} on ${date}, file ${file} was copied to N900"
done
