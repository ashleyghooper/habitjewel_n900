## This module contains some functions reused in the habitjewel application ##

import gtk, gobject
import os
import hildon

fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL

##Return the details of all the habits in the database
##return a list similar to [(1, 'Meditate', 'minutes', 'minute', 'minutes', 30, ... )]
def get_habits_list(conn, view_date):
    view_week_day_num = view_date.strftime("%w")

    habits_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.activity, m.desc, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
            CASE interval_code
                WHEN 'DAY' THEN 'today'
                WHEN 'WEEK' THEN 'this week'
                ELSE 'this month'
            END AS by_when,
            interval_code, interval,
            limit_week_day_nums,
            points, 
            CASE interval_code
                WHEN 'DAY' THEN IFNULL(hsd.percent_complete, -1)
                WHEN 'WEEK' THEN IFNULL(hsw.percent_complete, -1)
                ELSE IFNULL(hsm.percent_complete, -1)
            END AS percent_complete,
            CASE interval_code
                WHEN 'DAY' THEN IFNULL(points * hsd.percent_complete, 0)
                WHEN 'WEEK' THEN IFNULL(points * hsw.percent_complete, 0)
                ELSE IFNULL(points * hsm.percent_complete, 0)
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
                LEFT JOIN history hsm
                    ON hsm.habit_id = h.id
                         AND STRFTIME('%M', hsm.date) = STRFTIME('%M', ?)
            WHERE IFNULL(h.created_date, ?) <= ?
                AND IFNULL(h.deleted_date, ?) >= ?
                AND (
                        (   interval_code = 'DAY'
                        AND (   limit_week_day_nums IS NULL
                             OR limit_week_day_nums LIKE ?)
                        )
                     OR (   interval_code = 'WEEK'
                        AND STRFTIME('%W', ?) % interval = 0)
                     OR (   interval_code = 'MONTH'
                        AND STRFTIME('%M', ?) % interval = 0)
                    )
            ORDER BY priority, h.activity
        """, [view_date, view_date, view_date, view_date, view_date, \
                view_date, view_date, \
                '%' + view_week_day_num + '%', \
                view_date, view_date]
    ):

        # habits_list.append(row)

        habit = { \
            'id':                   row[0], \
            'activity':             row[1], \
            'measure_desc':         row[2], \
            'unit':                 row[3], \
            'plural':               row[4], \
            'target':               row[5], \
            'target_desc':          row[6], \
            'by_when':              row[7], \
            'interval_code':        row[8], \
            'interval':             row[9], \
            'limit_week_day_nums':  row[10], \
            'points':               row[11], \
            'pct_complete':         row[12], \
            'score':                row[13], \
            'priority':             row[14] \
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


def get_interval_types_list(conn):

    interval_types_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT id, code, desc, created_date, deleted_date
            FROM interval_types
            ORDER BY id
        """
    ):

        interval_type = { \
            'id':               row[0], \
            'code':             row[1], \
            'desc':             row[2], \
            'created_date':     row[3], \
            'deleted_date':     row[4]
        }
        interval_types_list.append(interval_type)

    return interval_types_list


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
            'activity':         row[1], \
            'created_date':     row[2], \
            'deleted_date':     row[3]
        }
        categories_list.append(category)

    return categories_list


def get_habit_details(conn, habit_id):
    habit = conn.execute(
        """
        SELECT DISTINCT h.id, h.activity, unit, plural, target,
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
