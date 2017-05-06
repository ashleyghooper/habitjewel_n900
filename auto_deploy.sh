#!/bin/sh

# Script to auto-deploy source code to N900 when files are created/updated

# get the current path
current_path=`pwd`

# set the project path
local_project_path=$HOME/src/python/n900/habitjewel/
remote_host=n900-usb
remote_project_path=/home/user/src/python/n900/habitjewel/

# set the event_epoch_time
last_event_epoch=$(date +%s)

# change to the project path
cd $local_project_path

echo "Waiting for file updates in $local_project_path to deploy to $remote_host"

inotifywait -r -mq --timefmt '%s' --format '%T %w %f %e' \
    -e modify . --exclude '(.*\.sw.|\.git)' | while read epoch dir file event
do
    echo "File update event seen for ${dir}${file}"
    event=${event}
    affected_file=${dir}${file}
    event_epoch=${epoch}
    difference=$(expr $event_epoch - $last_event_epoch)
    date=$(date +%d/%m/%Y)
    time=$(date +%H:%M:%S)
    if [ $difference -gt 2 ]; then
        last_event_epoch=${event_epoch}
        rsync --bwlimit=30 $affected_file $remote_host:$remote_project_path/${dir}
        ssh -f $remote_host "source /etc/osso-af-init/af-defines.sh && /bin/sh $remote_project_path/auto_restart.sh"
        echo "At ${time} on ${date}, file ${file} was copied to $remote_host"
    else
        echo "Ignoring duplicate event!"
    fi
done
