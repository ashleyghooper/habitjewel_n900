#!/usr/bin/env python
# -*- coding: UTF8 -*-
# Copyright (C) 2016 by Ashley Hooper
# <ashleyghooper@gmail.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# HabitJewel: Track your habits

VERSION = '0.2.4'

import datetime
import calendar
import gettext
import gobject
import gtk
import hildon
import pango
import os
import osso
import sqlite3
import sys
import time

from portrait import FremantleRotation
from cell_renderer_clickable_pixbuf import CellRendererClickablePixbuf

import habitjewel_utils


# Constants

# Layout pseudo-constants
UI_NORMAL = gtk.HILDON_UI_MODE_NORMAL
UI_EDIT = gtk.HILDON_UI_MODE_EDIT
BTN_ARR_HORIZ = hildon.BUTTON_ARRANGEMENT_HORIZONTAL
BTN_ARR_VERT  = hildon.BUTTON_ARRANGEMENT_VERTICAL
BTN_SIZE_FINGER = gtk.HILDON_SIZE_FINGER_HEIGHT
BTN_SIZE_THUMB  = gtk.HILDON_SIZE_THUMB_HEIGHT
WRAP_WIDTH_LANDSCAPE = 700
WRAP_WIDTH_PORTRAIT = 380
CLICK_DRAG_THRESHOLD = 1024

# Unused?
WIN_PROG_IND = hildon.hildon_gtk_window_set_progress_indicator
OSSO_CONTEXT = osso.Context('org.maemo.habitjewel', VERSION, False)


# Program constants
# Treeview column indexes and titles
TV_HABIT_LIST_COL_NUM_ID             = 0
TV_HABIT_LIST_COL_NAME_ID            = 'ID'
TV_HABIT_LIST_COL_NUM_ACTIVITY       = 1
TV_HABIT_LIST_COL_NAME_ACTIVITY      = 'Activity'
TV_HABIT_LIST_COL_NUM_STATUS         = 2
TV_HABIT_LIST_COL_NAME_STATUS        = 'Status'
TV_HABIT_LIST_COL_NUM_PCT_COMPLETE   = 3
TV_HABIT_LIST_COL_NAME_PCT_COMPLETE  = 'Percent complete'
TV_HABIT_LIST_COL_NUM_INTVL_CODE     = 4
TV_HABIT_LIST_COL_NAME_INTVL_CODE    = 'Interval type'

# Habit status thresholds and pixbufs
STATUS_DONE_PCT         = 100
PIXBUF_FILE_DONE        = "checkbox_checked.png"
STATUS_75_PCT           = 75
PIXBUF_FILE_75_PERCENT  = "checkbox_partial_75_pct.png"
STATUS_50_PCT           = 50
PIXBUF_FILE_50_PERCENT  = "checkbox_partial_50_pct.png"
STATUS_25_PCT           = 25
PIXBUF_FILE_25_PERCENT  = "checkbox_partial_25_pct.png"
STATUS_MISSED_PCT       = 0
PIXBUF_FILE_MISSED      = "checkbox_crossed.png"
STATUS_UNKNOWN_PCT      = -1
PIXBUF_FILE_UNKNOWN     = "checkbox_unchecked.png"


# Initialisation
home = os.path.expanduser('~')
config_dir = home + '/.habitjewel/'
db_file = config_dir + 'database'
log_file = config_dir + 'log.txt'

i = 0


# Detect if running locally or not
running_path = sys.path[0]
if running_path.startswith('/opt'):
    locally = False
else:
    locally = True

if locally:
    img_dir = 'pixmaps/'
else:
    app_dir = '/opt/habitjewel/'
    img_dir = app_dir + 'pixmaps/'



# Check for config dir, database. Create if necessary
if not os.path.exists(config_dir):
    os.mkdir(config_dir)

if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
else:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    print 'creating new database'
    cursor.execute(
        """
        CREATE TABLE goals (id INTEGER PRIMARY KEY, title TEXT,
            priority INTEGER, category_id INTEGER, due_date DATE,
            points_threshold INTEGER, created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE goal_habits (id INTEGER PRIMARY KEY,
            goal_id INTEGER, habit_id INTEGER)
        """)
    cursor.execute(
        """
        CREATE TABLE habits (id INTEGER PRIMARY KEY, activity TEXT,
            measure_id INTEGER, target INTEGER,
            priority INTEGER, interval_code TEXT, interval INTEGER,
            limit_week_day_nums STRING,
            points INTEGER, created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE interval_types (id INTEGER PRIMARY KEY, code TEXT,
            desc TEXT, created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE categories (id INTEGER PRIMARY KEY, title TEXT,
            created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE history (id INTEGER PRIMARY KEY, habit_id INTEGER, date DATE,
            percent_complete INTEGER)
        """)
    cursor.execute(
        """
        CREATE TABLE measures (id INTEGER PRIMARY KEY, unit TEXT, plural TEXT, desc TEXT,
            created_date DATE, deleted_date DATE)
        """)
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
    cursor.execute(
        """
        INSERT INTO interval_types (code, desc, created_date)
            VALUES (?, ?, CURRENT_DATE)
        """, ['DAY', 'Daily'])
    cursor.execute(
        """
        INSERT INTO interval_types (code, desc, created_date)
            VALUES (?, ?, CURRENT_DATE)
        """, ['WEEK', 'Weekly'])
    cursor.execute(
        """
        INSERT INTO interval_types (code, desc, created_date)
            VALUES (?, ?, CURRENT_DATE)
        """, ['MONTH', 'Monthly'])
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, created_date) VALUES (?, ?, ?, CURRENT_DATE)
        """, ['min', 'mins', 'minute'])
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, created_date) VALUES (?, ?, ?, CURRENT_DATE)
        """, ['km', 'kms', 'kilometre'])
    cursor.execute(
        """
        INSERT INTO measures (unit, plural, desc, created_date) VALUES (?, ?, ?, CURRENT_DATE)
        """, ['word', 'words', 'words'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, points, created_date)
            VALUES (?, 1, 30, 1, 'DAY', 100, CURRENT_DATE)
        """, ['Meditate'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'WEEK', 1, 100, CURRENT_DATE)
        """, ['Study French'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'WEEK', 1, 100, CURRENT_DATE)
        """, ['Study Spanish'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, interval, points, created_date)
            VALUES (?, 1, 60, 1, 'MONTH', 1, 100, CURRENT_DATE)
        """, ['Study software development'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, interval, limit_week_day_nums, points, created_date)
            VALUES (?, 2, 2, 2, 'DAY', 1, '0,1,3,5', 100, CURRENT_DATE)
        """, ['Walk'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_code, interval, points, created_date)
            VALUES (?, 2, 50, 3, 'WEEK', 1, 100, CURRENT_DATE)
        """, ['Cycle'])
    
    conn.commit()
    cursor.close()




class MainWindow:

    def __init__(self):
        gettext.install('habitjewel','/opt/habitjewel/share/locale')

        # Get today's date and use that as the date displayed on startup
        self.view_date = self.get_today_dt()

        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name('Habitjewel')

        self.top_window = hildon.StackableWindow()
        self.top_window.set_title(_('HabitJewel'))

        # N900-specific
        self.osso_app_name = 'habitjewel'
        self.rotation_obj = self.init_autorotation()
        # Below to be removed (probably)
        #self.rotation = FremantleRotation('HabitJewel', None, VERSION, 0)
        self.init_disp_orientation()

        self.top_window.connect('destroy', gtk.main_quit)
        self.top_window.get_screen().connect('size-changed', self.orientation_changed)
        self.program.add_window(self.top_window)

        self.fontsize = 15

        menu = self.setup_main_menu()
        self.top_window.set_app_menu(menu)

        self.setup_hildon_ui_manager()

        self.container = self.home_screen()
        self.top_window.add(self.container)

        self.top_window.show_all()

        # Initialise properties object for new/editing habits
        self.habit = None;



    def init_autorotation(self):
        try:
            import n900_maemo5_portrait

            last_mode_number = 0 # Force auto-rotation
            r_object = n900_maemo5_portrait.FremantleRotation(self.osso_app_name, \
                main_window=self.top_window, mode=last_mode_number)
            return r_object

        except Exception:
            print "LOGME: Initialising rotation object failed"


    def init_disp_orientation(self):
        global portrait
        portrait = self.is_portrait()
        if (portrait):
            self.line_wrap_width = WRAP_WIDTH_PORTRAIT
            self.button_size = BTN_SIZE_THUMB
        else:
            self.line_wrap_width = WRAP_WIDTH_LANDSCAPE
            self.button_size = BTN_SIZE_FINGER


    def setup_main_menu(self):
        """
        This is the menu for the main windows
        """
        menu = hildon.AppMenu()

        button = gtk.Button(_('New Habit'))
        button.connect('clicked', self.on_new_habit_menu_item_click)
        menu.append(button)

        button = gtk.Button(_('Go to Date'))
        button.connect('clicked', self.on_go_to_date_menu_item_click)
        menu.append(button)

        button = gtk.Button(_('Stats'))
        button.connect('clicked', self.on_stats_menu_item_click)
        menu.append(button)

        button = gtk.Button(_('About'))
        button.connect('clicked', self.on_about_menu_item_click)
        menu.append(button)

        # menu.connect('event', self.event_catcher)

        menu.show_all()
        return menu


    # Set up UI Manager/context menus
    def setup_hildon_ui_manager(self):
        self.h_ui_manager = gtk.UIManager()
        h_ui_desc = """
            <ui>
              <popup name="habitcmenu" action="habitcmenu">
                <menuitem action="edithabit"/>
              </popup>
              <popup name="statuscmenu" action="statuscmenu">
                <menuitem action="habitdone"/>
                <menuitem action="habit75pcdone"/>
                <menuitem action="habit50pcdone"/>
                <menuitem action="habit25pcdone"/>
                <menuitem action="habitmissed"/>
              </popup>
            </ui>
        """

        # TODO: Mute habits menu option
        """
                <menuitem action="mutehabit"/>
        """
        """
                ('mutehabit', None, _('Mute Habit'), None, None, self.on_habit_cmenu_mute_selected),
        """

        h_actions = (
                ('edithabit', None, _('Edit Habit'), None, None, self.on_habit_cmenu_edit_selected),
                ('habitdone', None, _('Done'), None, None, self.on_status_cmenu_done_selected),
                ('habit75pcdone', None, _('75%'), None, None, self.on_status_cmenu_75pct_selected),
                ('habit50pcdone', None, _('50%'), None, None, self.on_status_cmenu_50pct_selected),
                ('habit25pcdone', None, _('25%'), None, None, self.on_status_cmenu_25pct_selected),
                ('habitmissed', None, _('Missed'), None, None, self.on_status_cmenu_missed_selected),
        )

        h_action_group = gtk.ActionGroup('Actions')
        h_action_group.add_actions(h_actions)
        self.h_ui_manager.insert_action_group(h_action_group, 0)
        self.h_ui_manager.add_ui_from_string(h_ui_desc)
        # tap and hold on habit activity
        self.h_habit_cmenu = self.h_ui_manager.get_widget('/habitcmenu')
        # tap and hold on habit status (checkbox)
        self.h_status_cmenu = self.h_ui_manager.get_widget('/statuscmenu')


    def popup_hildon_menu(self, menu):
        menu.popup(None, None, None, 3, 0)
        menu.set_name('hildon-context-sensitive-menu')


    def on_stats_menu_item_click(self, widget):
        return


    def on_go_to_date_menu_item_click(self, widget):
        st_win = hildon.StackableWindow()
        st_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox_cal = gtk.VBox()
        self.cal = self.get_calendar(self, self.view_date)
        vbox_cal.pack_start(self.cal, True, True) 

        hbox_cal_btns = gtk.HBox(True)

        today_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, BTN_ARR_HORIZ)
        today_btn.set_label(_('Today'))
        today_btn.connect('clicked', self.on_cal_today_btn_click, st_win)
        hbox_cal_btns.pack_start(today_btn, True, True) 

        prev_month_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, BTN_ARR_VERT)
        prev_month_btn.set_label(_('Previous Month'))
        prev_month_btn.connect('clicked', self.on_cal_prev_month_btn_click, st_win)
        hbox_cal_btns.pack_start(prev_month_btn, True, True) 

        next_month_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, BTN_ARR_VERT)
        next_month_btn.set_label(_('Next Month'))
        next_month_btn.connect('clicked', self.on_cal_next_month_btn_click, st_win)
        hbox_cal_btns.pack_start(next_month_btn, True, True) 

        vbox_cal.pack_start(hbox_cal_btns, True, True)

        st_win.add(vbox_cal)

        st_win.set_title('Go to Date')
        st_win.show_all()
        self.cal.connect('day_selected', self.on_calendar_day_selected, st_win)


    def get_today_dt(self):
        today = datetime.date.today()
        return today
        

    def on_cal_today_btn_click(self, widget, st_win):
        self.view_date = self.get_today_dt()
        st_win.destroy()
        self.redraw_habit_list(widget)


    def get_prev_month_date_dt(self, orig_dt):
        # return datetime object original date + 1 month
        return orig_dt - datetime.timedelta(1*365/12)


    def on_cal_prev_month_btn_click(self, widget, st_win):
        orig_dt = self.get_calendar_selected_date_dt(self.cal)
        new_dt = self.get_prev_month_date_dt(orig_dt)
        self.set_calendar_month(self.cal, new_dt)


    def get_next_month_date_dt(self, orig_dt):
        # return datetime object original date - 1 month
        return orig_dt + datetime.timedelta(1*365/12)


    def on_cal_next_month_btn_click(self, widget, st_win):
        orig_dt = self.get_calendar_selected_date_dt(self.cal)
        new_dt = self.get_next_month_date_dt(orig_dt)
        self.set_calendar_month(self.cal, new_dt)


    def get_calendar_selected_date_dt(self, cal):
        year, month, day = cal.get_date()
        month += 1
        return datetime.datetime(year, month, day)


    def set_calendar_month(self, cal, set_dt):
        cal.select_month(set_dt.month - 1, set_dt.year)


    def get_calendar(self, widget, disp_date):
        #TODO: Increase size of calendar dates
        #TODO: Highlight days based on habit fulfillment
        cal = gtk.Calendar()
        cal.detail_height_rows = 2
        cal.no_month_change = False
        cal.select_month(disp_date.month, disp_date.year)
        cal.select_day(disp_date.day)
        return cal


    def on_calendar_day_selected(self, cal, st_win):
        year, month, day = cal.get_date()
        print str(month)
        self.view_date = datetime.date(year, month, day)
        st_win.destroy()
        self.redraw_habit_list(widget)


    def on_about_menu_item_click(self, widget):
        st_win = hildon.StackableWindow()
        st_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox = gtk.VBox()
        pan = hildon.PannableArea()

        text = hildon.TextView()
        text.set_wrap_mode(gtk.WRAP_WORD)
        text.set_editable(False)
        text.set_cursor_visible(False)
        buf = text.get_buffer()
        iter = buf.get_iter_at_offset(0)
        i_tag = buf.create_tag('i', style=pango.STYLE_ITALIC)
        b_tag = buf.create_tag('b', weight=pango.WEIGHT_BOLD)
        buf.insert_with_tags(iter, 'HabitJewel', b_tag)
        buf.insert(iter, ', copyright © Ashley Hooper, 2016\n\n')
        buf.insert_with_tags(iter, 'HabitJewel', i_tag)
        buf.insert(iter, ' tracks your desired habits and their fulfillment on a regular \
basis, helping to motivate your self-improvement.\n\n')
        buf.insert(iter, 'Habits are defined as follows:\n\n\
* The activity (e.g. ')
        buf.insert_with_tags(iter, 'Meditate', i_tag)
        buf.insert(iter, ')\n\
* The target for each repetition of the habit, e.g. 20 minutes\n\
* The repetition interval, which determines how often you want to perform the habit\n\n\
The repetition interval can be either:\n\
a) ')
        buf.insert_with_tags(iter, 'day-based', i_tag)
        buf.insert(iter, ', repeating either every day or selected days of the week such \
as Monday, Wednesday, Friday\n\
b) ')
        buf.insert_with_tags(iter, 'week-based', i_tag)
        buf.insert(iter, ', repeating once for every ')
        buf.insert_with_tags(iter, 'n', i_tag)
        buf.insert(iter, 'weeks\n\
c) ')
        buf.insert_with_tags(iter, 'month-based', i_tag)
        buf.insert(iter, ', repeating once for every ')
        buf.insert_with_tags(iter, 'n', i_tag)
        buf.insert(iter, ' months\n\n\
After creating your habits they are displayed on the main page, along with \
navigation buttons to go back or forward one day at a time. For each day, the \
habits that would be current for that day are displayed. A checkbox allows \
toggling the fulfillment status of each habit, either undetermined (empty \
box), completed (green tick), or missed (red cross).\n\n\
The status of a habit for the current day or any preceding day can be changed \
at any time, but for reasons that should be obvious, the fulfillment status of \
habits for future dates can not be set.')
        text.set_buffer(buf)
        pan.add(text)
        vbox.pack_start(pan)
        st_win.add(vbox)
        st_win.set_title('About HabitJewel')
        st_win.show_all()


    def home_screen(self):
        self.vbox_outer = gtk.VBox(False)
        self.pan_area = hildon.PannableArea()

        self.habit_list_tv = hildon.GtkTreeView(UI_NORMAL)
        self.habit_list_tv.set_name('HabitListTreeview')
        self.areaview = self.habit_list_tv.get_action_area_box()

        # HBox for 'prev' button
        self.hbox_prev = gtk.HBox()
        self.img_prev = gtk.image_new_from_icon_name('general_back', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_prev.pack_start(self.img_prev)
        # 'Prev' button
        self.button_prev = hildon.Button(self.button_size, BTN_ARR_HORIZ)
        self.button_prev.connect('clicked', self.prev_day)
        self.button_prev.add(self.hbox_prev)

        # HBox for date display
        self.hbox_date = gtk.HBox()
        self.img_date = gtk.image_new_from_icon_name('general_calendar', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_date.pack_start(self.img_date)
        label_text = self.get_date_label_text(self)
        self.date_label = gtk.Label(label_text)
        self.hbox_date.pack_start(self.date_label)

        # HBox for 'next' button
        self.hbox_next = gtk.HBox()
        self.img_next = gtk.image_new_from_icon_name('general_forward', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_next.pack_start(self.img_next)
        # 'Next' button
        self.button_next = hildon.Button(self.button_size, BTN_ARR_HORIZ)
        self.button_next.connect('clicked', self.next_day)
        self.button_next.add(self.hbox_next)

        self.vbox_nav = gtk.VBox(False)
        self.hbox_nav = gtk.HBox()
        if (not self.is_portrait()):
            self.hbox_nav.pack_start(self.button_prev)
            self.hbox_nav.pack_start(self.hbox_date)
            self.hbox_nav.pack_start(self.button_next)
        else:
            self.vbox_nav.pack_start(self.hbox_date, False, False, 5)
            self.hbox_nav.pack_start(self.button_prev)
            self.hbox_nav.pack_start(self.button_next)

        self.vbox_nav.pack_start(self.hbox_nav, False)

        self.habit_list_model = self.create_habit_list_model(self)
        self.habit_list_tv.set_model(self.habit_list_model)
        self.prepare_habit_list(self)

        self.habit_list_tv.connect('button-press-event', self.on_habit_list_button_press)

        self.habit_list_tv.tap_and_hold_setup(None)
        self.habit_list_tv.connect('tap-and-hold', self.on_habit_tv_habit_tap_and_hold)

        self.pan_area.add(self.habit_list_tv)

        self.vbox_outer.pack_start(self.vbox_nav, False)
        self.vbox_outer.pack_start(self.pan_area, True, True)

        return self.vbox_outer


    def on_habit_tv_habit_tap_and_hold(self, widget):
        if not self.touched_tv_col_title:
            return
        if self.touched_tv_col_title == TV_HABIT_LIST_COL_NAME_ACTIVITY:
            gobject.idle_add(self.popup_hildon_menu, self.h_habit_cmenu)
        elif self.touched_tv_col_title == TV_HABIT_LIST_COL_NAME_STATUS:
            gobject.idle_add(self.popup_hildon_menu, self.h_status_cmenu)


    def on_habit_list_button_press(self, widget, event):
        result = self.habit_list_tv.get_path_at_pos(int(event.x), int(event.y))
        if result is not None:
            path, column, x, y = result

            self.touched_tv_col_title = column.get_title()

            model = self.habit_list_tv.get_model()
            index = model.get_value(model.get_iter(path), TV_HABIT_LIST_COL_NUM_ID)
            # Look up the habit in the array of habits by its id
            # (there's got to be a more efficient way of doing this!)
            for habit in self.habit_list:
                if habit['id'] == index:
                    self.touched_habit = habit
                    break
        else:
            self.touched_habit = None


    def create_habit_list_model(self, widget):
        lstore = gtk.ListStore(int, str, gtk.gdk.Pixbuf, int, str)
        # add columns to the tree view
        self.add_columns_to_habit_list(self.habit_list_tv)
        return lstore


    def prepare_habit_list(self, widget):
        self.habit_list = habitjewel_utils.get_habits_list(conn, self.view_date)

        for item in self.habit_list:
            lstore_iter = self.habit_list_model.append()
            icon_pixbuf = self.get_pixbuf_filename_for_status (item['pct_complete'])
 
            self.habit_list_model.set(lstore_iter, \
                TV_HABIT_LIST_COL_NUM_ID, \
                    item['id'], \
                TV_HABIT_LIST_COL_NUM_ACTIVITY, \
                    '<b>' + item['activity'] + '</b> ' + str(item['target_desc']) \
                    + ' <i>' + item['by_when'] + '</i>', \
                TV_HABIT_LIST_COL_NUM_STATUS, \
                    icon_pixbuf, \
                TV_HABIT_LIST_COL_NUM_PCT_COMPLETE, \
                    item['pct_complete'], \
                TV_HABIT_LIST_COL_NUM_INTVL_CODE, \
                    item['interval_code'] \
            )


    def get_pixbuf_filename_for_status(self, pct_complete):
        if (pct_complete >= STATUS_DONE_PCT):
            icon_filename = PIXBUF_FILE_DONE
        elif (pct_complete >= STATUS_75_PCT):
            icon_filename = PIXBUF_FILE_75_PERCENT
        elif (pct_complete >= STATUS_50_PCT):
            icon_filename = PIXBUF_FILE_50_PERCENT
        elif (pct_complete >= STATUS_25_PCT):
            icon_filename = PIXBUF_FILE_25_PERCENT
        elif (pct_complete == STATUS_MISSED_PCT):
            icon_filename = PIXBUF_FILE_MISSED
        else:
            icon_filename = PIXBUF_FILE_UNKNOWN

        return gtk.gdk.pixbuf_new_from_file(img_dir + icon_filename)
 

    def add_columns_to_habit_list(self, treeview):
        # column for ID
        column = gtk.TreeViewColumn(TV_HABIT_LIST_COL_NAME_ID, gtk.CellRendererText(), text=TV_HABIT_LIST_COL_NUM_ID)
        column.set_visible(False)
        treeview.append_column(column)

        # column for activity
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', self.line_wrap_width)
        column = gtk.TreeViewColumn(TV_HABIT_LIST_COL_NAME_ACTIVITY, renderer, markup=TV_HABIT_LIST_COL_NUM_ACTIVITY)
        column.set_property('expand', True)
        #column.tap_and_hold_setup(self.habit_list_menu)
        treeview.append_column(column)

        # column for checkbox
        checkbox = CellRendererClickablePixbuf()
        checkbox.connect('clicked', self.habit_toggled, treeview)
        column = gtk.TreeViewColumn(TV_HABIT_LIST_COL_NAME_STATUS, checkbox, pixbuf=TV_HABIT_LIST_COL_NUM_STATUS)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(80)
        treeview.append_column(column)

        # column for percent complete
        column = gtk.TreeViewColumn(TV_HABIT_LIST_COL_NAME_PCT_COMPLETE, gtk.CellRendererText(), text=TV_HABIT_LIST_COL_NUM_PCT_COMPLETE)
        column.set_visible(False)
        treeview.append_column(column)

        # column for interval type
        #column = gtk.TreeViewColumn(TV_HABIT_LIST_COL_NAME_INTVL_CODE, gtk.CellRendererText(), text=TV_HABIT_LIST_COL_NUM_INTVL_CODE)
        #column.set_visible(False)
        #treeview.append_column(column)


    def habit_toggled(self, widget, row_num, treeview):
        # Toggle habit completion status (fulfilled / unfulfilled / unknown)
        model = treeview.get_model()
        iter = model.get_iter(row_num)
        current_status_pct = model[iter][TV_HABIT_LIST_COL_NUM_PCT_COMPLETE]

        if (current_status_pct >= STATUS_DONE_PCT):
            percent_complete = STATUS_MISSED_PCT
        elif (current_status_pct == STATUS_MISSED_PCT):
            percent_complete = STATUS_UNKNOWN_PCT
        else:
            percent_complete = STATUS_DONE_PCT

        self.set_habit_percent_complete (model[iter][TV_HABIT_LIST_COL_NUM_ID], \
                self.view_date,
                percent_complete
        )
        model[iter][TV_HABIT_LIST_COL_NUM_STATUS] = self.get_pixbuf_filename_for_status (percent_complete)
        model[iter][TV_HABIT_LIST_COL_NUM_PCT_COMPLETE] = percent_complete
        # Maybe set timeout to redraw the habit list a few seconds later?


    def set_habit_percent_complete (self, habit_id, view_date, percent_complete):
        habitjewel_utils.set_habit_pct_complete (conn, \
                habit_id, \
                view_date, \
                percent_complete \
        )


    def prev_day(self, widget):
        self.view_date = self.view_date - datetime.timedelta(days=1)
        self.redraw_habit_list(widget)


    def next_day(self, widget):
        self.view_date = self.view_date + datetime.timedelta(days=1)
        self.redraw_habit_list(widget)


    def get_date_label_text(self, widget):
        date_disp = self.view_date.strftime('%a %d %B %Y')
        return date_disp


    def redraw_habit_list(self, widget):
        label_text = self.get_date_label_text(self)
        self.date_label.set_text(label_text)
        self.habit_list_model.clear()
        self.prepare_habit_list(self)
        checkbox_col = self.habit_list_tv.get_column(TV_HABIT_LIST_COL_NUM_STATUS)
        today = datetime.date.today()
        if (self.view_date <= today):
            checkbox_col.set_visible(True)
        else:
            checkbox_col.set_visible(False)
        self.redraw_window()


    def redraw_window(self):
        self.top_window.queue_draw()


    def on_new_habit_menu_item_click (self, widget):
        self.habit = None
        self.habit_edit_dlg (widget)


    def on_habit_cmenu_edit_selected (self, action):
        if not self.touched_habit:
            return
        else:
            self.habit = self.touched_habit
            # Can this be changed to pass habit to below func?
            self.habit_edit_dlg ()


    def on_status_cmenu_pct_selected (self, pct_complete):
        habit = self.touched_habit
        self.set_habit_percent_complete(habit['id'], self.view_date, pct_complete)
        self.redraw_habit_list(self)


    def on_status_cmenu_done_selected (self, action):
        if not self.touched_habit:
            return
        else:
            self.on_status_cmenu_pct_selected (100)


    def on_status_cmenu_75pct_selected (self, menu_item):
        if not self.touched_habit:
            return
        else:
            self.on_status_cmenu_pct_selected (75)


    def on_status_cmenu_50pct_selected (self, menu_item):
        if not self.touched_habit:
            return
        else:
            self.on_status_cmenu_pct_selected (50)


    def on_status_cmenu_25pct_selected (self, menu_item):
        if not self.touched_habit:
            return
        else:
            self.on_status_cmenu_pct_selected (25)


    def on_status_cmenu_missed_selected (self, menu_item):
        if not self.touched_habit:
            return
        else:
            self.on_status_cmenu_pct_selected (0)


    def habit_edit_dlg(self):

        # Get categories
        categories = habitjewel_utils.get_categories_list(conn)

        self.edit_win = hildon.StackableWindow()
        self.edit_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox = gtk.VBox()

        if not self.habit:
            self.habit = {'interval_code':'DAY', \
                    'activity':'Describe activity here', \
                    'target':'10', \
                    'measure_desc':'minute', \
                    'limit_week_day_nums':'0,1,2,3,4,5,6', \
                    'interval':'' \
                    }
            win_title = _('Add new habit')
        else:
            win_title = _('Edit habit')

        # Draw new/edit habit form 

        table = gtk.Table(2, 2, True)
        table.set_row_spacings(5)
        table.set_col_spacings(5)

        # Habit activity
        a_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        a_entry.set_input_mode(gtk.HILDON_GTK_INPUT_MODE_ALPHA | gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
        # set_placeholder doesn't work for some reason (displays only briefly)
        # a_entry.set_placeholder('Test placeholder')
        a_entry.set_text(self.habit['activity'])
        a_entry.set_position(len(self.habit['activity']))
        a_entry.connect('changed', self.on_activity_changed)

        # Habit target
        # (change to SpinButton ?)
        #l = gtk.Label()
        #l.set_markup('<b>' + _('Target') + '</b>')
        #adj = gtk.Adjustment(habit['target'], 0, 100, 1, 0, 0)
        #t_spin = gtk.SpinButton(adj, 0, 0)
        #t_spin.set_numeric(t_spin)
        t_selector = self.create_target_selector(self.habit['target'])
        t_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        t_picker.set_title(_('Target'))
        t_picker.set_selector(t_selector)
        table.attach(t_picker, 0, 1, 0, 1)
        t_selector.connect('changed', self.on_target_changed)

        #t_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        #t_entry.set_text(str(habit['target']))
        #table.attach(l, 0, 1, 1, 2, gtk.FILL)
        #table.attach(t_entry, 1, 2, 1, 2)

        # Habit measure
        m_selector = self.create_measures_selector(self.habit['measure_desc'])
        m_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        m_picker.set_title(_('Measure'))
        m_picker.set_selector(m_selector)
        #table.attach(m_picker, 1, 2, 0, 1, gtk.FILL)
        table.attach(m_picker, 1, 2, 0, 1)
        m_selector.connect('changed', self.on_measure_changed)

        # Habit interval type
        it_selector = self.create_interval_type_selector(self.habit['interval_code'])
        it_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        it_picker.set_title(_('Interval Type'))
        it_picker.set_selector(it_selector)
        table.attach(it_picker, 0, 1, 1, 2)
        it_selector.connect('changed', self.on_interval_type_changed)

        # Habit interval
        int_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)

        if self.habit['interval_code'] == 'DAY':
            # Allow limiting daily habit to specific days of the week
            int_selector = self.create_limit_week_days_selector(self.habit['limit_week_day_nums'])
            int_picker.set_title(_('Days of Week'))
            int_selector.connect('changed', self.on_limit_week_days_changed)

        else:
            # Selection of repeat interval for weekly/monthly habits
            int_selector = self.create_interval_selector(self.habit['interval'])
            int_picker.set_title(_('Interval'))
            int_selector.connect('changed', self.on_interval_changed)

        int_picker.set_selector(int_selector)

        table.attach(int_picker, 1, 2, 1, 2)

        # Save button
        save_button = hildon.Button(gtk.HILDON_SIZE_AUTO, BTN_ARR_VERT)
        save_button.set_label(_('Save'))
        save_button.connect('clicked', self.on_save_habit_btn_click)

        # Render
        vbox.pack_start(a_entry, True, True, 0)
        vbox.pack_start(table, True, True, 0)
        vbox.pack_start(save_button, True, True, 25)

        self.edit_win.add(vbox)
        self.edit_win.set_title(win_title)
        self.edit_win.show_all()

        
    def on_activity_changed(self, widget):
        self.habit['activity'] = widget.get_text()


    def create_target_selector(self, selected_target = None):
        selector = hildon.TouchSelector(text = True)
        for i in range(101):
            selector.append_text(str(i))
            if str(i) == str(selected_target):
                selector.set_active(0, i)
        return selector


    def on_target_changed(self, widget, user_data):
        self.habit['target'] = widget.get_current_text()


    def create_measures_selector(self, selected_measure = None):
        measures = habitjewel_utils.get_measures_list(conn)
        selector = hildon.TouchSelector(text = True)
        index = 0
        for measure in measures:
            selector.append_text(measure['desc'])
            if str(measure['desc']) == str(selected_measure):
                selector.set_active(0, index)
            index += 1
        return selector


    def on_measure_changed(self, widget, user_data):
        self.habit['measure_desc'] = widget.get_current_text()


    def create_interval_type_selector(self, selected_interval_code = None):
        interval_types = habitjewel_utils.get_interval_types_list(conn)
        selector = hildon.TouchSelector(text = True)
        index = 0
        for interval_type in interval_types:
            selector.append_text(interval_type['desc'])
            if str(interval_type['code']) == str(selected_interval_code):
                selector.set_active(0, index)
            index += 1
        return selector


    def on_interval_type_changed(self, widget, user_data):
        self.habit['interval_code'] = widget.get_current_text()


    def create_interval_selector(self, selected_interval = None):
        selector = hildon.TouchSelector(text = True)
        for i in range(10):
            selector.append_text(str(i))
            if str(i) == str(selected_interval):
                selector.set_active(0, i)
        return selector


    def on_interval_changed(self, widget, user_data):
        self.habit['interval'] = widget.get_current_text()


    def create_limit_week_days_selector(self, selected_days_of_week = None):
        selector = hildon.TouchSelector(text = True)
        selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        for i in range(7):
            selector.append_text(calendar.day_abbr[i])
            if not selected_days_of_week or selected_days_of_week.find(str(i)) != -1:
                selector.select_iter(0, selector.get_model(0).get_iter(i), True)
        return selector


    def on_limit_week_days_changed(self, widget, user_data):
        widget_text = widget.get_current_text()
        selected_days = []
        for i in range(7):
            if widget_text.find(calendar.day_abbr[i]) != -1:
                selected_days.append(str(i))
        self.habit['limit_week_day_nums'] = ','.join(selected_days)


    def on_save_habit_btn_click(self, widget):
        valid = None
        if self.habit['activity'] and \
                self.habit['target'] and \
                self.habit['measure_desc'] and \
                self.habit['interval_code']:

            if self.habit['interval_code'] == 'DAY' and \
                    self.habit['limit_week_day_nums']:
                valid = True
            elif self.habit['interval']:
                valid = True

        if valid:
            habitjewel_utils.save_habit(conn, self.habit)
            self.edit_win.destroy()
            self.show_info_banner(self.top_window, 'Habit "' + self.habit['activity'] + '" saved')
            self.redraw_habit_list(widget)
        else:
            self.show_info_banner (widget, 'Please ensure all fields are completed')


    def show_info_banner(self, widget, msg):
        hildon.hildon_banner_show_information(widget, 'qgn_note_infoprint', msg)


    def is_portrait(self):
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        if width > height:
            return False
        else:
            return True


    def event_catcher(self, widget, event):
        print "----------------------------------------------"
        print "Widget: " + str(widget)
        print str(event)
        print str(event.type)
        return False


    #FIXME: there's a bug that occurs with these steps:
    # 1) Start application in landscape, Edit a habit
    # 2) Go to portrait, go to landscape
    # 3) Go back to initial list
    # 4) Put to portrait
    # 5) Edit a habit in portrait
    # 6) Go to landscape
    def orientation_changed(self, screen):
        global portrait
        portrait = self.is_portrait()

        # This works but may be possible to improve on
        self.init_disp_orientation()
        self.top_window.remove(self.container)

        self.container = self.home_screen()
        self.top_window.add(self.container)
        self.top_window.show_all()

        return

        # Below example of reparenting etc from PyRecipe

        if not self.image.get_parent_window():
            print 'not in the right screen, doing nothing'
            return

        try:
            if self.is_portrait():
                print 'from landscape to portrait'

                #unparent the widgets
                self.hbox1.remove(self.freqbtn)
                self.hbox1.remove(self.daysbtn)

                self.mainbox.pack_start(self.freqbtn, False, False, 0)
                self.mainbox.reorder_child(self.freqbtn, 1)
                self.mainbox.pack_start(self.daysbtn, False, False, 0)
                self.mainbox.reorder_child(self.daysbtn, 2)

            else:
                print 'from portrait to landscape'

                self.mainbox.remove(self.freqbtn)
                self.mainbox.remove(self.daysbtn)

                try: #if hbox1/hbox2 exists, just packing the widgets
                    self.hbox1.pack_start(self.freqbtn, True, True, 0)
                    self.hbox1.reorder_child(self.freqbtn, 0)
                    self.hbox1.pack_start(self.daysbtn, True, True, 0)
                    self.hbox1.reorder_child(self.daysbtn, 1)

                except:
                    self.hbox1 = gtk.HBox()
                    self.hbox1.set_homogeneous(True)
                    self.hbox1.pack_start(self.freqbtn, True, True, 0)
                    self.hbox1.pack_start(self.daysbtn, True, True, 0)
                    self.mainbox.pack_start(self.hbox1, False, False, 0)
                    self.mainbox.reorder_child(self.hbox1, 1)

                    self.mainbox.show_all()

        except:
            print 'it isnt the new/edit habit screen'


 
if __name__ == "__main__":
    MainWindow = MainWindow()
    #gtk.gdk.threads_enter()
    gtk.main()
    #gtk.gdk.threads_leave()
