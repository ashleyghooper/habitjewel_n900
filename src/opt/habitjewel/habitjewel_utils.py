## This module contains some functions reused in the habitjewel application ##

import gtk, gobject
import os
import hildon

fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL

##Return the titles and ids of the all recipes in the database
##return a list similar to [(1, 'recipe1'), (2, 'recipe2')]
def get_habits_list(conn, view_date):
    view_day_abbrev = view_date.strftime("%a")

    habits_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.title, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
            CASE interval_type
                WHEN 'Day' THEN 'today'
                ELSE 'this week'
            END AS by_when,
            interval_type, interval,
            points, 
            CASE interval_type
                WHEN 'Day' THEN IFNULL(hsd.percent_complete, -1)
                ELSE IFNULL(hsw.percent_complete, -1)
            END AS percent_complete,
            CASE interval_type
                WHEN 'Day' THEN IFNULL(points * hsd.percent_complete, 0)
                ELSE IFNULL(points * hsw.percent_complete, 0)
            END AS score,
            priority
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
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
            '%' + view_day_abbrev + '%', view_date]
    ):

        habit = { \
            'id':               row[0], \
            'title':            row[1], \
            'unit':             row[2], \
            'plural':           row[3], \
            'target':           row[4], \
            'target_desc':      row[5], \
            'by_when':          row[6], \
            'interval_type':    row[7], \
            'interval':         row[8], \
            'points':           row[9], \
            'pct_complete':     row[10], \
            'score':            row[11], \
            'priority':         row[12] \
        }
        habits_list.append(habit)

    return habits_list


def get_measures_list(conn):

    measures_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT id, unit, plural, desc, created_date, deleted_date
            FROM measures
            ORDER BY unit
        """
    ):

        measure = { \
            'id':               row[0], \
            'unit':             row[1], \
            'plural':           row[2], \
            'desc':             row[3], \
            'created_date':     row[4], \
            'deleted_date':     row[5]
        }
        measures_list.append(measure)

    return measures_list


def get_categories_list(conn):

    categories_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT id, title, created_date, deleted_date
            FROM categories
            ORDER BY title
        """
    ):

        category = { \
            'id':               row[0], \
            'title':            row[1], \
            'created_date':     row[2], \
            'deleted_date':     row[3]
        }
        categories_list.append(category)

    return categories_list


def get_habit_details(conn, habit_id):
    habit = conn.execute(
        """
        SELECT DISTINCT h.id, h.title, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS goal,
            interval_type,
            interval,
            m.id, m.desc, m.unit, m.plural,
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
            WHERE habit_id = ?
        """, [habit_id]
    )
    
    return habit


def set_fulfillment_status (conn, habit_id, interval_type, view_date, percent):
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
