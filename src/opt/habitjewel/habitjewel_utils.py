## This module contains some functions reused in the habitjewel application ##

import gtk, gobject
import os
import hildon

fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL

##Return the titles and ids of the all recipes in the database
##return a list similar to [(1, 'recipe1'), (2, 'recipe2')]
def get_habit_list(conn, view_date):
    view_day_abbrev = view_date.strftime("%a")
    rows = []
    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.title, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS goal,
            CASE interval_type
                WHEN 'Day' THEN 'today'
                ELSE 'this week'
            END AS by_when,
            interval_type, interval,
            points, 
            CASE interval_type
                WHEN 'Day' THEN IFNULL(hsd.percent_complete, 0)
                ELSE IFNULL(hsw.percent_complete, 0)
            END AS percent_complete,
            CASE interval_type
                WHEN 'Day' THEN IFNULL(points * hsd.percent_complete, 0)
                ELSE IFNULL(points * hsw.percent_complete, 0)
            END AS score,
            priority, c.id, c.title
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
                JOIN categories c
                    ON c.id = h.category_id
                LEFT JOIN history hsd
                    ON hsd.habit_id = h.id
                         AND hsd.date = ?
                LEFT JOIN history hsw
                    ON hsw.habit_id = h.id
                         AND STRFTIME('%W', hsw.date) = STRFTIME('%W', ?)
            WHERE IFNULL(h.created_date, ?) <= ?
                AND IFNULL(h.deleted_date, ?) >= ?
                AND (
                        (   interval_type = 'Day'
                        AND interval LIKE ?)
                     OR (   interval_type = 'Week'
                        AND STRFTIME('%W', ?) % interval = 0)
                )
            ORDER BY priority, h.title
        """, [view_date, view_date, view_date, view_date, view_date, view_date, \
            '%' + view_day_abbrev + '%', view_date]):
        rows.append(row)

    habit_list=[]

    for i in range(len(rows)):
        id = rows[i][0]
        title = rows[i][1]
        unit = rows[i][2]
        plural = rows[i][3]
        target = rows[i][4]
        goal = rows[i][5]
        by_when = rows[i][6]
        interval_type = rows[i][7]
        interval = rows[i][8]
        points = rows[i][9]
        pct_complete = rows[i][10]
        score = rows[i][11]
        priority = rows[i][12]
        cat_id = rows[i][13]
        cat_title = rows[i][14]

        habit = (id, title, unit, plural, target, goal, by_when, interval_type, interval, \
            points, pct_complete, score, priority, cat_id, cat_title)
        habit_list.append(habit)

    return habit_list


def set_percent_complete (conn, habit_id, interval_type, view_date, percent):
    if (interval_type == 'Day'):
        conn.execute(
            """
            INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                VALUES ((SELECT id FROM history WHERE habit_id = ? AND date = ?),
                    ?, ?, ?)
            """, [habit_id, view_date, habit_id, view_date, percent])
    else:
        conn.execute(
            """
            INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                VALUES ((SELECT id FROM history
                            WHERE habit_id = ?
                            AND STRFTIME('%W', date) = STRFTIME('%W', ?)),
                    ?, DATE(?, 'weekday 0', '-6 day'), ?)
            """, [habit_id, view_date, habit_id, view_date, percent])
    conn.commit()


def is_portrait():
    width = gtk.gdk.screen_width()
    height = gtk.gdk.screen_height()
    if width > height:
        return False
    else:
        return True


#Show the hildon.filechooser dialog to open/save a file.
def show_filechooser_dialog(window, action, title, name, format, EXT):
    if action == 'open':
        action = gtk.FILE_CHOOSER_ACTION_OPEN
    elif action == 'save':
        action = gtk.FILE_CHOOSER_ACTION_SAVE

    m = hildon.FileSystemModel()
    file_dialog = hildon.FileChooserDialog(window, action, m)
    file_dialog.set_title(title + format)

    portrait = is_portrait()
    if portrait:
        hildon.hildon_gtk_window_set_portrait_flags(file_dialog, 1)

    file_dialog.set_current_name(name)
    HOME = os.path.expanduser("~")

    if os.path.exists(HOME + '/MyDocs/.documents'):
        file_dialog.set_current_folder(HOME + '/MyDocs/.documents')
    else:
        file_dialog.set_current_folder(HOME)

    file_dialog.set_default_response(gtk.RESPONSE_CANCEL)

    result = file_dialog.run()
    if result == gtk.RESPONSE_OK:
        namefile = file_dialog.get_filename()
        if (action==gtk.FILE_CHOOSER_ACTION_SAVE):
            namefile = file_dialog.get_filename()
            namefile, extension = os.path.splitext(namefile)
            namefile = namefile + "." + EXT

    else:
        namefile = None
    file_dialog.destroy()

    return namefile