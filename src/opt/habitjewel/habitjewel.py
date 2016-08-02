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

VERSION = '0.1'

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

# Unused?
WIN_PROG_IND = hildon.hildon_gtk_window_set_progress_indicator
OSSO_CONTEXT = osso.Context("org.maemo.habitjewel", VERSION, False)


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
home = os.path.expanduser("~")
config_dir = home + '/.habitjewel/'
db_file = config_dir + 'database'
log_file = config_dir + 'log.txt'


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
        CREATE TABLE habits (id INTEGER PRIMARY KEY, title TEXT,
            measure_id INTEGER, target INTEGER,
            priority INTEGER, category_id INTEGER, interval_type TEXT, interval TEXT,
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
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 1, 'Day', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', 100, CURRENT_DATE)
        """, ['Meditate'])
    cursor.execute(
        """
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 3, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study French'])
    cursor.execute(
        """
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 3, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study Spanish'])
    cursor.execute(
        """
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 1, 30, 1, 3, 'Week', '1', 100, CURRENT_DATE)
        """, ['Study software development'])
    cursor.execute(
        """
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 2, 2, 3, 2, 'Day', 'Mon,Wed,Fri,Sun', 100, CURRENT_DATE)
        """, ['Walk'])
    cursor.execute(
        """
        INSERT INTO habits (title, measure_id, target, priority, category_id,
            interval_type, interval, points, created_date)
            VALUES (?, 2, 50, 2, 2, 'Week', '1', 100, CURRENT_DATE)
        """, ['Cycle'])
    
    conn.commit()
    cursor.close()


# Get today's date and use that as the date displayed on startup
today = datetime.date.today()
view_date = today


class MainWindow:

    def __init__(self):
        gettext.install('habitjewel','/opt/habitjewel/share/locale')
        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name("Habitjewel")

        self.top_window = hildon.StackableWindow()
        self.top_window.set_title(_("HabitJewel"))

        # N900-specific
        self.osso_app_name = 'habitjewel'

        self.rotation_obj = self.init_autorotation()

        self.top_window.connect("destroy", gtk.main_quit)
        self.top_window.get_screen().connect("size-changed", self.orientation_changed)
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

        button = gtk.Button(_("Stats"))
        button.connect("clicked", self.stats)
        menu.append(button)

        button = gtk.Button(_("Go to Date"))
        button.connect("clicked", self.display_calendar)
        menu.append(button)

        button = gtk.Button(_("Delete"))
        button.connect("clicked", self.remove_habits)
        menu.append(button)

        button = gtk.Button(_("About"))
        button.connect("clicked", self.about)
        menu.append(button)

        menu.show_all()
        return menu


    def stats(self, widget):
        return


    def display_calendar(self, widget):
        TODO: Increase size of calendar dates
        TODO: Highlight days based on habit fulfillment
        self.win = hildon.StackableWindow()
        self.win.set_title('Go to Date')
        self.win.get_screen().connect("size-changed", self.orientation_changed)
        vbox_cal = gtk.VBox()
        cal = gtk.Calendar()
        cal.select_month(view_date.month, view_date.year)
        cal.select_day(view_date.day)
        vbox_cal.pack_start(cal) 
        cal.connect("day_selected", self.calendar_date_selected)
        self.win.add(vbox_cal)
        self.win.show_all()


    def calendar_date_selected(self, cal):
        global view_date
        year, month, day = cal.get_date()
        view_date = datetime.date(year, month, day)
        self.win.destroy()
        self.redraw_habit_list(self)


    def remove_habits(self, widget):
        return


    def about(self, widget):
        return


    def home_screen(self):
        self.vbox_outer = gtk.VBox(False)
        self.pan_area = hildon.PannableArea()

        self.habit_list_tv = hildon.GtkTreeView(UI_NORMAL)
        self.areaview = self.habit_list_tv.get_action_area_box()

        # HBox for 'prev' button
        self.hbox_prev = gtk.HBox()
        self.img_prev = gtk.image_new_from_icon_name("general_back", gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_prev.pack_start(self.img_prev)
        # 'Prev' button
        self.button_prev = hildon.Button(self.button_size, BTN_ARR_HORIZ)
        self.button_prev.connect("clicked", self.prev_day)
        self.button_prev.add(self.hbox_prev)

        # HBox for date display
        self.hbox_date = gtk.HBox()
        self.img_date = gtk.image_new_from_icon_name("general_calendar", gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_date.pack_start(self.img_date)
        label_text = self.get_date_label_text(self)
        self.date_label = gtk.Label(label_text)
        self.hbox_date.pack_start(self.date_label)

        # HBox for 'next' button
        self.hbox_next = gtk.HBox()
        self.img_next = gtk.image_new_from_icon_name("general_forward", gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.hbox_next.pack_start(self.img_next)
        # 'Next' button
        self.button_next = hildon.Button(self.button_size, BTN_ARR_HORIZ)
        self.button_next.connect("clicked", self.next_day)
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

        self.pan_area.add(self.habit_list_tv)

        self.vbox_outer.pack_start(self.vbox_nav, False)
        self.vbox_outer.pack_start(self.pan_area, True, True)

        return self.vbox_outer


    def create_habit_list_model(self, widget):
        lstore = gtk.ListStore(int, str, int, gtk.gdk.Pixbuf, str)
        # add columns to the tree view
        self.add_columns_to_habit_list(self.habit_list_tv)

        return lstore


    def prepare_habit_list(self, widget):
        habit_list = habitjewel_utils.get_habit_list(conn, view_date)

        for item in habit_list:
            lstore_iter = self.habit_list_model.append()
            icon_pixbuf = self.get_pixbuf_filename_for_status (item['pct_complete'])
 
            self.habit_list_model.set(lstore_iter, \
                TV_HABIT_LIST_ID, \
                    item['id'], \
                TV_HABIT_LIST_DESC, \
                    '<b>' + item['title'] + '</b> ' + str(item['goal']) \
                    + ' <i>' + item['by_when'] + '</i>  for ' \
                    + str(item['points']) + ' pts', \
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

        # column for title
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', self.line_wrap_width)
        column = gtk.TreeViewColumn('Habit title', renderer, markup=TV_HABIT_LIST_DESC)
        column.set_property("expand", True)
        treeview.append_column(column)

        # column for checkbox
        checkbox = CellRendererClickablePixbuf()
        checkbox.connect("clicked", self.habit_toggled, treeview)
        column = gtk.TreeViewColumn('Status', checkbox, pixbuf=TV_HABIT_LIST_PIXBUF)
        treeview.append_column(column)

        # column for percent complete
        column = gtk.TreeViewColumn('Percent complete', gtk.CellRendererText(), text=TV_HABIT_LIST_PCT_COMPLETE)
        column.set_visible(False)
        treeview.append_column(column)

        # column for category
        #column = gtk.TreeViewColumn('Category', gtk.CellRendererText(), text=2)
        #column.set_visible(False)
        #treeview.append_column(column)

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
            view_date, \
            percent_complete \
        )
        model[iter][TV_HABIT_LIST_PIXBUF] = self.get_pixbuf_filename_for_status (percent_complete)
        model[iter][TV_HABIT_LIST_PCT_COMPLETE] = percent_complete


    def prev_day(self, widget):
        global view_date
        view_date = view_date - datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def next_day(self, widget):
        global view_date
        view_date = view_date + datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def get_date_label_text(self, widget):
        date_disp = view_date.strftime("%a %d %B %Y")
        return date_disp


    def redraw_habit_list(self, widget):
        label_text = self.get_date_label_text(self)
        self.date_label.set_text(label_text)
        self.habit_list_model.clear()
        self.prepare_habit_list(self)
        checkbox_col = self.habit_list_tv.get_column(2)
        if (view_date <= today):
            checkbox_col.set_visible(True)
        else:
            checkbox_col.set_visible(False)
        self.redraw_window()


    def redraw_window(self):
        self.top_window.queue_draw()


    #TODO: Everything below here
    def habit_edit_screen(self, widget, kind, habit_id):
        print "kind = "
        print kind
        print "habit_id = "
        print habit_id
        if kind == 'edit':
            titlewin = _('Editing habit')
#            self.get_habit_data(habit_id)
        else:
            titlewin = _('Creating new habit')
#            self.initialize_vars()

        win = hildon.StackableWindow()
        win.set_title(titlewin)

        menu = self.make_edit_menu(kind)
        win.set_app_menu(menu)

        win.get_screen().connect("size-changed", self.orientation_changed)

        self.entitle = hildon.Entry(fhsize)
        self.entitle.set_placeholder(_("Title"))
        self.entitle.set_text(self.title)
        self.entitle.connect("changed", self.change_title)

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


    def make_edit_menu(self, kind):
        kind = self.mode

        menu = hildon.AppMenu()

        button = gtk.Button(_("Save"))
        button.connect("clicked", self.save_habit)
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
