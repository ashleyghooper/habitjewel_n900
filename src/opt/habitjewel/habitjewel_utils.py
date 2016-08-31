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
            IFNULL((SELECT SUM(IFNULL(percent_complete, 0)) * 0.01 FROM history WHERE habit_id = h.id AND STRFTIME('%W', date) = STRFTIME('%W', ?)), 0) AS progress,
            frequency,
            points, 
            IFNULL(hs.percent_complete, -1) AS percent_complete,
            IFNULL((points * hs.percent_complete) * 0.01, 0) AS score,
            priority,
            h.created_date,
            paused_until_date,
            h.deleted_date
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
                LEFT JOIN history hs
                    ON hs.habit_id = h.id
                         AND hs.date = ?
            WHERE IFNULL(h.created_date, ?) <= ?
                AND IFNULL(h.paused_until_date, ?) <= ?
                AND IFNULL(h.deleted_date, ?) > ?
            ORDER BY CASE
                -- Sort habits with partial/unknown completion to top
                WHEN IFNULL(hs.percent_complete, -1) NOT IN (0, 100) THEN 0
                -- Sort fulfilled habits to bottom
                WHEN SUM(IFNULL(hs.percent_complete, 0)) * 0.01 >= frequency THEN 2
                -- Any others in between
                ELSE 1
            END, priority, h.activity
        """, [view_date_dt,   # subquery
                view_date_dt,   # join history
                view_date_dt, view_date_dt, # created date
                view_date_dt, view_date_dt, # paused until date
                view_date_dt + datetime.timedelta(days=1), view_date_dt # deleted date
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
            'progress':             row[7], \
            'frequency':            row[8], \
            'points':               row[9], \
            'pct_complete':         row[10], \
            'score':                row[11], \
            'priority':             row[12], \
            'created_date':         row[13], \
            'paused_until_date':    row[14], \
            'deleted_date':         row[15] \
        }
        habits_list.append(habit)

    return habits_list


def get_habits_list_all(conn):

    habits_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.activity, m.desc, unit, plural, target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
            frequency,
            points, 
            priority,
            h.created_date,
            paused_until_date,
            h.deleted_date
            FROM habits h
                JOIN measures m
                    ON m.id = h.measure_id
            ORDER BY CASE
                -- Sort unfulfilled or completed habits to bottom
                WHEN h.deleted_date IS NOT NULL THEN 2 
                WHEN paused_until_date IS NOT NULL THEN 0
                ELSE 1
            END, priority, h.activity
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
            'frequency':            row[7], \
            'points':               row[8], \
            'priority':             row[9], \
            'created_date':         row[10], \
            'paused_until_date':    row[11], \
            'deleted_date':         row[12] \
        }
        habits_list.append(habit)

    return habits_list


def save_habit(conn, habit):

    activity = habit['activity']
    target = habit['target']
    measure_desc = habit['measure_desc']
    frequency = habit['frequency']
    paused_until_date = habit['paused_until_date']
    deleted_date = habit['deleted_date']

    # Do we already have a habit id? i.e. editing existing habit
    if 'id' in habit:
        habit_id = habit['id']

        conn.execute(
            """
            INSERT INTO habits_a
                SELECT DATETIME('now', 'localtime'),
                    *
                  FROM habits
                 WHERE id = ?
            """, [habit_id])

        conn.execute(
            """
            UPDATE habits
               SET activity = ?, target = ?,
                       measure_id = (SELECT id FROM measures WHERE desc = ?),
                       frequency = ?,
                       paused_until_date = ?, deleted_date = ?
             WHERE id = ?
            """, [activity, target, measure_desc, \
                    frequency, \
                    paused_until_date, deleted_date, \
                    habit_id])

    # If not, insert a new habit
    else:

        conn.execute(
            """
            INSERT INTO habits (activity, target, measure_id,
                    frequency, created_date)
                VALUES (?, ?, (SELECT id FROM measures WHERE desc = ?),
                    ?, ?, CURRENT_DATE)
            """, [activity, target, measure_desc, \
                    frequency])


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
            frequency,
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
    conn.execute(
        """
        INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
            VALUES ((SELECT id FROM history
                        WHERE habit_id = ?
                        AND date = ?),
                ?, ?, ?)
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
