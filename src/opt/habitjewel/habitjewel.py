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

VERSION = '0.1.1'

import datetime
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
from CellRendererClickablePixbuf import CellRendererClickablePixbuf

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
TV_HABIT_LIST_ID           = 0
TV_HABIT_LIST_DESC         = 1
TV_HABIT_LIST_PCT_COMPLETE = 2
TV_HABIT_LIST_PIXBUF       = 3
TV_HABIT_LIST_INTVL_TYPE   = 4
STATUS_FULFILLED_PCT    = 100
STATUS_UNFULFILLED_PCT  = 0
STATUS_UNKNOWN_PCT      = -1
PIXBUF_FILE_FULFILLED   = "checkbox_checked.png"
PIXBUF_FILE_UNFULFILLED = "checkbox_crossed.png"
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
            priority INTEGER, interval_type TEXT, interval TEXT,
            points INTEGER, created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE categories (id INTEGER PRIMARY KEY, title TEXT,
            created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE measures (id INTEGER PRIMARY KEY, unit TEXT, plural TEXT, desc TEXT,
            created_date DATE, deleted_date DATE)
        """)
    cursor.execute(
        """
        CREATE TABLE history (id INTEGER PRIMARY KEY, habit_id INTEGER, date DATE,
            percent_complete INTEGER)
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
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'Day', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 100, CURRENT_DATE)
        """, ['Meditate'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study French'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study Spanish'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study software development'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_type, interval, points, created_date)
            VALUES (?, 2, 2, 3, 'Day', 'Mon,Wed,Fri,Sun', 100, CURRENT_DATE)
        """, ['Walk'])
    cursor.execute(
        """
        INSERT INTO habits (activity, measure_id, target, priority,
            interval_type, interval, points, created_date)
            VALUES (?, 2, 50, 2, 'Week', '1', 100, CURRENT_DATE)
        """, ['Cycle'])
    
    conn.commit()
    cursor.close()




class MainWindow:

    def __init__(self):
        gettext.install('habitjewel','/opt/habitjewel/share/locale')

        # Get today's date and use that as the date displayed on startup
        today = datetime.date.today()
        self.view_date = today

        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name('Habitjewel')

        self.top_window = hildon.StackableWindow()
        self.top_window.set_title(_('HabitJewel'))

        # N900-specific
        self.osso_app_name = 'habitjewel'

        self.rotation_obj = self.init_autorotation()

        self.top_window.connect('destroy', gtk.main_quit)
        self.top_window.get_screen().connect('size-changed', self.orientation_changed)
        self.program.add_window(self.top_window)

        #self.rotation = FremantleRotation('HabitJewel', None, VERSION, 0)
        self.init_disp_orientation()

        self.fontsize = 15

        menu = self.make_menu()
        self.top_window.set_app_menu(menu)

        self.container = self.home_screen()
        self.top_window.add(self.container)

        self.top_window.show_all()


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


    def make_menu(self):
        """
        This is the menu for the main windows
        """
        menu = hildon.AppMenu()

        button = gtk.Button(_('New Habit'))
        button.connect('clicked', self.habit_edit_screen)
        menu.append(button)

        button = gtk.Button(_('Stats'))
        button.connect('clicked', self.stats)
        menu.append(button)

        button = gtk.Button(_('Go to Date'))
        button.connect('clicked', self.go_to_date)
        menu.append(button)

        button = gtk.Button(_('Delete'))
        button.connect('clicked', self.remove_habits)
        menu.append(button)

        button = gtk.Button(_('About'))
        button.connect('clicked', self.about)
        menu.append(button)

        menu.connect('event', self.event_catcher)

        menu.show_all()
        return menu


    def stats(self, widget):
        return


    def go_to_date(self, widget):
        st_win = hildon.StackableWindow()
        st_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox_cal = gtk.VBox()
        cal = self.get_calendar(self, self.view_date)
        vbox_cal.pack_start(cal, True, True) 
        st_win.add(vbox_cal)
        st_win.set_title('Go to Date')
        st_win.show_all()
        cal.connect('day_selected', self.calendar_date_selected, st_win)


    def get_calendar(self, widget, disp_date):
        #TODO: Increase size of calendar dates
        #TODO: Highlight days based on habit fulfillment
        cal = gtk.Calendar()
        cal.detail_height_rows = 20
        cal.no_month_change = False
        cal.select_month(disp_date.month, disp_date.year)
        cal.select_day(disp_date.day)
        return cal


    def calendar_date_selected(self, cal, st_win):
        year, month, day = cal.get_date()
        self.view_date = datetime.date(year, month, day)
        st_win.destroy()
        self.redraw_habit_list(self)


    def remove_habits(self, widget):
        return


    def about(self, widget):
        st_win = hildon.StackableWindow()
        st_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox_about = gtk.VBox()
        text = hildon.TextView()
        text.set_placeholder('About page')
        vbox_about.pack_start(text)
        st_win.add(vbox_about)
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

        # "Long press" context menu
        self.habit_list_menu = gtk.Menu()
        # "Emulate" hildon_gtk_menu_new
        self.habit_list_menu.set_name('hildon-context-sensitive-menu')
        menu_item = gtk.MenuItem(_('Edit'))
        self.habit_list_menu.append(menu_item)
        menu_item.connect('activate', self.edit_habit, self.habit_list_tv)
        self.habit_list_menu.show_all()
        self.habit_list_tv.tap_and_hold_setup(self.habit_list_menu)

        self.pan_area.add(self.habit_list_tv)

        self.vbox_outer.pack_start(self.vbox_nav, False)
        self.vbox_outer.pack_start(self.pan_area, True, True)

        return self.vbox_outer


    def on_habit_list_button_press(self, widget, event):
        result = self.habit_list_tv.get_path_at_pos(int(event.x), int(event.y))
        if result is not None:
            path, column, x, y = result
            model = self.habit_list_tv.get_model()
            index = model.get_value(model.get_iter(path), TV_HABIT_LIST_ID) - 1
            self.touched_habit = self.habit_list[index]
        else:
            self.touched_habit = None


    def create_habit_list_model(self, widget):
        lstore = gtk.ListStore(int, str, int, gtk.gdk.Pixbuf, str)
        # add columns to the tree view
        self.add_columns_to_habit_list(self.habit_list_tv)
        return lstore


    def prepare_habit_list(self, widget):
        self.habit_list = habitjewel_utils.get_habits_list(conn, self.view_date)

        for item in self.habit_list:
            lstore_iter = self.habit_list_model.append()
            icon_pixbuf = self.get_pixbuf_filename_for_status (item['pct_complete'])
 
            self.habit_list_model.set(lstore_iter, \
                TV_HABIT_LIST_ID, \
                    item['id'], \
                TV_HABIT_LIST_DESC, \
                    '<b>' + item['activity'] + '</b> ' + str(item['target_desc']) \
                    + ' <i>' + item['by_when'] + '</i>', \
                TV_HABIT_LIST_PCT_COMPLETE, \
                    item['pct_complete'], \
                TV_HABIT_LIST_PIXBUF, \
                    icon_pixbuf, \
                TV_HABIT_LIST_INTVL_TYPE, \
                    item['interval_type'] \
            )


    def get_pixbuf_filename_for_status(self, status):
        if (status == STATUS_FULFILLED_PCT):
            icon_filename = PIXBUF_FILE_FULFILLED
        elif (status == STATUS_UNFULFILLED_PCT):
            icon_filename = PIXBUF_FILE_UNFULFILLED
        else:
            icon_filename = PIXBUF_FILE_UNKNOWN

        return gtk.gdk.pixbuf_new_from_file(img_dir + icon_filename)
 

    def add_columns_to_habit_list(self, treeview):
        # column for ID
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=TV_HABIT_LIST_ID)
        column.set_visible(False)
        treeview.append_column(column)

        # column for activity
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', self.line_wrap_width)
        column = gtk.TreeViewColumn('Habit activity', renderer, markup=TV_HABIT_LIST_DESC)
        column.set_property('expand', True)
        treeview.append_column(column)

        # column for checkbox
        checkbox = CellRendererClickablePixbuf()
        checkbox.connect('clicked', self.habit_toggled, treeview)
        column = gtk.TreeViewColumn('Status', checkbox, pixbuf=TV_HABIT_LIST_PIXBUF)
        treeview.append_column(column)

        # column for percent complete
        column = gtk.TreeViewColumn('Percent complete', gtk.CellRendererText(), text=TV_HABIT_LIST_PCT_COMPLETE)
        column.set_visible(False)
        treeview.append_column(column)

        # column for interval type
        #column = gtk.TreeViewColumn('Interval type', gtk.CellRendererText(), text=4)
        #column.set_visible(False)
        #treeview.append_column(column)


    def habit_toggled(self, widget, row_num, treeview):
        # Toggle habit completion status (fulfilled / unfulfilled / unknown)
        model = treeview.get_model()
        iter = model.get_iter(row_num)
        current_status_pct = model[iter][TV_HABIT_LIST_PCT_COMPLETE]

        if (current_status_pct == STATUS_FULFILLED_PCT):
            percent_complete = STATUS_UNFULFILLED_PCT
        elif (current_status_pct == STATUS_UNFULFILLED_PCT):
            percent_complete = STATUS_UNKNOWN_PCT
        else:
            percent_complete = STATUS_FULFILLED_PCT

        habitjewel_utils.set_fulfillment_status (conn, \
            model[iter][TV_HABIT_LIST_ID], \
            model[iter][TV_HABIT_LIST_INTVL_TYPE], \
            self.view_date, \
            percent_complete \
        )
        model[iter][TV_HABIT_LIST_PIXBUF] = self.get_pixbuf_filename_for_status (percent_complete)
        model[iter][TV_HABIT_LIST_PCT_COMPLETE] = percent_complete


    def prev_day(self, widget):
        self.view_date = self.view_date - datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def next_day(self, widget):
        self.view_date = self.view_date + datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def get_date_label_text(self, widget):
        date_disp = self.view_date.strftime('%a %d %B %Y')
        return date_disp


    def redraw_habit_list(self, widget):
        label_text = self.get_date_label_text(self)
        self.date_label.set_text(label_text)
        self.habit_list_model.clear()
        self.prepare_habit_list(self)
        checkbox_col = self.habit_list_tv.get_column(2)
        today = datetime.date.today()
        if (self.view_date <= today):
            checkbox_col.set_visible(True)
        else:
            checkbox_col.set_visible(False)
        self.redraw_window()


    def redraw_window(self):
        self.top_window.queue_draw()


    def edit_habit (self, menu_item, widget):
        if not self.touched_habit:
            return
        else:
            self.habit_edit_screen (widget, self.touched_habit)


    #TODO: Everything below here
    #def habit_edit_screen(self, widget, habit_id=None):
    def habit_edit_screen(self, widget, habit=None):

        measures = habitjewel_utils.get_measures_list(conn)
        categories = habitjewel_utils.get_categories_list(conn)

        st_win = hildon.StackableWindow()
        st_win.get_screen().connect('size-changed', self.orientation_changed)
        vbox = gtk.VBox()

        if (not habit):
            win_title = _('Add new habit')
        else:
            win_title = _('Edit habit')
            #habit = habitjewel_utils.get_habit_details(conn, habit_id)

        # Draw new/edit habit form 

        table = gtk.Table(3, 2)
        #table.set_row_spacings(2)
        #table.set_col_spacings(2)

        # Habit activity
        l = gtk.Label()
        l.set_markup('<b>' + _('Activity') + '</b>')
        a_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        a_entry.set_text(habit['activity'])
        table.attach(l, 0, 1, 0, 1, gtk.FILL, 0)
        table.attach(a_entry, 1, 2, 0, 1)

        # Habit target
        # (change to SpinButton ?)
        l = gtk.Label()
        l.set_markup('<b>' + _('Target') + '</b>')
        #adj = gtk.Adjustment(habit['target'], 0, 100, 1, 0, 0)
        #t_spin = gtk.SpinButton(adj, 0, 0)
        #t_spin.set_numeric(t_spin)
        t_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        t_entry.set_text(str(habit['target']))
        table.attach(l, 0, 1, 1, 2, gtk.FILL, 0)
        table.attach(t_entry, 1, 2, 1, 2)

        # Habit measure
        l = gtk.Label()
        l.set_markup('<b>' + _('Measure') + '</b>')
        m_selector = hildon.TouchSelector(text = True)
        store_measures = gtk.ListStore(gobject.TYPE_INT, gobject.TYPE_STRING)
        for measure in measures:
            print str(measure)
            iter = store_measures.append()
            store_measures.set(iter, 0, measure['id'], 1, measure['desc'])
        m_entry = gtk.CellRendererText()
        column = m_selector.append_column(store_measures, m_entry, id = 0)
        column.set_property("text-column", 1)
        table.attach(l, 0, 1, 2, 3, gtk.FILL, 0)
        table.attach(m_selector, 1, 2, 2, 3)

        """
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=TV_HABIT_LIST_ID)
        column.set_visible(False)
        treeview.append_column(column)
        """

        """
        l = gtk.Label()
        l.set_markup('<b>' + _('Measure') + '</b>')
        m_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        m_entry.set_text(str(habit['measure']))
        table.attach(l, 0, 1, 1, 2, gtk.FILL, 0)
        table.attach(m_entry, 1, 2, 1, 2)
        """

        # Habit interval_type

        # Habit interval

        vbox.pack_start(table, True, True, 0)

        st_win.add(vbox)
        st_win.set_title(win_title)
        st_win.show_all()

        

        # Below goes after logic
        # vbox_cal.pack_start(cal, True, True) 
        # st_win.add(vbox_cal)
        # st_win.show_all()
        # cal.connect('day_selected', self.calendar_date_selected, st_win)

        # menu = self.make_edit_menu(kind)
        # win.set_app_menu(menu)

        """
        self.entitle = hildon.Entry(fhsize)
        self.entitle.set_placeholder(_('Title'))
        self.entitle.set_text(self.title)
        self.entitle.connect('changed', self.change_title)

        self.mainbox = gtk.VBox()
        self.mainbox.pack_start(self.entitle, False, False, 0)

        if self.is_portrait():
            self.mainbox.pack_start(self.freqbtn, False, False, 0)
            self.mainbox.pack_start(self.daysbtn, False, False, 0)

        else:
            self.hbox1 = gtk.HBox()
            self.hbox1.set_homogeneous(True)
            self.hbox1.pack_start(self.freqbtn, True, True, 0)
            self.hbox1.pack_start(self.daysbtn, True, True, 0)
            self.mainbox.pack_start(self.hbox1, False, False, 0)

        #self.mainbox.pack_start(toolbar, False, False, 0)

        win.add(self.mainbox)
        win.show_all()
        """

    def make_edit_menu(self, kind):
        kind = self.mode

        menu = hildon.AppMenu()

        button = gtk.Button(_('Save'))
        button.connect('clicked', self.save_habit)
        menu.append(button)

        menu.show_all()
        return menu


    def save_habit():
        return


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
