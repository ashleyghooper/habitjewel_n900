## This module contains some functions reused in the habitjewel application ##

import datetime
import gtk, gobject
import hildon
import os
import sqlite3

# For backing up database before schema upgrade
from shutil import copyfile


class HabitJewelDb:

    def __init__(self, config_dir, code_version):

        # Check the code version is in correct format
        if code_version.count('.') == 2:
            code_schema_ver = '.'.join(code_version.split('.')[0:2])
        else:
            print 'Version ' + code_version + ' not in valid format (x.y.z)'
            sys.exit(-1)

        # Prepare connection
        db_file = config_dir + '/database'

        # Create the database
        if os.path.exists(db_file):
            print 'checking database schema version'
            self.conn = sqlite3.connect(db_file)
            self.check_and_upgrade_schema(db_file, code_schema_ver)
        else:
            print 'creating new database for schema version ' + code_schema_ver
            self.conn = sqlite3.connect(db_file)
            self.create_new_database(code_schema_ver)


    # Iterate through a date range between two dates
    def date_range(self, start_date, end_date):
        if start_date <= end_date:
            for n in range( ( end_date - start_date ).days + 1 ):
                yield start_date + datetime.timedelta( n )
        else:
            for n in range( ( start_date - end_date ).days + 1 ):
                yield start_date - datetime.timedelta( n )

    
    ##Return the details of all habits for the current view date
    ##return a list similar to [(1, 'Meditate', 'minutes', 'minute', 'minutes', 30, ... )]
    def get_habits_list_for_date(self, view_date_dt):
    
        # Convert between python datetime (sunday=0) and gtk calendar (monday=0)
        view_week_day_num = str((int(view_date_dt.strftime("%w")) + 7 - 1) % 7)
    
        habits_list=[]
    
        for h in self.conn.execute(
            """
            SELECT DISTINCT h.id, h.activity,
                weekly_quota,
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
            """, [view_date_dt,   # history
                    view_date_dt, view_date_dt, # created date
                    view_date_dt, view_date_dt, # paused until date
                    view_date_dt + datetime.timedelta(days=1), view_date_dt # deleted date
                    ]
        ):
    
            habit = { \
                'id':                   h[0], \
                'activity':             h[1], \
                'weekly_quota':         h[2], \
                'priority':             h[3], \
                'measure_desc':         h[4], \
                'null_measure':         h[5], \
                'unit':                 h[6], \
                'plural':               h[7], \
                'target':               h[8], \
                'target_desc':          h[9], \
                'created_date':         h[10], \
                'paused_until_date':    h[11], \
                'deleted_date':         h[12] \
            }
    
            day_percent_complete = -1
            view_date_minus_week_dt = view_date_dt - datetime.timedelta(7)
            habit_prec_7d = {}
            # Get rid
            wk_complete_overall = 0

            for wk_hs in self.conn.execute(
                """
                SELECT DISTINCT date,
                                percent_complete,
                                CASE WHEN STRFTIME('%W', date) = STRFTIME('%W', ?) 
                                    THEN 0
                                ELSE
                                    -1
                                END AS week_offset
                  FROM history
                 WHERE habit_id = ?
                   AND date BETWEEN ? AND ?
                 ORDER BY date
                """, [view_date_dt, habit['id'], view_date_minus_week_dt, view_date_dt]
            ):
                pc_date      = wk_hs[0]
                pc_percent   = wk_hs[1]
                pc_wk_offset = wk_hs[2]
                habit_prec_7d[pc_date] = [pc_percent, pc_wk_offset]
                # If history record is for the current day, set it
                if pc_date == view_date_dt.strftime('%Y-%m-%d'):
                    day_percent_complete = pc_percent

            completion_by_day = []
            for day_dt in self.date_range(view_date_minus_week_dt, view_date_dt):
                db_date = day_dt.strftime('%Y-%m-%d')
                if db_date in habit_prec_7d:
                    completion_by_day.append(habit_prec_7d[db_date])
                    if habit_prec_7d[db_date][1] == 0:
                        wk_complete_overall += habit_prec_7d[db_date][0] * 0.01
                else:
                    completion_by_day.append([])

            habit['pct_complete'] = day_percent_complete
            habit['completion_by_day'] = completion_by_day
            habit['wk_complete_overall'] = wk_complete_overall

            # Add the habit to the list
            habits_list.append(habit)
    
        return habits_list
    
    
    def get_habits_list_all(self):
    
        habits_list=[]
    
        for row in self.conn.execute(
            """
            SELECT DISTINCT h.id, h.activity,
                weekly_quota,
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
                'priority':             row[3], \
                'measure_desc':         row[4], \
                'null_measure':         row[5], \
                'unit':                 row[6], \
                'plural':               row[7], \
                'target':               row[8], \
                'target_desc':          row[9], \
                'created_date':         row[10], \
                'paused_until_date':    row[11], \
                'deleted_date':         row[12] \
            }
            habits_list.append(habit)
    
        return habits_list
    
    
    def save_habit(self, habit):
    
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
    
            self.conn.execute(
                """
                INSERT INTO habits_a
                    SELECT DATETIME('now'),
                        *
                      FROM habits
                     WHERE id = ?
                """, [habit_id])
    
            self.conn.execute(
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
    
            self.conn.execute(
                """
                INSERT INTO habits (activity, weekly_quota, measure_id, priority, target,
                        created_date)
                    VALUES (?, ?, (SELECT id FROM measures WHERE desc = ?),
                        ?, ?, CURRENT_DATE)
                """, [activity, weekly_quota, measure_desc, priority, target])
    
        self.conn.commit()
    
    
    def clone_habit(self, habit_id, new_activity):
        self.conn.execute(
            """
            INSERT INTO habits
                SELECT NULL,
                    ?,
                    weekly_quota,
                    priority,
                    measure_id,
                    target,
                    goal_id,
                    CURRENT_DATE,
                    NULL,
                    NULL
                  FROM habits
                 WHERE id = ?
            """, [new_activity, habit_id])
    
        self.conn.commit()
    
    
    def get_measures_list(self):
    
        measures_list=[]
    
        for row in self.conn.execute(
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
    
    
    def get_measure(self, measure_desc):
        cursor = self.conn.execute(
            """
            SELECT id, unit, plural
              FROM measures
             WHERE LOWER(desc) = ?
            """, [measure_desc.lower()])
    
        row = cursor.fetchone()
    
        return row
    
    
    def is_null_measure(self, measure_desc):
        cursor = self.conn.execute(
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
    
    
    def get_categories_list(self):
    
        categories_list=[]
    
        for row in self.conn.execute(
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
    
    
    def get_habit_details(self, habit_id):
        cursor = self.conn.execute(
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
    
    
    def set_habit_pct_complete (self, habit_id, view_date_dt, percent):
    
        if percent != -1:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO history (id, habit_id, date, percent_complete)
                    VALUES ((SELECT id FROM history
                                WHERE habit_id = ?
                                AND date = ?),
                        ?, ?, ?)
                """, [habit_id, view_date_dt, habit_id, view_date_dt, percent])
    
        else:
            self.conn.execute(
                """
                DELETE FROM history
                 WHERE habit_id = ?
                   AND date = ?
                """, [habit_id, view_date_dt])
    
        self.conn.commit()
    
    
    def set_habit_paused_until_date (self, habit_id, paused_until_date):
        self.conn.execute(
            """
            UPDATE habits
               SET paused_until_date = ?
             WHERE id = ?
            """, [paused_until_date, habit_id])
        self.conn.commit()
    
    
    def delete_habit(self, habit_id):
        self.conn.execute(
            """
            UPDATE habits
               SET deleted_date = CURRENT_DATE
             WHERE id = ?
            """, [habit_id])
        self.conn.commit()
    
    
    def add_schema_version_history(self, code_schema_ver):
        code_schema_ver_arr = code_schema_ver.split('.')
        major = code_schema_ver_arr[0]
        minor = code_schema_ver_arr[1]
    
        # Insert a row for the current schema version
        self.conn.execute(
            """
            INSERT INTO schema_version_history (major, minor, patch,
                result, install_date)
                VALUES (?, ?, 0, 'OK', CURRENT_DATE)
            """, [major, minor])
        self.conn.commit()
    
    
    def check_and_upgrade_schema(self, db_file, code_schema_ver):
        # Get current schema version
        cursor = self.conn.execute(
            """
            SELECT major,
                   minor
              FROM schema_version_history
             ORDER BY major DESC
                   , minor DESC
            """)
    
        # Get the highest version only
        row = cursor.fetchone()
        db_schema_ver = str(row[0]) + '.' + str(row[1])
        
        if db_schema_ver == code_schema_ver:
            print 'Database schema version (' + db_schema_ver + ') is up to date for this version'
            return
    
        else:
            if db_schema_ver == '0.5' or db_schema_ver == '0.4':
        
                cursor.close()
                self.conn.close()
                print "Backing up current database..."
                copyfile(db_file, db_file + '_ver_' + db_schema_ver + '.backup')

                self.conn = sqlite3.connect(db_file)
                print 'Upgrading database schema to version ' + code_schema_ver + '...'

                # Remove points column from habits audit table
                cursor = self.conn.executescript(
                    """
                    BEGIN TRANSACTION;
                    CREATE TEMPORARY TABLE habits_a_tmp(
                        update_date DATE,
                        id INTEGER,
                        activity TEXT,
                        weekly_quota INTEGER,
                        priority INTEGER,
                        measure_id INTEGER,
                        target INTEGER,
                        goal_id INTEGER,
                        created_date DATE,
                        paused_until_date DATE,
                        deleted_date DATE);
                    INSERT INTO habits_a_tmp
                        SELECT update_date,
                               id,
                               activity,
                               weekly_quota,
                               priority,
                               measure_id,
                               target,
                               goal_id,
                               created_date,
                               paused_until_date,
                               deleted_date
                          FROM habits_a;
                    DROP TABLE habits_a;
                    CREATE TABLE habits_a (
                        update_date DATE,
                        id INTEGER,
                        activity TEXT,
                        weekly_quota INTEGER,
                        priority INTEGER,
                        measure_id INTEGER,
                        target INTEGER,
                        goal_id INTEGER,
                        created_date DATE,
                        paused_until_date DATE,
                        deleted_date DATE);
                    INSERT INTO habits_a
                        SELECT *
                          FROM habits_a_tmp;
                    DROP TABLE habits_a_tmp;
                    COMMIT;
                    """)
    
                # Remove points column from habits table
                cursor = self.conn.executescript(
                    """
                    BEGIN TRANSACTION;
                    CREATE TEMPORARY TABLE habits_tmp(
                        id INTEGER,
                        activity TEXT,
                        weekly_quota INTEGER,
                        priority INTEGER,
                        measure_id INTEGER,
                        target INTEGER,
                        goal_id INTEGER,
                        created_date DATE,
                        paused_until_date DATE,
                        deleted_date DATE);
                    INSERT INTO habits_tmp
                        SELECT id,
                               activity,
                               weekly_quota,
                               priority,
                               measure_id,
                               target,
                               goal_id,
                               created_date,
                               paused_until_date,
                               deleted_date
                          FROM habits;
                    DROP TABLE habits;
                    CREATE TABLE habits (
                        id INTEGER,
                        activity TEXT,
                        weekly_quota INTEGER,
                        priority INTEGER,
                        measure_id INTEGER,
                        target INTEGER,
                        goal_id INTEGER,
                        created_date DATE,
                        paused_until_date DATE,
                        deleted_date DATE);
                    INSERT INTO habits
                        SELECT *
                          FROM habits_tmp;
                    DROP TABLE habits_tmp;
                    COMMIT;
                    """)
    
                self.add_schema_version_history(code_schema_ver)
                return True
    
            else:
                print 'No upgrade method available for Schema version ' + db_schema_ver
                return False
    
    
    def create_new_database(self, code_schema_ver):
        cursor = self.conn.cursor()
    
        code_ver_arr = code_schema_ver.split('.')
        code_ver = code_ver_arr[0] + '.' + code_ver_arr[1]
    
        # Table to track schema changes for upgrading between incompatible versions
        cursor.execute(
            """
            CREATE TABLE schema_version_history (id INTEGER PRIMARY KEY,
                major INTEGER, minor INTEGER, patch INTEGER,
                result TEXT, install_date DATE)
            """)
    
        # Insert a row for the current schema version
        self.add_schema_version_history(code_schema_ver)
    
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
                weekly_quota, created_date)
                VALUES (?, 1, NULL, 2, 4, CURRENT_DATE)
            """, ['Go for a run'])
    
        # A sample habit
        cursor.execute(
            """
            INSERT INTO habits (activity, measure_id, target, priority,
                weekly_quota, created_date)
                VALUES (?, 4, 2, 3, 4, CURRENT_DATE)
            """, ['Walk'])
    
        # A sample habit
        cursor.execute(
            """
            INSERT INTO habits (activity, measure_id, target, priority,
                weekly_quota, created_date)
                VALUES (?, 2, 30, 1, 5, CURRENT_DATE)
            """, ['Study'])
    
        self.conn.commit()
        cursor.close()
