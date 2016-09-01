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
        SELECT DISTINCT h.id, h.activity,
            weekly_quota,
            points, 
            IFNULL(hs.percent_complete, -1) AS percent_complete,
            IFNULL((SELECT SUM(IFNULL(percent_complete, 0)) * 0.01 FROM history WHERE habit_id = h.id AND STRFTIME('%W', date) = STRFTIME('%W', ?)), 0) AS progress,
            IFNULL((points * hs.percent_complete) * 0.01, 0) AS score,
            priority,
            m.desc,
            null_measure,
            unit, plural,
            target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
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
                WHEN SUM(IFNULL(hs.percent_complete, 0)) * 0.01 >= weekly_quota THEN 2
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
            'weekly_quota':         row[2], \
            'points':               row[3], \
            'pct_complete':         row[4], \
            'progress':             row[5], \
            'score':                row[6], \
            'priority':             row[7], \
            'measure_desc':         row[8], \
            'null_measure':         row[9], \
            'unit':                 row[10], \
            'plural':               row[11], \
            'target':               row[12], \
            'target_desc':          row[13], \
            'created_date':         row[14], \
            'paused_until_date':    row[15], \
            'deleted_date':         row[16] \
        }
        habits_list.append(habit)

    return habits_list


def get_habits_list_all(conn):

    habits_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT h.id, h.activity,
            weekly_quota,
            points, 
            priority,
            m.desc,
            null_measure,
            unit, plural,
            target,
            target || ' ' || CASE WHEN target > 1 THEN plural ELSE unit END AS target_desc,
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
            'weekly_quota':         row[2], \
            'points':               row[3], \
            'priority':             row[4], \
            'measure_desc':         row[5], \
            'null_measure':         row[6], \
            'unit':                 row[7], \
            'plural':               row[8], \
            'target':               row[9], \
            'target_desc':          row[10], \
            'created_date':         row[11], \
            'paused_until_date':    row[12], \
            'deleted_date':         row[13] \
        }
        habits_list.append(habit)

    return habits_list


def save_habit(conn, habit):

    activity = habit['activity']
    weekly_quota = habit['weekly_quota']
    measure_desc = habit['measure_desc']
    priority = habit['priority']
    target = habit['target']
    paused_until_date = habit['paused_until_date']
    deleted_date = habit['deleted_date']

    # Do we already have a habit id? i.e. editing existing habit
    if 'id' in habit:
        habit_id = habit['id']

        conn.execute(
            """
            INSERT INTO habits_a
                SELECT DATETIME('now'),
                    *
                  FROM habits
                 WHERE id = ?
            """, [habit_id])

        conn.execute(
            """
            UPDATE habits
               SET activity = ?,
                   weekly_quota = ?,
                   measure_id = (SELECT id FROM measures WHERE desc = ?),
                   priority = ?,
                   target = ?,
                   paused_until_date = ?,
                   deleted_date = ?
             WHERE id = ?
            """, [activity, weekly_quota, measure_desc, \
                    priority, target, paused_until_date, deleted_date, \
                    habit_id])

    # If not, insert a new habit
    else:

        conn.execute(
            """
            INSERT INTO habits (activity, weekly_quota, measure_id, priority, target,
                    created_date)
                VALUES (?, ?, (SELECT id FROM measures WHERE desc = ?),
                    ?, ?, CURRENT_DATE)
            """, [activity, weekly_quota, measure_desc, priority, target])

    conn.commit()


def get_measures_list(conn):

    measures_list=[]

    for row in conn.execute(
        """
        SELECT DISTINCT id, unit, plural, desc, created_date, deleted_date
            FROM measures
            ORDER BY sort, unit
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


def is_null_measure(conn, measure_desc):
    cursor = conn.execute(
        """
        SELECT null_measure
          FROM measures
         WHERE LOWER(desc) = ?
        """, [measure_desc.lower()])

    row = cursor.fetchone()
    if row[0] == 1:
        return True
    else:
        return False


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
            weekly_quota,
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

    if percent != -1:
        conn.execute(
            """
            INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                VALUES ((SELECT id FROM history
                            WHERE habit_id = ?
                            AND date = ?),
                    ?, ?, ?)
            """, [habit_id, view_date_dt, habit_id, view_date_dt, percent])

    else:
        conn.execute(
            """
            DELETE FROM history
             WHERE habit_id = ?
               AND date = ?
            """, [habit_id, view_date_dt])

    conn.commit()


def set_habit_paused_until_date (conn, habit_id, paused_until_date):
    conn.execute(
        """
        UPDATE habits
           SET paused_until_date = ?
         WHERE id = ?
        """, [paused_until_date, habit_id])
    conn.commit()


def delete_habit(conn, habit_id):
    conn.execute(
        """
        UPDATE habits
           SET deleted_date = CURRENT_DATE
         WHERE id = ?
        """, [habit_id])
    conn.commit()


def create_new_database(conn):
    cursor = conn.cursor()

    # Table to track schema changes for upgrading between incompatible versions
    cursor.execute(
        """
        CREATE TABLE schema_version_history (id INTEGER PRIMARY KEY,
            major INTEGER, minor INTEGER, patch INTEGER,
            result TEXT, install_date DATE)
        """)

    # Insert a row for the current schema version
    cursor.execute(
        """
        INSERT INTO schema_version_history (major, minor, patch,
            result, install_date)
            VALUES (0, 4, 0, 'OK', CURRENT_DATE)
        """)

    # Table to track goals
    cursor.execute(
        """
        CREATE TABLE goals (id INTEGER PRIMARY KEY, title TEXT,
            priority INTEGER, category_id INTEGER, due_date DATE,
            points_threshold INTEGER, created_date DATE, deleted_date DATE)
        """)

    # Table to track habits (which may optionally belong to goals)
    cursor.execute(
        """
        CREATE TABLE habits (id INTEGER PRIMARY KEY,
            activity TEXT,
            weekly_quota INTEGER,
            priority INTEGER,
            measure_id INTEGER,
            target INTEGER,
            points INTEGER,
            goal_id INTEGER,
            created_date DATE,
            paused_until_date DATE,
            deleted_date DATE)
        """)

    # Habits audit table, to help with calculating stats when habits have changed
    cursor.execute(
        """
        CREATE TABLE habits_a (update_date DATE,
            id INTEGER,
            activity TEXT,
            weekly_quota INTEGER,
            priority INTEGER,
            measure_id INTEGER,
            target INTEGER,
            points INTEGER,
            goal_id INTEGER,
            created_date DATE,
            paused_until_date DATE,
            deleted_date DATE)
        """)

    # Categories - not really used at present, but could be useful for stats
    cursor.execute(
        """
        CREATE TABLE categories (id INTEGER PRIMARY KEY, title TEXT,
            created_date DATE, deleted_date DATE)
        """)

    # History - this is where we record which habits were fully or partially completed,
    # or missed
    cursor.execute(
        """
        CREATE TABLE history (id INTEGER PRIMARY KEY, habit_id INTEGER, date DATE,
            percent_complete INTEGER)
        """)

    # Measures - this is where the types of measures habits can have are defined
    cursor.execute(
        """
        CREATE TABLE measures (id INTEGER PRIMARY KEY, unit TEXT, plural TEXT, desc TEXT,
            sort INTEGER, null_measure INTEGER, created_date DATE, deleted_date DATE)
        """)

    # Define some sample categories
    cursor.execute(
        """
        INSERT INTO categories (title, created_date) VALUES (?, CURRENT_DATE)
        """, ['Mental'])
    cursor.execute(
        """
        INSERT INTO categories (title, created_date) VALUES (?, CURRENT_DATE)
        """, ['Exercise'])
    cursor.execute(
        """
        INSERT INTO categories (title, created_date) VALUES (?, CURRENT_DATE)
        """, ['Academic'])

    # Define the default set of measures
    # None (Special measure for habits with no useful measure, e.g. "Bake a cake")
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, null_measure, created_date) VALUES (?, ?, ?, ?, ?, CURRENT_DATE)
        """, ['none', 'none', '(None)', 0, 1])
    # Minutes
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, created_date) VALUES (?, ?, ?, ?, CURRENT_DATE)
        """, ['min', 'mins', 'minute', 1])
    # Hours
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, created_date) VALUES (?, ?, ?, ?, CURRENT_DATE)
        """, ['hour', 'hours', 'hour', 1])
    # Kilometres
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, created_date) VALUES (?, ?, ?, ?, CURRENT_DATE)
        """, ['km', 'kms', 'kilometre', 1])
    # Miles
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, created_date) VALUES (?, ?, ?, ?, CURRENT_DATE)
        """, ['mile', 'miles', 'mile', 1])
    # Words
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, sort, created_date) VALUES (?, ?, ?, ?, CURRENT_DATE)
        """, ['word', 'words', 'words', 1])

    # A sample habit
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            weekly_quota, points, created_date)
            VALUES (?, 1, NULL, 2, 4, 100, CURRENT_DATE)
        """, ['Go for a run'])

    # A sample habit
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            weekly_quota, points, created_date)
            VALUES (?, 4, 2, 3, 4, 100, CURRENT_DATE)
        """, ['Walk'])

    # A sample habit
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            weekly_quota, points, created_date)
            VALUES (?, 2, 30, 1, 5, 100, CURRENT_DATE)
        """, ['Study'])

    conn.commit()
    cursor.close()
