#!/usr/bin/env python
# -*- coding: UTF8 -*-
#
# Habit Jewel: Track your habits
# Copyright (c) 2016 Ashley Hooper
# <ashleyghooper@gmail.com>
#
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

VERSION = '0.7.0' # (major.minor.sub-minor)

# Minor version changes each time database schema changes 

"""
CHANGELOG:

v0.7.0
* Implemented countdown timer, accessible for time-based habits on current date only

v0.6.1
* Refactored history gathering
* Tweaked mini bar graph display
* Disabled main menu Stats button (for now)

v0.6.0
* Added mini bar-graphs next to each habit which display completion status for previous days
* Created HabitJewelDB class and moved all database functions there
* Added schema version check and upgrade script for schema vers 0.4 and 0.5

v0.5.0
* Added New Habit button and 'clone habit' tap and hold option in MHL
* Added habit parameters preview on habit editing screen

v0.4.0
* Added priority to the Edit Habits screen
* Added null measure for habits which don't have any associated measure
* Added a schema version history table, version will be inserted on database creation,
  and future versions with incompatible schema changes can use this to determine the
  version so as to know how to migrate to their newer schemas
* Renamed habitjewel_utils.py to habitjewel_db.py
* Moved database creation code to habitjewel_db.py and took out most of my sample habits
* Changed frequency field/column to weekly quota/quota (easier to make sense of)
* Fixed module path include code
* Added timezone
* Fixed portrait on startup using Khertan's patch to thp's FremantleRotation
* Deleted cruft

v0.3.0
* Bumped version number due to incompatible schema changes

v0.2.12
* Fixed incorrect dependency on portrait for FremantleRotation
* Changed habit schedules to based on weekly quota (repetitions) per weekly cycle

v0.2.10
* Changed back from Gtk UIManager to normal Gtk Menus for Hildon-styled popups

v0.2.9
* Fixed redraw of master habits list on orientation change
* Redraw edit habit window when paused/unpaused or deleted/undeleted
* Removed window stack, tried various ways to only handle rotation for visible window,
  but failed so reverted to blanket rotation.
* Created window stack to track top window to better handle rotation for windows
* Make copy of habit object as editing_habit (and clean up on editing window destroy)
* Added some date utility functions
* Refactoring
* Add DELETE & PAUSE to tap and hold menu for habits
* Make master habit list, accessible from main menu to edit all habits (not just current day)

TODO:
* Test for orientation change issues (see FIXME)
* Don't prepopulate habit table when no database - make placeholder for when empty instead
* Restore single click on checkbox to toggle done/missed/unknown statuses
* Move "About" page markup to external file
* Track periods where habits were "paused" in order to calculate stats correctly
* Add graphs
* Visual indicator when browsing future or past days' habits
* Move constants to a module
* Move code at bare module scope into class(es)
"""

import datetime
import cairo
import calendar
import fcntl
import gettext
import gobject
import gtk
import hildon
import os
import osso
import pango
import sqlite3
import sys
import time

# GStreamer for playing audio
import pygst
pygst.require('0.10')
import gst

# Get path to determine library and static resource locations
running_path = sys.path[0]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
img_dir = running_path + '/pixmaps/'

# Now import utilities (database) module
import habitjewel_db


# Constants
APP_DISPLAY_NAME = 'Habit Jewel'
APP_SYSTEM_NAME = 'habitjewel'
WIN_PROG_IND = hildon.hildon_gtk_window_set_progress_indicator
OSSO_CONTEXT = osso.Context('org.maemo.habitjewel', VERSION, False)

# Display
# Device display orientation (autorotation)
LANDSCAPE, PORTRAIT = range(2)

# Stackable Window titles
WIN_TITLE_TOP                = APP_DISPLAY_NAME
WIN_TITLE_TIMER              = 'Habit Jewel Timer'
WIN_TITLE_GO_TO_DATE         = 'Go To Date'
WIN_TITLE_PAUSE_UNTIL_DATE   = 'Pause Habit Until Date'
WIN_TITLE_MASTER_HABITS_LIST = 'Master Habits List'
WIN_TITLE_ADD_NEW_HABIT      = 'Add New Habit'
WIN_TITLE_EDIT_HABIT         = 'Edit Habit'
WIN_TITLE_ABOUT              = 'About HabitJewel'

# Gtk CellRenderer wrapping widths
# Day Habit List
TV_DAY_ACTIVITY_WRAP_WIDTH_LANDSCAPE = 650
TV_DAY_ACTIVITY_WRAP_WIDTH_PORTRAIT  = 360
# Master Habit List
TV_MASTER_ACTIVITY_WRAP_WIDTH_LANDSCAPE = 550
TV_MASTER_QUOTA_WRAP_WIDTH_LANDSCAPE    = 250
TV_MASTER_ACTIVITY_WRAP_WIDTH_PORTRAIT  = 300
TV_MASTER_QUOTA_WRAP_WIDTH_PORTRAIT     = 170

# Timer activity display wrapping widths
TIMER_ACTIVITY_WRAP_WIDTH_LANDSCAPE = 600
TIMER_ACTIVITY_WRAP_WIDTH_PORTRAIT  = 300

# TreeView constants
# Day habits list treeview column indexes and titles
TV_DAY_COL_NUM_ID             = 0
TV_DAY_COL_NAME_ID            = 'ID'
TV_DAY_COL_NUM_ACTIVITY       = 1
TV_DAY_COL_NAME_ACTIVITY      = 'Activity'
TV_DAY_COL_NUM_HISTICON       = 2
TV_DAY_COL_NAME_HISTICON      = 'History'
TV_DAY_COL_NUM_CHECKBOX       = 3
TV_DAY_COL_NAME_CHECKBOX      = 'Checkbox'
TV_DAY_COL_NUM_PCT_COMPLETE   = 4
TV_DAY_COL_NAME_PCT_COMPLETE  = 'Percent complete'

# Day habits list treeview column indexes and titles
TV_MASTER_COL_NUM_ID             = 0
TV_MASTER_COL_NAME_ID            = 'ID'
TV_MASTER_COL_NUM_ICON           = 1
TV_MASTER_COL_NAME_ICON          = 'Icon'
TV_MASTER_COL_NUM_ACTIVITY       = 2
TV_MASTER_COL_NAME_ACTIVITY      = 'Activity'
TV_MASTER_COL_NUM_QUOTA_DISP     = 3
TV_MASTER_COL_NAME_QUOTA_DISP    = 'Quota'
TV_MASTER_COL_NUM_QUOTA          = 4
TV_MASTER_COL_NAME_QUOTA         = 'Quota'
TV_MASTER_COL_NUM_STATUS         = 5
TV_MASTER_COL_NAME_STATUS        = 'Status'

# Habit status thresholds and pixbufs
HISTORY_DONE_PCT            = 100
HISTORY_DONE_PIXBUF_FILE    = "checkbox_checked.png"
HISTORY_75_PCT              = 75
HISTORY_75_PCT_PIXBUF_FILE  = "checkbox_partial_75_pct.png"
HISTORY_50_PCT              = 50
HISTORY_50_PCT_PIXBUF_FILE  = "checkbox_partial_50_pct.png"
HISTORY_25_PCT              = 25
HISTORY_25_PCT_PIXBUF_FILE  = "checkbox_partial_25_pct.png"
HISTORY_MISSED_PCT          = 0
HISTORY_MISSED_PIXBUF_FILE  = "checkbox_crossed.png"
HISTORY_CLEAR_PCT           = -1
HISTORY_CLEAR_PIXBUF_FILE   = "checkbox_unchecked.png"

# Habit recent history graph size
HABIT_RECENT_HIST_PIXBUF_SIZE = 48
HABIT_RECENT_HIST_BAR_HEIGHT  = 32

# Master Habits List status icons
MASTER_STATUS_DELETED_PIXBUF_FILE = "habit_deleted.png"
MASTER_STATUS_PAUSED_PIXBUF_FILE  = "habit_paused.png"
MASTER_STATUS_ACTIVE_PIXBUF_FILE  = "habit_active.png"

# Misc constants
NULL_MEASURE_DESC = '(None)'
TIMER_TIMEOUT_INTERVAL_SECS = 10

# Set timezone
time.tzset()

# User data initialisation
home = os.path.expanduser('~')
config_dir = home + '/.habitjewel'

# Check for config dir
if not os.path.exists(config_dir):
    os.mkdir(config_dir)





####################
### MainWindow class
####################

class MainWindow:

    def __init__(self):
        self.db = habitjewel_db.HabitJewelDb(config_dir, VERSION)

        gettext.install(APP_SYSTEM_NAME,'/opt/habitjewel/share/locale')

        # Get today's date and use that as the date displayed on startup
        self.view_date_dt = self.get_today_dt()

        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name(APP_DISPLAY_NAME)

        # Rotation setup
        orientation = self.get_current_screen_orientation()
        self.last_orientation = orientation
        self.set_window_orientation_params(orientation)
        # self.window_last_orientations = {}
        self.top_win = self.get_stackable_window(_(WIN_TITLE_TOP))
        self.program.add_window(self.top_win)

        # N900-specific
        self.osso_app_name = APP_SYSTEM_NAME
        self.rotation_obj = self.init_autorotation()

        # Determine current orientation
        orientation = self.get_current_screen_orientation()
        self.last_orientation = orientation
        self.set_window_orientation_params(orientation)

        # Set up callback for the Gdk.Window destroy signal
        self.top_win.connect('destroy', gtk.main_quit)
        # Set up callback for the Gdk.Screen size-changed signal
        self.top_win.get_screen().connect('size-changed', self.on_screen_orientation_changed)

        # Menus
        menu = self.setup_main_menu()
        self.top_win.set_app_menu(menu)
        self.setup_popup_menus()

        # Initialise Timer
        self.timer = {}

        self.top_container = self.get_day_habits_list_container()
        self.top_win.add(self.top_container)

        self.top_win.show_all()


    def init_autorotation(self):
        try:
            import fremantle_rotation
            r_object = fremantle_rotation.FremantleRotation(self.osso_app_name, main_window=self.top_win, version=VERSION, mode=0)
            return r_object

        except:
            print 'LOGME: Initialising rotation object failed'


    def set_window_orientation_params(self, orientation):
        if orientation == PORTRAIT:
            self.button_size = gtk.HILDON_SIZE_THUMB_HEIGHT
            self.tv_day_activity_wrap_width    = TV_DAY_ACTIVITY_WRAP_WIDTH_PORTRAIT
            self.tv_master_activity_wrap_width = TV_MASTER_ACTIVITY_WRAP_WIDTH_PORTRAIT
            self.tv_master_quota_wrap_width  = TV_MASTER_QUOTA_WRAP_WIDTH_PORTRAIT

        else:
            self.button_size = gtk.HILDON_SIZE_FINGER_HEIGHT
            self.tv_day_activity_wrap_width    = TV_DAY_ACTIVITY_WRAP_WIDTH_LANDSCAPE
            self.tv_master_activity_wrap_width = TV_MASTER_ACTIVITY_WRAP_WIDTH_LANDSCAPE
            self.tv_master_quota_wrap_width  = TV_MASTER_QUOTA_WRAP_WIDTH_LANDSCAPE





    #############################
    ### General utility functions
    #############################


    def redraw_window(self):
        self.top_win.queue_draw()


    def show_info_banner(self, widget, msg):
        hildon.hildon_banner_show_information(widget, 'qgn_note_infoprint', msg)


    def get_current_screen_orientation(self):
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        if width > height:
            return LANDSCAPE
        else:
            return PORTRAIT


    def get_active_window_title(self):
        window_stack = gtk.window_list_toplevels()
        for window in window_stack:
            # DEBUG: print str(window.get_title())
            if window.is_active():
                return window.get_title()


    def get_stackable_window(self, title):
        win = hildon.StackableWindow()
        win.set_title(title)
        return win


    def event_catcher(self, widget, event):
        print "----------------------------------------------"
        print "Widget: " + str(widget)
        print str(event)
        print str(event.type)
        return False


    def on_screen_orientation_changed(self, screen = None):
        orientation = self.get_current_screen_orientation()
        if orientation == self.last_orientation:
            # Current orientation same as the last? If so, do nothing
            return

        self.last_orientation = orientation
        self.set_window_orientation_params(orientation)

        # Re-render the top window, even if behind another window
        self.top_win.remove(self.top_container)
        self.top_container = self.get_day_habits_list_container()
        self.top_win.add(self.top_container)
        self.top_win.show_all()

        # Check the active window's title and re-render if required
        active_window_title = self.get_active_window_title()
        if not active_window_title:
            print "DEBUG: couldn't find active window title"
            return

        # Rotation for Master Habits List
        if active_window_title == _(WIN_TITLE_MASTER_HABITS_LIST):
            self.mhl_win.remove(self.mhl_container)
            self.mhl_container = self.get_master_habits_list_container()
            self.mhl_win.add(self.mhl_container)
            self.mhl_win.show_all()

        # Rotation for Timer window
        elif active_window_title == _(WIN_TITLE_TIMER):
            # No need to re-layout at present
            self.timer_win.remove(self.timer_container)
            self.timer_container = self.get_timer_container()
            self.timer_win.add(self.timer_container)
            self.timer_win.show_all()





    ##############################
    ### Database-related functions
    ##############################


    def set_db_habit_deleted_date(self, habit, deleted_date_dt):
        self.db.delete_habit(habit['id'])
        self.show_info_banner(self.top_win, '"' + habit['activity'] + '" deleted')


    def set_db_habit_paused_until_date (self, habit, paused_until_date_dt):
        self.db.set_habit_paused_until_date (habit['id'], paused_until_date_dt)
        if paused_until_date_dt:
            self.show_info_banner(self.top_win, '"' + habit['activity'] + '" paused until ' + self.dt_to_display_date(paused_until_date_dt))
        else:
            self.show_info_banner(self.top_win, '"' + habit['activity'] + '" unpaused')





    ###############################
    ### Date and Calendar functions 
    ###############################

    # Date utility functions

    def db_date_to_dt(self, db_date):
        year, month, day = db_date.split('-')
        return datetime.date(int(year), int(month), int(day))


    def dt_to_display_date(self, dt):
        return dt.strftime('%a %d %B %Y')


    def db_date_to_display_date(self, db_date):
        dt = self.db_date_to_dt(db_date)
        return self.dt_to_display_date(dt)


    def dt_to_db_date(self, dt):
        return dt.strftime('%Y-%m-%d')


    def get_today_dt(self):
        today = datetime.date.today()
        return today
        

    def get_prev_month_date_dt(self, orig_dt):
        # return datetime object original date + 1 month
        return orig_dt - datetime.timedelta(1*365/12)


    def get_next_month_date_dt(self, orig_dt):
        # return datetime object original date - 1 month
        return orig_dt + datetime.timedelta(1*365/12)


    # Calendar functions

    def get_general_calendar_window(self, cal_date_dt = None, hide_today_btn = False):
        if not cal_date_dt:
            cal_date_dt = self.get_today_dt()
        st_win = hildon.StackableWindow()
        vbox_cal = gtk.VBox()
        self.cal = self.get_calendar_widget()
        self.cal.select_month((cal_date_dt.month + 12 - 1) % 12, cal_date_dt.year)
        self.cal.select_day(cal_date_dt.day)
        vbox_cal.pack_start(self.cal, True, True) 

        hbox_cal_btns = gtk.HBox(True)

        if not hide_today_btn:
            today_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
            today_btn.set_label(_('Today'))
            today_btn.connect('clicked', self.on_cal_today_btn_click, st_win)
            hbox_cal_btns.pack_start(today_btn, True, True) 

        prev_month_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        prev_month_btn.set_label(_('Previous Month'))
        prev_month_btn.connect('clicked', self.on_cal_prev_month_btn_click, st_win)
        hbox_cal_btns.pack_start(prev_month_btn, True, True) 

        next_month_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        next_month_btn.set_label(_('Next Month'))
        next_month_btn.connect('clicked', self.on_cal_next_month_btn_click, st_win)
        hbox_cal_btns.pack_start(next_month_btn, True, True) 

        vbox_cal.pack_start(hbox_cal_btns, True, True)

        st_win.add(vbox_cal)
        return st_win


    # "get" because we are also getting the date from the calendar widget
    def get_gtk_cal_date_to_dt(self, cal):
        year, gtk_month, day = cal.get_date()
        month = (gtk_month + 1) % 12 
        return datetime.date(int(year), int(month), int(day))


    def on_cal_today_btn_click(self, widget, st_win):
        self.view_date_dt = self.get_today_dt()
        st_win.destroy()
        self.redraw_day_habits_list()


    def on_cal_prev_month_btn_click(self, widget, st_win):
        orig_dt = self.get_calendar_selected_date_dt(self.cal)
        new_dt = self.get_prev_month_date_dt(orig_dt)
        self.set_calendar_month(self.cal, new_dt)


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


    def get_calendar_widget(self):
        #TODO: Increase size of calendar dates
        #TODO: Highlight days based on habit fulfillment
        cal = gtk.Calendar()
        cal.detail_height_rows = 2
        cal.no_month_change = False
        return cal


    def on_go_to_date_cal_date_selected(self, cal, st_win):
        self.view_date_dt = self.get_gtk_cal_date_to_dt(cal)
        st_win.destroy()
        self.redraw_day_habits_list()





    #####################
    # Main Menu functions
    #####################


    def setup_main_menu(self):
        """
        This is the menu for the main windows
        """
        menu = hildon.AppMenu()

        button = gtk.Button(_('New Habit'))
        button.connect('clicked', self.on_main_menu_new_habit_click)
        menu.append(button)

        button = gtk.Button(_('Go to Date'))
        button.connect('clicked', self.on_main_menu_go_to_date_click)
        menu.append(button)

        # Stats page not yet implemented
        """
        button = gtk.Button(_('Stats'))
        button.connect('clicked', self.on_main_menu_stats_click)
        menu.append(button)
        """

        button = gtk.Button(_('Master Habits list'))
        button.connect('clicked', self.on_main_menu_master_habits_list_click)
        menu.append(button)

        button = gtk.Button(_('About'))
        button.connect('clicked', self.on_main_menu_about_click)
        menu.append(button)

        # menu.connect('event', self.event_catcher)

        menu.show_all()
        return menu


    def get_generated_hildon_context_menu(self, menu_def):
        m = gtk.Menu()
        m.set_name('hildon-context-sensitive-menu')

        for item in menu_def:
            if item[0] == 'menu':
                smi = gtk.MenuItem(_(item[1]))
                m.append(smi)
                sm = gtk.Menu()
                sm.set_name('hildon-context-sensitive-menu')
                smi.set_submenu(sm)

                for subitem in item[2]:
                    i = gtk.MenuItem(_(subitem[0]))
                    i.connect("activate", subitem[1])
                    sm.append(i)

            else:
                mi = gtk.MenuItem(_(item[0]))
                mi.connect("activate", item[1])
                m.append(mi)

        m.show_all()

        return m


    def get_day_activity_cmenu(self, hide_pause_submenu = False, show_unpause = False):
        menu_def = []
        if show_unpause:
            menu_def.extend([ \
                ['Unpause Habit', self.on_day_activity_cmenu_unpause_selected], \
            ])

        elif not hide_pause_submenu:
            menu_def.extend([ \
                    ['menu', 'Pause...', \
                        [ \
                            ['until tomorrow', self.on_day_activity_cmenu_pause_1_day_selected], \
                            ['2 days', self.on_day_activity_cmenu_pause_2_days_selected], \
                            ['1 week', self.on_day_activity_cmenu_pause_1_week_selected], \
                            ['2 weeks', self.on_day_activity_cmenu_pause_2_weeks_selected], \
                            ['until date', self.on_day_activity_cmenu_pause_until_date_selected], \
                        ], \
                    ], \
            ])

        menu_def.extend(( \
            ['Edit Habit', self.on_day_activity_cmenu_edit_selected], \
            ['Delete Habit', self.on_day_activity_cmenu_delete_selected], \
        ))

        return self.get_generated_hildon_context_menu(menu_def)


    def get_day_status_cmenu(self, show_open_timer = False):
        menu_def = []
        if show_open_timer:
            menu_def.extend([ \
                    ['Open Timer', self.on_status_cmenu_open_timer_selected], \
            ])

        menu_def.extend([ \
                ['Done', self.on_status_cmenu_done_selected], \
                ['75%', self.on_status_cmenu_75pct_selected], \
                ['50%', self.on_status_cmenu_50pct_selected], \
                ['25%', self.on_status_cmenu_25pct_selected], \
                ['Clear', self.on_status_cmenu_clear_selected], \
                ['Missed', self.on_status_cmenu_missed_selected], \
        ])

        return self.get_generated_hildon_context_menu(menu_def)


    def get_master_activity_cmenu(self):
        menu_def = [ \
                ['Edit Habit', self.on_master_activity_cmenu_edit_selected], \
                ['Clone Habit', self.on_master_activity_cmenu_clone_selected], \
                ['Delete Habit', self.on_master_activity_cmenu_delete_selected], \
        ]


        return self.get_generated_hildon_context_menu(menu_def)


    def setup_popup_menus(self):
        self.h_tv_day_activity_cmenu = self.get_day_activity_cmenu()
        self.h_tv_day_status_cmenu = self.get_day_status_cmenu()
        self.h_tv_master_activity_cmenu = self.get_master_activity_cmenu()


    def popup_hildon_menu(self, menu):
        # Pop up the menu given
        # Use mouse button 0 (4th arg) otherwise submenus don't work properly
        menu.popup(None, None, None, 0, 0)


    def on_main_menu_stats_click(self, widget):
        return


    def on_main_menu_master_habits_list_click(self, widget):
        self.mhl_win = self.get_stackable_window(_(WIN_TITLE_MASTER_HABITS_LIST))
        self.mhl_container = self.get_master_habits_list_container()
        self.mhl_win.add(self.mhl_container)
        self.mhl_win.connect('destroy', self.on_master_habits_list_window_destroy)
        self.mhl_win.show_all()


    def on_main_menu_go_to_date_click(self, widget):
        st_win = self.get_general_calendar_window()
        st_win.set_title(_(WIN_TITLE_GO_TO_DATE))
        st_win.show_all()
        self.cal.connect('day_selected', self.on_go_to_date_cal_date_selected, st_win)


    def on_main_menu_about_click(self, widget):
        st_win = self.get_stackable_window(_(WIN_TITLE_ABOUT))
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
        buf.insert_with_tags(iter, APP_DISPLAY_NAME + ' v' + VERSION, b_tag)
        buf.insert(iter, ', copyright © Ashley Hooper, 2016\n\n')
        buf.insert_with_tags(iter, APP_DISPLAY_NAME, i_tag)
        buf.insert(iter, ' tracks your desired habits and their fulfillment on a regular \
basis, helping to motivate your self-improvement.\n\n')
        buf.insert(iter, 'Habits are defined as follows:\n\n\
* The activity (e.g. ')
        buf.insert_with_tags(iter, 'Study complex algorithms', i_tag)
        buf.insert(iter, ')\n\
* The target for each repetition of the habit, e.g. 20 minutes\n\
* The weekly quota, which is the number of times per week you want to perform the habit\n\
* The priority for the habit, which determines how important the habit is and its sorting order\n\n\
After creating your habits they are displayed on the main page, along with \
navigation buttons to go back or forward one day at a time. For each day, the \
habits that would be current for that day are displayed. A checkbox allows \
toggling the fulfillment status of each habit, either:\n\n\
* undetermined (empty box)\n\
* completed (green tick)\n\
* partially complete (checkbox partially filled with yellow), or\n\
* missed (red cross)\n\n\
The habit fulfillment status for the current day can be set by a right click/tap and hold \
on the checkbox column, then selecting the desired status from the popup menu.\n\n\
The status of a habit for the current day or any preceding day can be changed \
at any time, but for reasons that should be obvious, the fulfillment status of \
habits for future dates can not be set.\n\n\
To edit, pause/unpause, or delete a habit, perform a right click/tap and hold on the \
activity description in the day habits view.\n\n\
The Master Habits List, accessible from the main menu allows editing, deletion, undeletion, \
etc. of all habits, whereas the daily habits view only shows habits for the current day.')
        text.set_buffer(buf)
        pan.add(text)
        vbox.pack_start(pan)
        st_win.add(vbox)
        st_win.show_all()


    def on_main_menu_new_habit_click (self, widget):
        habit = None
        self.habit_edit_window(habit)





    ##############################
    # Master Habits List functions
    ##############################


    def get_master_habits_list_container(self):
        self.master_habits_list = self.fetch_master_habits_list()

        self.master_habits_list_tv = hildon.GtkTreeView(gtk.HILDON_UI_MODE_NORMAL)
        self.master_habits_list_tv.set_headers_visible(True)
        self.master_habits_list_model = self.create_master_habits_list_model()
        self.master_habits_list_tv.set_model(self.master_habits_list_model)
        self.add_columns_to_master_habits_list_tv(self.master_habits_list_tv)
        self.populate_master_habits_list_ls(self.master_habits_list_model, self.master_habits_list)

        self.master_habits_list_tv.connect('button-press-event', self.on_master_habits_list_button_press)

        self.master_habits_list_tv.tap_and_hold_setup(None)
        self.master_habits_list_tv.connect('tap-and-hold', self.on_master_tv_habit_tap_and_hold)

        # Create the outermost container
        vbox = gtk.VBox()

        # Create the New Habit button
        hbox = gtk.HBox()
        img = gtk.image_new_from_icon_name("general_add", gtk.ICON_SIZE_SMALL_TOOLBAR)
        img.set_alignment(0.95, 0.5)
        hbox.pack_start(img, True, True, 0)
                        
        label = gtk.Label(_("New Habit"))
        label.set_alignment(0.05, 0.5)
        hbox.pack_start(label, True, True, 0)

        button = hildon.Button(self.button_size, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.connect("clicked", self.on_master_habits_list_new_habit_click)
        button.add(hbox)

        vbox.pack_start(button, False, False, 0)

        # Create the pannable area for the treeview
        pan_area = hildon.PannableArea()
        pan_area.add(self.master_habits_list_tv)
        vbox.pack_start(pan_area)

        return vbox


    def create_master_habits_list_model(self):
        return gtk.ListStore(int, gtk.gdk.Pixbuf, str, str, str, str, str)


    def fetch_master_habits_list(self):
        return self.db.get_habits_list_all()


    def add_columns_to_master_habits_list_tv(self, treeview):
        # column for ID
        c_id = gtk.TreeViewColumn(TV_MASTER_COL_NAME_ID, gtk.CellRendererText(), text=TV_MASTER_COL_NUM_ID)
        c_id.set_visible(False)
        treeview.append_column(c_id)

        # column for status icon
        pixbuf = gtk.CellRendererPixbuf()
        c_pixbuf = gtk.TreeViewColumn(TV_MASTER_COL_NAME_ICON, pixbuf, pixbuf=TV_MASTER_COL_NUM_ICON)
        treeview.append_column(c_pixbuf)

        # column for activity
        r_activity = gtk.CellRendererText()
        r_activity.set_property('wrap-mode', gtk.WRAP_WORD)
        r_activity.set_property('wrap-width', self.tv_master_activity_wrap_width)
        c_activity = gtk.TreeViewColumn(TV_MASTER_COL_NAME_ACTIVITY, r_activity, markup=TV_MASTER_COL_NUM_ACTIVITY)
        c_activity.set_property('expand', True)
        c_activity.set_property('sizing', gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        treeview.append_column(c_activity)

        # column for weekly quota display (e.g. 1/Week)
        r_quota = gtk.CellRendererText()
        r_quota.set_property('wrap-mode', gtk.WRAP_WORD)
        r_quota.set_property('wrap-width', self.tv_master_quota_wrap_width)
        c_quota = gtk.TreeViewColumn(TV_MASTER_COL_NAME_QUOTA_DISP, r_quota, markup=TV_MASTER_COL_NUM_QUOTA_DISP)
        c_quota.set_property('expand', True)
        treeview.append_column(c_quota)

        # column for weekly quota
        c_intvl = gtk.TreeViewColumn(TV_MASTER_COL_NAME_QUOTA, gtk.CellRendererText(), text=TV_MASTER_COL_NUM_QUOTA)
        c_intvl.set_visible(False)
        treeview.append_column(c_intvl)

        # column for status
        c_status = gtk.TreeViewColumn(TV_MASTER_COL_NAME_STATUS, gtk.CellRendererText(), text=TV_MASTER_COL_NUM_STATUS)
        c_status.set_visible(False)
        treeview.append_column(c_status)


    def populate_master_habits_list_ls(self, model, master_habits_list):
        for item in master_habits_list:
            lstore_iter = model.append()

            if item['deleted_date']:
                status = 'deleted'
            elif item['paused_until_date']:
                status = 'paused'
            else:
                status = 'active'

            activity_markup = '<b>' + item['activity'] + '</b> '

            if item['null_measure'] != 1:
                activity_markup += str(item['target_desc']);

            icon_pixbuf = self.get_pixbuf_filename_for_master_status(status)

            model.set(lstore_iter, \
                TV_MASTER_COL_NUM_ID, \
                    item['id'], \
                TV_MASTER_COL_NUM_ICON, \
                    icon_pixbuf, \
                TV_MASTER_COL_NUM_ACTIVITY, \
                    activity_markup, \
                TV_MASTER_COL_NUM_QUOTA_DISP, \
                    str(item['weekly_quota']) + ' / ' + _('week'), \
                TV_MASTER_COL_NUM_QUOTA, \
                    item['weekly_quota'], \
                TV_MASTER_COL_NUM_STATUS, \
                    status \
            )


    def get_pixbuf_filename_for_master_status(self, status):
        if (status == 'deleted'):
            icon_filename = MASTER_STATUS_DELETED_PIXBUF_FILE
        elif (status == 'paused'):
            icon_filename = MASTER_STATUS_PAUSED_PIXBUF_FILE
        else:
            icon_filename = MASTER_STATUS_ACTIVE_PIXBUF_FILE

        return gtk.gdk.pixbuf_new_from_file(img_dir + icon_filename)


    def on_master_habits_list_button_press(self, widget, event):
        result = self.master_habits_list_tv.get_path_at_pos(int(event.x), int(event.y))
        if result is not None:
            path, column, x, y = result

            self.touched_tv_col_title = column.get_title()

            model = self.master_habits_list_tv.get_model()
            index = model.get_value(model.get_iter(path), TV_MASTER_COL_NUM_ID)
            # Look up the habit in the array of habits by its id
            # (there's got to be a more efficient way of doing this!)
            for habit in self.master_habits_list:
                if habit['id'] == index:
                    self.touched_habit = habit
                    # Bail once we've found our row
                    break
        else:
            self.touched_habit = None


    def on_master_habits_list_new_habit_click (self, widget):
        habit = None
        self.habit_edit_window(habit)


    def on_master_tv_habit_tap_and_hold(self, widget):
        if not self.touched_tv_col_title:
            return
        if self.touched_tv_col_title == TV_MASTER_COL_NAME_ACTIVITY:
            gobject.idle_add(self.popup_hildon_menu, self.h_tv_master_activity_cmenu)
        #elif self.touched_tv_col_title == TV_MASTER_COL_NAME_QUOTA:
        #    gobject.idle_add(self.popup_hildon_menu, self.h_tv_day_status_cmenu)


    def on_master_activity_cmenu_edit_selected(self, action):
        if not self.touched_habit:
            return
        else:
            self.habit_edit_window(self.touched_habit)


    def on_master_activity_cmenu_clone_selected(self, action):
        if not self.touched_habit:
            return
        else:
            new_activity = self.touched_habit['activity'] + ' (' + _('copy') + ')'
            self.db.clone_habit(self.touched_habit['id'], new_activity)
            self.redraw_master_habits_list()


    def on_master_activity_cmenu_delete_selected(self, action):
        if not self.touched_habit:
            return
        else:
            self.db.delete_habit(self.touched_habit['id'])
            self.redraw_master_habits_list()


    def on_master_habits_list_window_destroy(self, win):
        # Clear data structures and widgets
        self.master_habits_list_tv = None
        self.master_habits_list_model = None
        self.master_habits_list = None


    def redraw_master_habits_list(self):
        self.master_habits_list_model.clear()
        self.master_habits_list = self.fetch_master_habits_list()
        self.populate_master_habits_list_ls(self.master_habits_list_model, self.master_habits_list)
        self.redraw_window()





    ###########################
    # Day Habits List functions
    ###########################


    def get_day_habits_list_container(self):
        self.day_habits_list = self.fetch_habits_list_for_date(self.view_date_dt)

        self.day_habits_list_tv = hildon.GtkTreeView(gtk.HILDON_UI_MODE_NORMAL)
        self.day_habits_list_model = self.create_day_habits_list_model()
        self.day_habits_list_tv.set_model(self.day_habits_list_model)
        self.add_columns_to_day_habits_list_tv(self.day_habits_list_tv)
        self.populate_day_habits_list_ls(self.day_habits_list)

        self.vbox_outer = gtk.VBox(False)
        self.pan_area = hildon.PannableArea()

        # HBox for 'prev' button
        self.hbox_prev = gtk.HBox()
        self.img_prev = gtk.image_new_from_icon_name('general_back', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_prev.pack_start(self.img_prev)
        # 'Prev' button
        self.button_prev = hildon.Button(self.button_size, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        self.button_prev.connect('clicked', self.on_day_habits_list_prev_day_click)
        self.button_prev.add(self.hbox_prev)

        # HBox for date display
        self.hbox_date = gtk.HBox()
        self.img_date = gtk.image_new_from_icon_name('general_calendar', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_date.pack_start(self.img_date)
        label_text = self.get_date_label_text()
        self.date_label = gtk.Label(label_text)
        self.hbox_date.pack_start(self.date_label)

        # HBox for 'next' button
        self.hbox_next = gtk.HBox()
        self.img_next = gtk.image_new_from_icon_name('general_forward', gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_next.pack_start(self.img_next)
        # 'Next' button
        self.button_next = hildon.Button(self.button_size, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        self.button_next.connect('clicked', self.on_day_habits_list_next_day_click)
        self.button_next.add(self.hbox_next)

        self.vbox_nav = gtk.VBox(False)
        self.hbox_nav = gtk.HBox()
        if (self.get_current_screen_orientation() == PORTRAIT):
            self.vbox_nav.pack_start(self.hbox_date, False, False, 5)
            self.hbox_nav.pack_start(self.button_prev)
            self.hbox_nav.pack_start(self.button_next)
        else:
            self.hbox_nav.pack_start(self.button_prev)
            self.hbox_nav.pack_start(self.hbox_date)
            self.hbox_nav.pack_start(self.button_next)

        self.vbox_nav.pack_start(self.hbox_nav, False)

        self.day_habits_list_tv.connect('button-press-event', self.on_day_habits_list_button_press)


        self.day_habits_list_tv.tap_and_hold_setup(None)
        self.day_habits_list_tv.connect('tap-and-hold', self.on_day_tv_habit_tap_and_hold)

        self.pan_area.add(self.day_habits_list_tv)

        self.vbox_outer.pack_start(self.vbox_nav, False)
        self.vbox_outer.pack_start(self.pan_area, True, True)

        return self.vbox_outer


    def on_day_tv_habit_tap_and_hold(self, widget):
        if not self.touched_tv_col_title:
            return
        if self.touched_tv_col_title == TV_DAY_COL_NAME_ACTIVITY:
            gobject.idle_add(self.popup_hildon_menu, self.h_tv_day_activity_cmenu)
        elif self.touched_tv_col_title == TV_DAY_COL_NAME_CHECKBOX:
            gobject.idle_add(self.popup_hildon_menu, self.h_tv_day_status_cmenu)


    def on_day_habits_list_button_press(self, widget, event):
        result = self.day_habits_list_tv.get_path_at_pos(int(event.x), int(event.y))
        if result is not None:
            path, column, x, y = result

            self.touched_tv_col_title = column.get_title()

            model = self.day_habits_list_tv.get_model()
            index = model.get_value(model.get_iter(path), TV_DAY_COL_NUM_ID)
            # Look up the habit in the array of habits by its id
            # (there's got to be a more efficient way of doing this!)
            for habit in self.day_habits_list:
                if habit['id'] == index:
                    self.touched_habit = habit
                    today_dt = self.get_today_dt()

                    show_unpause = False
                    show_open_timer = False

                    if habit['paused_until_date']:
                        paused_until_date_dt = self.db_date_to_dt(habit['paused_until_date'])
                        if paused_until_date_dt > today_dt:
                            show_unpause = True

                    if habit['to_minutes'] and self.view_date_dt == today_dt:
                        show_open_timer = True


                    # Refresh the activity context menu to show the unpause option
                    if show_unpause:
                        self.h_tv_day_activity_cmenu = self.get_day_activity_cmenu(True, True)
                    else:
                        self.h_tv_day_activity_cmenu = self.get_day_activity_cmenu()
                    

                    # Refresh the status context menu to show the start timer option
                    if show_open_timer:
                        self.h_tv_day_status_cmenu = self.get_day_status_cmenu(True)
                    else:
                        self.h_tv_day_status_cmenu = self.get_day_status_cmenu()
                    break
        else:
            self.touched_habit = None


    def create_day_habits_list_model(self):
        lstore = gtk.ListStore(int, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, int, str)
        # add columns to the tree view
        return lstore


    def fetch_habits_list_for_date(self, view_date_dt):
        return self.db.get_habits_list_for_date(view_date_dt)


    def populate_day_habits_list_ls(self, day_habits_list):
        for item in day_habits_list:
            lstore_iter = self.day_habits_list_model.append()
            checkbox_pixbuf = self.get_pixbuf_filename_for_completion_status(item['pct_complete'])
 
            activity_markup = '<b>' + item['activity'] + '</b> '

            if item['null_measure'] != 1:
                activity_markup += str(item['target_desc']);

            if item['weekly_quota'] > 1:
                activity_markup += ' [ ' + str(item['completion_total']) + '/' + \
                        str(item['weekly_quota']) + ' ]'

            # Render the last 7 days history graph for the habit
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, \
                    HABIT_RECENT_HIST_PIXBUF_SIZE, HABIT_RECENT_HIST_PIXBUF_SIZE)
            pixbuf.fill(0x00000000)
            pixmap, mask = pixbuf.render_pixmap_and_mask()

            pixmap = gtk.gdk.Pixmap(None, HABIT_RECENT_HIST_PIXBUF_SIZE, \
                    HABIT_RECENT_HIST_BAR_HEIGHT + 8, 16)
            cr = pixmap.cairo_create()

            # Graph previous 7 days' history for habit, [0:7] returns all but view date
            #for day in sorted(item['history'][:-1]):
            for index, day in enumerate(sorted(item['history'])[0:7]):
                completion = item['history'][day]
                # If we have history for this day...
                if len(completion) > 0:

                    # If missed show red bar, height of 1
                    if completion[0] == 0:
                        rgb = [0.9, 0.0, 0.0]
                        bar_y = HABIT_RECENT_HIST_BAR_HEIGHT
                        bar_h = 4

                    # For all other results
                    else:
                        # If from preceding week, draw in grey
                        if completion[1] < 0:
                            rgb = [0.5, 0.5, 0.5]
                        # Otherwise, based on completion status
                        else:
                            red = (100 - completion[0]) * 0.01
                            green = (completion[0] * 0.004) + 0.6
                            blue = 0.0
                            rgb = [red, green, blue]

                        bar_y = (100 - completion[0]) * HABIT_RECENT_HIST_BAR_HEIGHT / 100
                        bar_h = completion[0] * HABIT_RECENT_HIST_BAR_HEIGHT / 100

                # Draw a placeholder since we have no history for this day
                else:
                    rgb = [0.3, 0.3, 0.3]
                    bar_y = HABIT_RECENT_HIST_BAR_HEIGHT - 1
                    bar_h = 1

                # Draw the bar
                cr.set_source_rgb(rgb[0], rgb[1], rgb[2])
                cr.rectangle(index * 7, bar_y + 4, 5, bar_h)
                cr.fill()


            # Turn pixmap back into pixbuf for Treeview column
            pixbuf.get_from_drawable(pixmap, gtk.gdk.colormap_get_system(), \
                    0, 0, 0, 4, -1, -1)

            # Add the row to the list store
            self.day_habits_list_model.set(lstore_iter, \
                TV_DAY_COL_NUM_ID, \
                    item['id'], \
                TV_DAY_COL_NUM_ACTIVITY, \
                    activity_markup, \
                TV_DAY_COL_NUM_HISTICON, \
                    pixbuf, \
                TV_DAY_COL_NUM_CHECKBOX, \
                    checkbox_pixbuf, \
                TV_DAY_COL_NUM_PCT_COMPLETE, \
                    item['pct_complete'] \
            )


    def get_pixbuf_filename_for_completion_status(self, pct_complete):
        if (pct_complete >= HISTORY_DONE_PCT):
            icon_filename = HISTORY_DONE_PIXBUF_FILE
        elif (pct_complete >= HISTORY_75_PCT):
            icon_filename = HISTORY_75_PCT_PIXBUF_FILE
        elif (pct_complete >= HISTORY_50_PCT):
            icon_filename = HISTORY_50_PCT_PIXBUF_FILE
        elif (pct_complete >= HISTORY_25_PCT):
            icon_filename = HISTORY_25_PCT_PIXBUF_FILE
        elif (pct_complete == HISTORY_MISSED_PCT):
            icon_filename = HISTORY_MISSED_PIXBUF_FILE
        else:
            icon_filename = HISTORY_CLEAR_PIXBUF_FILE

        return gtk.gdk.pixbuf_new_from_file(img_dir + icon_filename)
 

    def add_columns_to_day_habits_list_tv(self, treeview):
        # column for ID
        column = gtk.TreeViewColumn(TV_DAY_COL_NAME_ID, gtk.CellRendererText(), text=TV_DAY_COL_NUM_ID)
        column.set_visible(False)
        treeview.append_column(column)

        # column for activity
        rend = gtk.CellRendererText()
        rend.set_property('wrap-mode', gtk.WRAP_WORD)
        rend.set_property('wrap-width', self.tv_day_activity_wrap_width)
        column = gtk.TreeViewColumn(TV_DAY_COL_NAME_ACTIVITY, rend, markup=TV_DAY_COL_NUM_ACTIVITY)
        column.set_property('expand', True)
        treeview.append_column(column)

        # column for history
        rend = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(TV_DAY_COL_NAME_HISTICON, rend, pixbuf=TV_DAY_COL_NUM_HISTICON)
        treeview.append_column(column)

        # column for checkbox
        # below was for single-clickable checkbox toggle
        #checkbox = CellRendererClickablePixbuf()
        #checkbox.connect('clicked', self.habit_toggled, treeview)
        checkbox = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(TV_DAY_COL_NAME_CHECKBOX, checkbox, pixbuf=TV_DAY_COL_NUM_CHECKBOX)
        # Make the column a little wider to make it easier to press on
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(80)
        treeview.append_column(column)

        # column for percent complete
        column = gtk.TreeViewColumn(TV_DAY_COL_NAME_PCT_COMPLETE, gtk.CellRendererText(), text=TV_DAY_COL_NUM_PCT_COMPLETE)
        column.set_visible(False)
        treeview.append_column(column)

        # column for interval type
        #column = gtk.TreeViewColumn(TV_DAY_COL_NAME_PERIOD_CODE, gtk.CellRendererText(), text=TV_DAY_COL_NUM_PERIOD_CODE)
        #column.set_visible(False)
        #treeview.append_column(column)


    # This function is no longer used
    def habit_toggled(self, widget, row_num, treeview):
        # Toggle habit completion status (fulfilled / unfulfilled / unknown)
        model = treeview.get_model()
        iter = model.get_iter(row_num)
        current_status_pct = model[iter][TV_DAY_COL_NUM_PCT_COMPLETE]

        if (current_status_pct >= HISTORY_DONE_PCT):
            percent_complete = HISTORY_MISSED_PCT
        elif (current_status_pct == HISTORY_MISSED_PCT):
            percent_complete = HISTORY_CLEAR_PCT
        else:
            percent_complete = HISTORY_DONE_PCT

        self.set_habit_percent_complete (model[iter][TV_DAY_COL_NUM_ID], \
                self.view_date_dt,
                percent_complete
        )
        model[iter][TV_DAY_COL_NUM_CHECKBOX] = self.get_pixbuf_filename_for_completion_status (percent_complete)
        model[iter][TV_DAY_COL_NUM_PCT_COMPLETE] = percent_complete
        # Maybe set timeout to redraw the habit list a few seconds later?


    def on_day_habits_list_prev_day_click(self, widget):
        self.view_date_dt = self.view_date_dt - datetime.timedelta(days=1)
        self.redraw_day_habits_list()


    def on_day_habits_list_next_day_click(self, widget):
        self.view_date_dt = self.view_date_dt + datetime.timedelta(days=1)
        self.redraw_day_habits_list()


    def get_date_label_text(self):
        return self.dt_to_display_date(self.view_date_dt)


    def redraw_day_habits_list(self):
        label_text = self.get_date_label_text()
        self.date_label.set_text(label_text)
        self.day_habits_list_model.clear()
        self.day_habits_list = self.fetch_habits_list_for_date(self.view_date_dt)
        self.populate_day_habits_list_ls(self.day_habits_list)
        today = datetime.date.today()

        # If viewing the current day, show the pause menu and timer option
        if self.view_date_dt == today:
            self.h_tv_day_activity_cmenu = self.get_day_activity_cmenu()
        else:
            self.h_tv_day_activity_cmenu = self.get_day_activity_cmenu(True)

        # Hide checkbox column for dates in the future
        checkbox_col = self.day_habits_list_tv.get_column(TV_DAY_COL_NUM_CHECKBOX)
        if self.view_date_dt <= today:
            checkbox_col.set_visible(True)
        else:
            checkbox_col.set_visible(False)
        self.redraw_window()


    def on_day_activity_cmenu_set_pause (self, paused_until_date_dt):
        if not self.touched_habit:
            return
        else:
            habit = self.touched_habit
            self.set_db_habit_paused_until_date(habit, paused_until_date_dt)
            self.redraw_day_habits_list()


    def on_day_activity_cmenu_unpause_selected (self, action):
        self.on_day_activity_cmenu_set_pause(None)


    def on_day_activity_cmenu_pause_1_day_selected(self, action):
        paused_until_date_dt = self.get_today_dt() + datetime.timedelta(days=1)
        self.on_day_activity_cmenu_set_pause(paused_until_date_dt)


    def on_day_activity_cmenu_pause_2_days_selected(self, action):
        paused_until_date_dt = self.get_today_dt() + datetime.timedelta(days=2)
        self.on_day_activity_cmenu_set_pause(paused_until_date_dt)


    def on_day_activity_cmenu_pause_1_week_selected(self, action):
        paused_until_date_dt = self.get_today_dt() + datetime.timedelta(days=7)
        self.on_day_activity_cmenu_set_pause(paused_until_date_dt)


    def on_day_activity_cmenu_pause_2_weeks_selected(self, action):
        paused_until_date_dt = self.get_today_dt() + datetime.timedelta(days=14)
        self.on_day_activity_cmenu_set_pause(paused_until_date_dt)


    def on_day_activity_cmenu_pause_until_date_selected(self, action):
        st_win = self.get_general_calendar_window()
        st_win.set_title(_(WIN_TITLE_PAUSE_UNTIL_DATE))
        st_win.show_all()
        self.cal.connect('day_selected', self.on_day_activity_cmenu_set_pause_cal_date_selected, st_win)

 
    def on_day_activity_cmenu_set_pause_cal_date_selected(self, cal, st_win):
        paused_until_date_dt = self.get_gtk_cal_date_to_dt(cal)
        st_win.destroy()
        self.on_day_activity_cmenu_set_pause(paused_until_date_dt)


    def on_day_activity_cmenu_delete_selected(self, action):
        if not self.touched_habit:
            return
        else:
            habit = self.touched_habit
            today_dt = self.get_today_dt()
            self.set_db_habit_deleted_date(habit, today_dt)
            self.redraw_day_habits_list()


    def on_day_activity_cmenu_edit_selected(self, action):
        if not self.touched_habit:
            return
        else:
            self.habit_edit_window(self.touched_habit)


    def set_habit_percent_complete (self, habit_id, view_date_dt, percent_complete):
        self.db.set_habit_pct_complete (habit_id, view_date_dt, percent_complete)


    def on_status_cmenu_open_timer_selected (self, menu_item):
        if not self.touched_habit:
            return
        else:
            self.timer_habit = self.touched_habit
            # Initialise the timer window
            self.timer_win = self.get_stackable_window(_(WIN_TITLE_TIMER))
            self.timer_container = self.get_timer_container()
            self.timer_win.add(self.timer_container)
            self.timer_win.connect('destroy', self.on_timer_window_destroy)
            self.timer_win.show_all()


    def on_status_cmenu_pct_selected (self, pct_complete):
        if not self.touched_habit:
            return
        else:
            habit = self.touched_habit
            self.set_habit_percent_complete(habit['id'], self.view_date_dt, pct_complete)
            self.redraw_day_habits_list()


    def on_status_cmenu_done_selected (self, action):
        self.on_status_cmenu_pct_selected (HISTORY_DONE_PCT)


    def on_status_cmenu_75pct_selected (self, menu_item):
        self.on_status_cmenu_pct_selected (75)


    def on_status_cmenu_50pct_selected (self, menu_item):
        self.on_status_cmenu_pct_selected (50)


    def on_status_cmenu_25pct_selected (self, menu_item):
        self.on_status_cmenu_pct_selected (25)


    def on_status_cmenu_missed_selected (self, menu_item):
        self.on_status_cmenu_pct_selected (HISTORY_MISSED_PCT)


    def on_status_cmenu_clear_selected (self, menu_item):
        self.on_status_cmenu_pct_selected (HISTORY_CLEAR_PCT)





    ##################################
    # Countdown timer window functions
    ##################################


    def get_timer_container(self):
        habit = self.timer_habit
        activity_tbl = gtk.Table(2, 2, False)
        activity_tbl.set_row_spacings(5)
        activity_tbl.set_col_spacings(5)

        a_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, \
                hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        a_btn.set_label(_('Timer for:'))

        a_entry = gtk.Label(habit['activity'])
        a_entry.set_line_wrap(True)
        activity_tbl.attach(a_btn, 0, 1, 0, 1)
        activity_tbl.attach(a_entry, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL)

        t_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, \
                hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        t_btn.set_label(_('Target:'))

        if habit['pct_complete'] > 0:
            status = str(100 - habit['pct_complete']) + '% ' + _('remaining')
        else:
            status = _('not started')
        t_text = habit['target_desc'] + ' (' + status + ')'
        t_entry = gtk.Label(t_text)
        t_entry.set_line_wrap(True)
        activity_tbl.attach(t_btn, 0, 1, 1, 2)
        activity_tbl.attach(t_entry, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL)

        if self.last_orientation == LANDSCAPE:
            box_controls = gtk.HBox(True)
        else:
            box_controls = gtk.VBox(True)

        box_controls.set_spacing(30)

        # When timer is running, display
        if not 'running' in self.timer and not 'remain_secs' in self.timer:
            # Set slider initial value (current remaining time in mins if existing timer)
            # Calculate remaining time based on percent already complete and target
            remain_mins = (100 - habit['pct_complete']) * \
                    (habit['target'] * habit['to_minutes']) * 0.01
            self.timer['remain_secs'] = remain_mins * 60

        else:
            remain_mins = self.timer['remain_secs'] * 0.01666666


        self.timer_adj = gtk.Adjustment(remain_mins, 0, habit['target'] * habit['to_minutes'] * 2, 0, 1)
        scale = gtk.HScale(self.timer_adj)
        # Disable decimals
        scale.set_digits(0)
        scale.connect('value_changed', self.on_timer_time_changed)

        vbox_scale = gtk.VBox(True)
        scale_lbl = gtk.Label(_('Countdown Time (Minutes)'))
        vbox_scale.pack_start(scale_lbl, True, False) 
        vbox_scale.pack_start(scale, True, False) 

        box_controls.pack_start(vbox_scale, True, False) 

        self.start_stop_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, \
                hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        start_stop_btn_lbl = self.get_timer_start_stop_btn_lbl()
        self.start_stop_btn.set_label(start_stop_btn_lbl)
        self.start_stop_btn.connect('clicked', self.on_timer_start_stop_btn_click)

        box_controls.pack_start(self.start_stop_btn, True, True) 

        vbox = gtk.VBox()
        vbox.pack_start(activity_tbl, True, True)
        vbox.pack_start(box_controls, True, False)

        return vbox


    def set_timer_adjustment_value(self, value):
        self.timer_adj.set_value(value) 


    def get_timer_start_stop_btn_lbl(self):
        if 'running' in self.timer:
            return _('Stop Timer')
        else:
            return _('Start Timer')


    def set_timer_countdown_time(self, seconds):
        self.timer['remain_secs'] = seconds


    def on_timer_start_stop_btn_click(self, win):
        self.on_timer_start_or_stop()


    def on_timer_start_or_stop(self):
        if 'running' in self.timer:
            self.timer.pop('running', None)
            self.timer.pop('remain_secs', None)
        else:
            self.timer['running'] = True
            gobject.timeout_add_seconds(TIMER_TIMEOUT_INTERVAL_SECS, self.timer_countdown)

        btn_lbl = self.get_timer_start_stop_btn_lbl()
        self.start_stop_btn.set_label(btn_lbl)


    def on_timer_time_changed(self, widget):
        if not 'running' in self.timer:
            self.set_timer_countdown_time(self.timer_adj.get_value() * 60)
        else:
            self.timer_adj.set_value(self.timer['remain_secs'] * 0.01666666)


    def timer_countdown(self):
        if not 'running' in self.timer:
            return False

        # Timer is running but still has time to go
        elif self.timer['remain_secs'] > TIMER_TIMEOUT_INTERVAL_SECS:
            self.timer['remain_secs'] -= TIMER_TIMEOUT_INTERVAL_SECS
            new_min = abs(self.timer['remain_secs'] % 60) 
            if new_min == 0 or new_min >= 60 - TIMER_TIMEOUT_INTERVAL_SECS:
                self.set_timer_adjustment_value(self.timer['remain_secs'] * 0.01666666)
            return True

        # Timer is running and time's up!
        else:
            self.set_timer_adjustment_value(0)
            self.on_timer_start_or_stop()
            pl = gst.element_factory_make("playbin", "player")
            pl.set_property('uri','file:///usr/share/sounds/ui-wake_up_tune.wav')
            pl.set_state(gst.STATE_PLAYING)
            return False


    def on_timer_window_destroy(self, win):
        # Clear data structures and widgets
        # TODO: Stop timer? or maybe not...
        if 'running' in self.timer:
            self.on_timer_start_or_stop()
            self.show_info_banner(self.top_win, _('Timer Cleared'))
            self.timer = None




    ################################
    # Habit editing window functions
    ################################


    def habit_edit_window(self, habit):
        # Get categories
        categories = self.db.get_categories_list()

        self.edit_win = hildon.StackableWindow()
        vbox = gtk.VBox()

        if not habit:
            self.editing_habit = { \
                    'activity':'Describe activity here', \
                    'weekly_quota':'7', \
                    'measure_desc':NULL_MEASURE_DESC, \
                    'unit':'', \
                    'plural':'', \
                    'null_measure':'1', \
                    'priority':'2', \
                    'target':'1', \
                    'paused_until_date':'', \
                    'deleted_date':'' \
                    }
            win_title = _(WIN_TITLE_ADD_NEW_HABIT)
        else:
            self.editing_habit = habit
            win_title = _(WIN_TITLE_EDIT_HABIT)

        # Draw new/edit habit form 
        # Habit activity
        a_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        # set_placeholder doesn't work for some reason (displays only briefly)
        # a_entry.set_placeholder('Test placeholder')
        a_entry.set_max_length(50)
        a_entry.set_text(self.editing_habit['activity'])
        a_entry.set_position(len(self.editing_habit['activity']))
        a_entry.connect('changed', self.on_activity_changed)

        # Preview label
        preview_info = self.get_edit_habit_preview_label_text(self.editing_habit)
        preview_lbl = gtk.Label(preview_info)

        # Settings table
        settings_tbl = gtk.Table(2, 2, True)
        settings_tbl.set_row_spacings(5)
        settings_tbl.set_col_spacings(5)

        # Habit weekly quota
        f_selector = self.create_weekly_quota_selector(self.editing_habit['weekly_quota'])
        f_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        f_picker.set_title(_('Weekly Quota'))
        f_picker.set_selector(f_selector)
        settings_tbl.attach(f_picker, 0, 1, 0, 1)
        f_selector.connect('changed', self.on_edit_habit_weekly_quota_changed, preview_lbl)

        # Habit measure
        m_selector = self.create_measures_selector(self.editing_habit['measure_desc'])
        m_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        m_picker.set_title(_('Measure'))
        m_picker.set_selector(m_selector)
        settings_tbl.attach(m_picker, 1, 2, 0, 1)
        m_selector.connect('changed', self.on_edit_habit_measure_changed, preview_lbl)

        # Habit priority
        p_selector = self.create_priority_selector(self.editing_habit['priority'])
        p_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        p_picker.set_title(_('Priority'))
        p_picker.set_selector(p_selector)
        settings_tbl.attach(p_picker, 0, 1, 1, 2)
        p_selector.connect('changed', self.on_edit_habit_priority_changed, preview_lbl)

        # Habit target
        # (change to SpinButton ?)
        #l = gtk.Label()
        #l.set_markup('<b>' + _('Target') + '</b>')
        #adj = gtk.Adjustment(editing_habit['target'], 0, 100, 1, 0, 0)
        #t_spin = gtk.SpinButton(adj, 0, 0)
        #t_spin.set_numeric(t_spin)
        t_selector = self.create_target_selector(self.editing_habit['target'])
        t_picker = hildon.PickerButton(gtk.HILDON_SIZE_AUTO,
                hildon.BUTTON_ARRANGEMENT_VERTICAL)
        t_picker.set_title(_('Target'))
        t_picker.set_selector(t_selector)
        settings_tbl.attach(t_picker, 1, 2, 1, 2)
        t_selector.connect('changed', self.on_edit_habit_target_changed, preview_lbl)
        # Expose target picker widget as class variable
        self.edit_habit_target_picker = t_picker

        # Status label
        habit_status_text = self.get_edit_habit_status_label_text(self.editing_habit)
        status_lbl = gtk.Label(habit_status_text)

        # Button bar table
        btn_tbl = gtk.Table(1, 3, True)
        btn_tbl.set_row_spacings(5)
        btn_tbl.set_col_spacings(5)

        # Delete/undelete button
        delete_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        if not self.editing_habit['deleted_date']:
            delete_btn.set_label(_('Delete'))
        else:
            delete_btn.set_label(_('Undelete'))
        delete_btn.connect('clicked', self.on_edit_habit_delete_btn_click, status_lbl)
        btn_tbl.attach(delete_btn, 0, 1, 0, 1)

        # Pause/unpause button
        pause_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        if not self.editing_habit['paused_until_date']:
            pause_btn.set_label(_('Pause'))
        else:
            pause_btn.set_label(_('Unpause'))
        pause_btn.connect('clicked', self.on_edit_habit_pause_btn_click, status_lbl)
        btn_tbl.attach(pause_btn, 1, 2, 0, 1)

        # Save button
        save_btn = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        save_btn.set_label(_('Save'))
        save_btn.connect('clicked', self.on_edit_habit_save_btn_click)
        btn_tbl.attach(save_btn, 2, 3, 0, 1)

        # Render
        vbox.pack_start(a_entry, False, True, 0)
        vbox.pack_start(preview_lbl, True, False, 0)
        vbox.pack_start(settings_tbl, True, True, 0)
        vbox.pack_start(status_lbl, True, False, 0)
        vbox.pack_start(btn_tbl, True, True, 0)

        self.edit_win.add(vbox)
        self.edit_win.set_title(win_title)
        self.edit_win.connect('destroy', self.on_edit_habit_window_destroy)
        self.edit_win.show_all()

        # Hide target picker if non-measurable habit
        self.set_target_picker_visibility()


    def set_target_picker_visibility(self):
        if self.db.is_null_measure(self.editing_habit['measure_desc']):
            self.edit_habit_target_picker.hide();
        else:
            self.edit_habit_target_picker.show();


    def get_edit_habit_preview_label_text(self, habit):
        preview = ''
        if not 'null_measure' in habit or \
                'null_measure' in habit and habit['null_measure'] != '1':

            if 'target' in habit and habit['target'] and \
                    'measure_desc' in habit and habit['measure_desc']:
                if habit['target'] == '1':
                    measure = habit['unit']
                else:
                    measure = habit['plural']
                preview += str(habit['target']) + ' ' + measure

        if preview:
            preview += ', '

        if 'weekly_quota' in habit and habit['weekly_quota']:
            preview += str(habit['weekly_quota']) + ' ' + _('times per week')

        if 'priority' in habit and habit['priority']:
            preview += ' (' + _('priority') + ' ' + str(habit['priority']) + ')'

        return preview


    def get_edit_habit_status_label_text(self, habit):
        if 'deleted_date' in habit and habit['deleted_date']:
            habit_info = _('Deleted')
            habit_info += ' ' + self.db_date_to_display_date(habit['deleted_date'])
        elif 'paused_until_date' in habit and habit['paused_until_date']:
            habit_info = _('Paused until')
            habit_info += ' '
            if self.db_date_to_dt(habit['paused_until_date']) == self.get_today_dt():
                habit_info += _('today')
            else:
                habit_info += self.db_date_to_display_date(habit['paused_until_date'])
        else:
            if 'created_date' in habit and habit['created_date']:
                habit_info = _('Active')
                habit_info += ' ('
                habit_info += _('Created on')
                habit_info += ' '
                habit_info += self.db_date_to_display_date(habit['created_date'])
                habit_info += ')'
            else:
                habit_info = _('Define habit')
        return habit_info 


    def on_activity_changed(self, widget):
        self.editing_habit['activity'] = widget.get_text()


    def get_edit_habit_weekly_quota_selector(self):
        # Selection of repeat weekly quota
        selector = self.create_weekly_quota_selector(self.editing_habit['weekly_quota'])
        title = _('Weekly Quota')
        selector.connect('changed', self.on_edit_habit_weekly_quota_changed)
        return selector


    def create_weekly_quota_selector(self, selected_weekly_quota = None):
        selector = hildon.TouchSelector(text = True)
        for i in range(8):
            selector.append_text(str(i))
            if str(i) == str(selected_weekly_quota):
                selector.set_active(0, i)
        return selector


    def create_measures_selector(self, selected_measure = None):
        measures = self.db.get_measures_list()
        selector = hildon.TouchSelector(text = True)
        index = 0
        for measure in measures:
            selector.append_text(measure['desc'])
            if str(measure['desc']) == str(selected_measure):
                selector.set_active(0, index)
            index += 1
        return selector


    def on_edit_habit_measure_changed(self, widget, user_data, preview_lbl):
        self.editing_habit['measure_desc'] = widget.get_current_text()
        self.set_target_picker_visibility()
        if self.editing_habit['measure_desc'] != NULL_MEASURE_DESC:
            self.editing_habit['null_measure'] = '0'
            measure_id, unit, plural = \
                    self.db.get_measure(self.editing_habit['measure_desc'])
            self.editing_habit['unit'] = unit
            self.editing_habit['plural'] = plural
        else:
            self.editing_habit['null_measure'] = '1'
            self.editing_habit['unit'] = ''
            self.editing_habit['plural'] = ''
        preview_lbl.set_text(self.get_edit_habit_preview_label_text(self.editing_habit))


    def create_priority_selector(self, selected_priority = None):
        selector = hildon.TouchSelector(text = True)
        for i in range(1,4):
            selector.append_text(str(i))
            if str(i) == str(selected_priority):
                selector.set_active(0, i - 1)
        return selector


    def on_edit_habit_priority_changed(self, widget, user_data, preview_lbl):
        self.editing_habit['priority'] = widget.get_current_text()
        preview_lbl.set_text(self.get_edit_habit_preview_label_text(self.editing_habit))


    def create_target_selector(self, selected_target = None):
        selector = hildon.TouchSelector(text = True)
        for i in range(101):
            selector.append_text(str(i))
            if str(i) == str(selected_target):
                selector.set_active(0, i)
        return selector


    def on_edit_habit_target_changed(self, widget, user_data, preview_lbl):
        self.editing_habit['target'] = widget.get_current_text()
        preview_lbl.set_text(self.get_edit_habit_preview_label_text(self.editing_habit))


    def on_edit_habit_weekly_quota_changed(self, widget, user_data, preview_lbl):
        self.editing_habit['weekly_quota'] = widget.get_current_text()
        preview_lbl.set_text(self.get_edit_habit_preview_label_text(self.editing_habit))


    def on_edit_habit_delete_btn_click(self, widget, status_lbl):
        if self.editing_habit['deleted_date']:
            widget.set_label(_('Delete'))
            self.editing_habit['deleted_date'] = None
        else:
            widget.set_label(_('Undelete'))
            self.editing_habit['deleted_date'] = self.dt_to_db_date(self.get_today_dt())
        status_lbl.set_text(self.get_edit_habit_status_label_text(self.editing_habit))


    def on_edit_habit_pause_cal_date_selected(self, cal, st_win, widget, status_lbl):
        paused_until_date_dt = self.get_gtk_cal_date_to_dt(cal)
        st_win.destroy()
        widget.set_label(_('Unpause'))
        self.editing_habit['paused_until_date'] = self.dt_to_db_date(paused_until_date_dt)
        status_lbl.set_text(self.get_edit_habit_status_label_text(self.editing_habit))


    def on_edit_habit_pause_btn_click(self, widget, status_lbl):
        if self.editing_habit['paused_until_date']:
            widget.set_label(_('Pause'))
            self.editing_habit['paused_until_date'] = None
            status_lbl.set_text(self.get_edit_habit_status_label_text(self.editing_habit))
        else:
            # parameters are date for calendar and whether to hide the 'Today' button
            st_win = self.get_general_calendar_window(None, True)
            st_win.set_title(_(WIN_TITLE_PAUSE_UNTIL_DATE))
            st_win.show_all()
            self.cal.connect('day_selected', self.on_edit_habit_pause_cal_date_selected, st_win, widget, status_lbl)


    def on_edit_habit_save_btn_click(self, widget):

        # Variable to record whether we have a valid habit record to save
        valid = None

        if self.editing_habit['activity'] and \
                self.editing_habit['measure_desc'] and \
                self.editing_habit['priority']:

            # If non-measurable we're valid...
            if self.editing_habit['null_measure'] == 1:
                valid = True

            # ...otherwise check we have a target
            else:
                if 'target' in self.editing_habit and self.editing_habit['target']:
                    valid = True
                else:
                    valid = False

        if valid:
            self.db.save_habit(self.editing_habit)
            self.show_info_banner(self.top_win, 'Habit "' + self.editing_habit['activity'] + '" saved')
            self.edit_win.destroy()
            self.redraw_day_habits_list()
            active_window_title = self.get_active_window_title()
            # Only try to redraw master habits list if it's the active window
            if hasattr(self, 'master_habits_list_model'):
                self.redraw_master_habits_list()
        else:
            self.show_info_banner (widget, _('Please ensure all fields are completed'))


    def on_edit_habit_window_destroy(self, win):
        # Clear data structures and widgets
        self.editing_habit = None


###################
# end of MainWindow 
###################





if __name__ == '__main__':
    MainWindow = MainWindow()
    #gtk.gdk.threads_enter()
    gtk.main()
    #gtk.gdk.threads_leave()
