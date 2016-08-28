## This module contains some functions reused in the habitjewel application ##

import gtk, gobject
import os
import hildon
import datetime

##Return the details of all habits for the current view date
##return a list similar to [(1, 'Meditate', 'minutes', 'minute', 'minutes', 30, ... )]
def get_habits_list_for_date(conn, view_date_dt):

    # Convert between python datetime (sunday=0) and gtk calendar (monday=0)
    view_week_day_num = str((int(view_date_dt.strftime("%w")) + 7 - 1) % 7)

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
            priority,
            h.created_date,
            paused_until_date,
            h.deleted_date
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
                AND IFNULL(h.paused_until_date, ?) <= ?
                AND IFNULL(h.deleted_date, ?) > ?
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
            ORDER BY CASE
                -- Sort unfulfilled or completed habits to bottom
                WHEN interval_code = 'DAY'
                    AND IFNULL(hsd.percent_complete, -1) NOT IN (0, 100) THEN 0
                WHEN interval_code = 'WEEK'
                    AND IFNULL(hsw.percent_complete, -1) NOT IN (0, 100) THEN 0
                WHEN interval_code = 'MONTH'
                    AND IFNULL(hsm.percent_complete, -1) NOT IN (0, 100) THEN 0
                ELSE 1
            END, priority, h.activity
        """, [view_date_dt,   # join hsd
                view_date_dt, # join hsw
                view_date_dt, # join hsm
                view_date_dt, view_date_dt, # created date
                view_date_dt, view_date_dt, # paused until date
                view_date_dt + datetime.timedelta(days=1), view_date_dt, # deleted date
                '%' + view_week_day_num + '%', # limit week day nums
                view_date_dt, # weekly interval
                view_date_dt  # monthly interval
                ]
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
            'priority':             row[14], \
            'created_date':         row[15], \
            'paused_until_date':    row[16], \
            'deleted_date':         row[17] \
        }
        habits_list.append(habit)

    return habits_list


def get_habits_list_all(conn):

    habits_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.activity, m.desc, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
            interval_code, interval,
            limit_week_day_nums,
            points, 
            priority,
            h.created_date,
            paused_until_date,
            h.deleted_date
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
        """, []
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
            'interval_code':        row[7], \
            'interval':             row[8], \
            'limit_week_day_nums':  row[9], \
            'points':               row[10], \
            'priority':             row[11], \
            'created_date':         row[12], \
            'paused_until_date':    row[13], \
            'deleted_date':         row[14] \
        }
        habits_list.append(habit)

    return habits_list


def save_habit(conn, habit):

    activity = habit['activity']
    target = habit['target']
    measure_desc = habit['measure_desc']
    interval_code = habit['interval_code']
    interval = habit['interval']
    limit_week_day_nums = habit['limit_week_day_nums']

    # Do we already have a habit id? i.e. editing existing habit
    if 'id' in habit:
        habit_id = habit['id']

        conn.execute(
            """
            UPDATE habits
               SET activity = ?, target = ?,
                       measure_id = (SELECT id FROM measures WHERE desc = ?),
                       interval_code = ?, interval = ?, limit_week_day_nums = ?,
                       paused_until 
             WHERE id = ?
            """, [activity, target, measure_desc, \
                    interval_code, interval, limit_week_day_nums, \
                    habit_id])

    # If not, insert a new habit
    else:

        conn.execute(
            """
            INSERT INTO habits (activity, target, measure_id, interval_code,
                    interval, limit_week_day_nums, created_date)
                VALUES (?, ?, (SELECT id FROM measures WHERE desc = ?),
                    ?, ?, ?, CURRENT_DATE)
            """, [activity, target, measure_desc, \
                    interval_code, interval, limit_week_day_nums])


    conn.commit()


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
    cursor = conn.execute(
        """
        SELECT DISTINCT h.id, h.activity, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS goal,
            interval_code,
            interval,
            m.id, m.desc, m.unit, m.plural,
            created_date,
            paused_until_date,
            deleted_date
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
            WHERE habit_id = ?
        """, [habit_id]
    )

    habit = cursor.fetchone()
    
    return habit


def set_habit_pct_complete (conn, habit_id, view_date_dt, percent):
    cursor = conn.execute(
        """
        SELECT interval_code FROM habits WHERE id = ?
        """, [habit_id]
    )
    interval_code = cursor.fetchone()[0]

    if interval_code == 'DAY':
        conn.execute(
            """
            INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                VALUES ((SELECT id FROM history WHERE habit_id = ? AND date = ?),
                    ?, ?, ?)
            """, [habit_id, view_date_dt, habit_id, view_date_dt, percent])
        conn.commit()
    elif interval_code == 'WEEK' or interval_code == 'MONTH':
        conn.execute(
            """
            INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                VALUES ((SELECT id FROM history
                            WHERE habit_id = ?
                            AND STRFTIME('%W', date) = STRFTIME('%W', ?)),
                    ?, DATE(?, 'weekday 0', '-6 day'), ?)
            """, [habit_id, view_date_dt, habit_id, view_date_dt, percent])
        conn.commit()


def set_habit_paused_until_date (conn, habit_id, paused_until_date):
    conn.execute(
        """
        UPDATE habits
           SET paused_until_date = ?
         WHERE id = ?
        """, [paused_until_date, habit_id])
    conn.commit()


def delete_habit (conn, habit_id):
    conn.execute(
        """
        UPDATE habits
           SET deleted_date = CURRENT_DATE
         WHERE id = ?
        """, [habit_id])
    conn.commit()
