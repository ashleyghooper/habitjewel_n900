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
# Version 0.1
#

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

import habitjewel_utils


osso_c = osso.Context("org.maemo.habitjewel", VERSION, False)


fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL
verbtn = hildon.BUTTON_ARRANGEMENT_VERTICAL
ui_normal = gtk.HILDON_UI_MODE_NORMAL
ui_edit = gtk.HILDON_UI_MODE_EDIT
winprogind = hildon.hildon_gtk_window_set_progress_indicator
thsize = gtk.HILDON_SIZE_THUMB_HEIGHT

# Initialisation
HOME = os.path.expanduser("~")
configdir = HOME + '/.habitjewel/'
dbfile = configdir + 'database'
logfile = configdir + 'log.txt'

#detect if running locally or not
runningpath = sys.path[0]

if '/opt' in runningpath:
    locally = False
else:
    locally = True


# Check for config dir, database. Create if necessary
if not os.path.exists(configdir):
    os.mkdir(configdir)

if os.path.exists(dbfile):
    conn = sqlite3.connect(dbfile)
else:
    conn = sqlite3.connect(dbfile)
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


if locally:
    imgdir = 'pixmaps/'
else:
    appdir = '/opt/habitjewel/'
    imgdir = appdir + 'pixmaps/'


# Get today's date
view_date = datetime.date.today()


class MainWindow:

    def __init__(self):

        gettext.install('habitjewel','/opt/habitjewel/share/locale')
        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name("Habitjewel")

        self.window = hildon.StackableWindow()
        self.window.set_title(_("HabitJewel"))
        self.window.set_default_size(800, 480)
        self.window.connect("destroy", gtk.main_quit)
        self.program.add_window(self.window)

        self.rotation = FremantleRotation('HabitJewel', None, VERSION, 0)
        self.initialize_vars()

        self.fontsize = 15

        menu = self.make_menu()
        self.window.set_app_menu(menu)

        vbox = self.home_screen()
        self.window.add(vbox)

        self.window.show_all()


    def initialize_vars(self):
        self.title = ''
        self.mode = 'new'
        self.cat = _('Daily')


    def make_menu(self):
        """
        This is the menu for the main windows
        """
        menu = hildon.AppMenu()

        button = gtk.Button(_("Stats"))
        button.connect("clicked", self.stats)
        menu.append(button)

        button = gtk.Button(_("Go to Date"))
        button.connect("clicked", self.go_to_date)
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

    def go_to_date(self, widget):
        return

    def remove_habits(self, widget):
        return

    def about(self, widget):
        return

    def home_screen(self):
        vbox = gtk.VBox()

        parea = hildon.PannableArea()

        self.habitlist_tv = hildon.GtkTreeView(ui_normal)

        areaview = self.habitlist_tv.get_action_area_box()
        self.habitlist_tv.set_action_area_visible(True)

        hbox = gtk.HBox()
        img = gtk.image_new_from_icon_name("general_back", gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(img, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.connect("clicked", self.prev_day)
        button.add(hbox)
        areaview.pack_start(button, True, True, 0)

        hbox = gtk.HBox()
        img = gtk.image_new_from_icon_name("general_calendar", gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(img, True, True, 0)
        self.date_label = gtk.Label()
        self.draw_date_label(self)
        hbox.pack_start(self.date_label, True, True, 0)
        areaview.pack_start(hbox, True, True, 0)

        hbox = gtk.HBox()
        img = gtk.image_new_from_icon_name("general_forward", gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(img, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.connect("clicked", self.next_day)
        button.add(hbox)
        areaview.pack_start(button, True, True, 0)

        self.habit_list_model = self.create_habit_list_model(self)
        self.habitlist_tv.set_model(self.habit_list_model)
        self.prepare_habit_list(self)

        parea.add(self.habitlist_tv)
        vbox.pack_start(parea, True, True, 0)

        return vbox


    def create_habit_list_model(self, widget):
        lstore = gtk.ListStore(gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_INT, \
            gobject.TYPE_INT, gobject.TYPE_STRING)

        #habitlist=[[id, 'title', 'unit', 'plural', 'target', 'goal', 'when', 
        #   'interval_type', 'interval', 
        #   'points', 'pct_complete', 'score', 'priority', 'cat_id', 'cat_title']...]

        # add columns to the tree view
        self.add_columns_to_habit_list(self.habitlist_tv)

        return lstore


    def prepare_habit_list(self, widget):
        habitlist = habitjewel_utils.get_habit_list(conn, view_date)

        for item in habitlist:
            lstore_iter = self.habit_list_model.append()
            if (item[10] == 100):
                completed = 1
            else:
                completed = 0
            self.habit_list_model.set(lstore_iter, 0, item[0], \
                1, '<b>' + item[1] + '</b> ' + str(item[5]) \
                + ' <i>' + item[6] + '</i>  for ' + str(item[9]) + ' pts', \
                2, completed, 3, item[10], 4, item[7])


    def add_columns_to_habit_list(self, treeview):
        # column for ID
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=0)
        column.set_visible(False)
        treeview.append_column(column)

        # column for category
        #column = gtk.TreeViewColumn('Category', gtk.CellRendererText(), text=2)
        #column.set_visible(False)
        #treeview.append_column(column)

        # column for title
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', 700)
        column = gtk.TreeViewColumn('Habit title', renderer, markup=1)
        column.set_property("expand", True)
        treeview.append_column(column)

        # column for percent complete
        column = gtk.TreeViewColumn('Percent complete', gtk.CellRendererText(), text=3)
        column.set_visible(False)
        treeview.append_column(column)

        # column for interval type
        column = gtk.TreeViewColumn('Interval type', gtk.CellRendererText(), text=4)
        column.set_visible(False)
        treeview.append_column(column)

        # column for checkbox
        checkbox = gtk.CellRendererToggle()
        checkbox.connect("toggled", self.habit_toggled, treeview)
        column = gtk.TreeViewColumn('Status', checkbox, active=2)
        column.set_property("expand", True)
        treeview.append_column(column)


    def habit_toggled(self, widget, row_num, treeview):
        # Toggle habit completion status (0% / 100%)
        model = treeview.get_model()
        iter = model.get_iter(row_num)

        if (model[iter][3] < 100):
            percent_complete = 100
        else:
            percent_complete = 0

        habitjewel_utils.set_percent_complete (conn, model[iter][0], model[iter][4], view_date, \
            percent_complete)
        model[iter][3] = percent_complete
        model[iter][2] = not model[iter][2] 


    def prev_day(self, widget):
        global view_date
        view_date = view_date - datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def next_day(self, widget):
        global view_date
        view_date = view_date + datetime.timedelta(days=1)
        self.redraw_habit_list(self)


    def draw_date_label(self, widget):
        date_disp = view_date.strftime("%a %d %B %Y")
        self.date_label.set_text(date_disp)


    def redraw_habit_list(self, widget):
        self.draw_date_label(self)
        self.habit_list_model.clear()
        self.prepare_habit_list(self)
        self.redraw_window()


    def redraw_window(self):
        self.window.queue_draw()


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
