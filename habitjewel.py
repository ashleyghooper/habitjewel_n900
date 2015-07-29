#!/usr/bin/env python
# -*- coding: UTF8 -*-
# Copyright (C) 2015 Ashley Hooper
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
# HabitJewel: Habit tracking software
# Version 0.1
#

VERSION = '0.1'

import gtk
import hildon
import gobject
import logging
import pango
import sqlite3
import os
import habitjewel_utils
import base64
import gettext

import osso
osso_c = osso.Context("org.maemo.habitjewel", VERSION, False)

from portrait import FremantleRotation

fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL
verbtn = hildon.BUTTON_ARRANGEMENT_VERTICAL
ui_normal = gtk.HILDON_UI_MODE_NORMAL
ui_edit = gtk.HILDON_UI_MODE_EDIT
winprogind = hildon.hildon_gtk_window_set_progress_indicator
thsize = gtk.HILDON_SIZE_THUMB_HEIGHT

HOME = os.path.expanduser("~")
configdir = HOME + '/.habitjewel/'
logfile = configdir + 'log.txt'

#detect if is ran locally or not
import sys
runningpath = sys.path[0]

if '/opt' in runningpath:
    locally = False
else:
    locally = True

if not os.path.exists(configdir):
    os.mkdir(configdir)

if os.path.exists(configdir + 'database'):
    habitdb = sqlite3.connect(configdir + 'database')
else:
    habitdb = sqlite3.connect(configdir + 'database')
    cursor_sql = habitdb.cursor()
    print 'creating new database'
    cursor_sql.execute('CREATE TABLE habits (id INTEGER PRIMARY KEY, \
        title TEXT, created_date DATE, deleted_date DATE)')
    cursor_sql.execute('CREATE TABLE records (id INTEGER PRIMARY KEY, \
        habit_id INTEGER, date DATE, status TEXT)')
    cursor_sql.close()

if locally:
    imgdir = 'pixmaps/'
else:
    appdir = '/opt/habitjewel/'
    imgdir = appdir + 'pixmaps/'

logger = logging.getLogger('habitjewel')
logging.basicConfig(filename=logfile,level=logging.ERROR, filemode='w')

DEBUG = True

if DEBUG:
    #set the main logger to DEBUG
    logger.setLevel(logging.DEBUG)

    #Create a handler for console debug
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logger.debug("Starting log")

gtk.gdk.threads_init()

class MainWindow:
    def __init__(self):
        gettext.install('habitjewel','/opt/habitjewel/share/locale')
        self.program = hildon.Program()
        self.program.__init__()
        gtk.set_application_name("Habitjewel")

        self.window = hildon.StackableWindow()
        self.window.set_title(_("Habits"))
        self.window.set_default_size(800, 480)
        self.window.connect("destroy", gtk.main_quit)
        self.program.add_window(self.window)

        self.rotation = FremantleRotation('Habitjewel', None, VERSION, 0)
        self.initialize_vars()

        self.fontsize = 15

        menu = self.make_menu()
        self.window.set_app_menu(menu)

        vbox = self.initial_screen()
        self.window.add(vbox)

        self.window.show_all()


    def initialize_vars(self):
        self.title = ''
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
        button.connect("clicked", About)
        menu.append(button)

        menu.show_all()
        return menu

    def initial_screen(self):
        vbox = gtk.VBox()

        parea = hildon.PannableArea()

        self.habitlist_tv = hildon.GtkTreeView(ui_normal)

        areaview = self.habitlist_tv.get_action_area_box()
        self.habitlist_tv.set_action_area_visible(True)

        hbox = gtk.HBox()
        img = gtk.image_new_from_icon_name("general_add", gtk.ICON_SIZE_SMALL_TOOLBAR)
        img.set_alignment(0.95, 0.5)
        hbox.pack_start(img, True, True, 0)

        label = gtk.Label(_("New habit"))
        label.set_alignment(0.05, 0.5)
        hbox.pack_start(label, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.connect("clicked", self.habit_edit_screen, 'new', '0')
        button.add(hbox)
        areaview.pack_start(button, True, True, 0)

        habitlist = habitjewel_utils.get_habit_list(habitdb)
        self.habitlist_model = self.create_habit_list_model(habitlist)
        self.habitlist_tv.set_model(self.habitlist_model)

        self.habitlist_tv.connect("row-activated", self.view_habit, self.habitlist_model)

        # add columns to the tree view
        self.add_columns_to_habit_list(self.habitlist_tv)

        parea.add(self.habitlist_tv)
        vbox.pack_start(parea, True, True, 0)

        return vbox

    def remove_habits(self, widget):
        win = hildon.StackableWindow()
        win.fullscreen()
        toolbar = hildon.EditToolbar(_("Select habits to delete"), _("Delete"))
        win.set_edit_toolbar(toolbar)

        vbox = gtk.VBox()
        parea = hildon.PannableArea()
        tv = hildon.GtkTreeView(ui_edit)
        selection = tv.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        tv.set_model(self.habitlist_model)
        self._tv_remove_habits_columns(tv)
        parea.add(tv)

        toolbar.connect("button-clicked", self.delete_habits, selection)
        toolbar.connect_object("arrow-clicked", gtk.Window.destroy, win)

        vbox.pack_start(parea, True, True, 0)
        win.add(vbox)
        win.show_all()

    def _tv_remove_habits_columns(self, treeview):
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=0)
        column.set_visible(False)
        treeview.append_column(column)

        # column for title
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', 780)
        column = gtk.TreeViewColumn('Habit title', renderer, text=1)
        column.set_property("expand", True)
        treeview.append_column(column)

    def create_habit_list_model(self, habitlist):
        lstore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        #habitlist=[[id, 'title', 'category']...]
        for item in habitlist:
            lstore_iter = lstore.append()
            lstore.set(lstore_iter, 0, item[0], 1, item[1], 2, item[2])

        return lstore

    def add_columns_to_habit_list(self, treeview):
        model = treeview.get_model()

        # column for ID
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=0)
        column.set_visible(False)
        treeview.append_column(column)

        # column for category
        column = gtk.TreeViewColumn('Category', gtk.CellRendererText(), text=2)
        column.set_visible(False)
        treeview.append_column(column)

        # column for title
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', 780)
        column = gtk.TreeViewColumn('Habit title', renderer, text=1)
        column.set_sort_column_id(1)
        column.set_property("expand", True)
        treeview.append_column(column)

    #Delete the selected habits
    def delete_habits(self, widget, selection):
        if selection.count_selected_rows() == 0:
            self.show_info_banner(widget, _('No selected habit'))
            return

        selnum = selection.count_selected_rows()
        title = gettext.ngettext("Delete habit?", "Delete habits?", selnum)

        #show confirmation dialog
        confirmation = habitjewel_utils.on_confirmation(self.window, title)

        if confirmation == True:
            try:
                selmodel, selected = selection.get_selected_rows()
                iters = [selmodel.get_iter(path) for path in selected]
                for i in iters:
                    habit_id = selmodel.get_value(i, 0)
                    selmodel.remove(i)

                    #update sqlite database
                    habitdb.execute("delete from habits where id=%s"
                                    % int(habit_id))
                    habitdb.commit()

                self.show_info_banner(widget, _('Habits deleted'))
            except:
                logger.exception("Deleting habit")
                self.show_info_banner(widget, _("Error deleting habit"))
        else:
            return

    def is_portrait(self):
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        if width > height:
            return False
        else:
            return True

    def habit_edit_screen(self, widget, kind, habit_id):
        if kind == 'edit':
            titlewin = _('Editing habit')
            self.get_habit_data(habit_id)
        else:
            titlewin = _('Creating new habit')
            self.initialize_vars()

        win = hildon.StackableWindow()
        win.set_title(titlewin)

        menu = self.make_edit_menu(kind)
        win.set_app_menu(menu)

        win.get_screen().connect("size-changed", self.orientation_changed)


        self.entitle = hildon.Entry(fhsize)
        self.entitle.set_placeholder(_("Title"))
        self.entitle.set_text(self.title)
        self.entitle.connect("changed", self.change_title)

        self.freqbtn = hildon.PickerButton(fhsize, horbtn)
        freqdata = [_("Daily"), _("Weekdays"), _("Weekly")]
        selector = self.create_selector(freqdata, True)
        self.freqbtn.set_selector(selector)
        self.freqbtn.set_title(_("Frequency"))
        self.freqbtn.set_value(self.freq)
        self.freqbtn.connect("value-changed", self.change_freq)

        self.daysbtn = hildon.PickerButton(fhsize, horbtn)
        daydata = [_("Monday"), _("Tuesday"), _("Wednesday"),
                   _("Thursday"), _("Friday"), _("Saturday"),
                   _("Sunday") ]
        selector = self.create_selector(daydata, True)
        self.daysbtn.set_selector(selector)
        self.daysbtn.set_title(_("Days"))
        self.daysbtn.set_value(self.day)
        self.daysbtn.connect("value-changed", self.change_day)

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

    def change_title(self, entry):
        self.title = entry.get_text()

    def change_freq(self, button):
        self.freq = button.get_value()

    def change_days(self, button):
        self.days = button.get_value()

    def make_edit_menu(self, kind):
        kind = self.mode

        menu = hildon.AppMenu()

        button = gtk.Button(_("New"))
        button.connect("clicked", self.clear_habit)
        menu.append(button)

        button = gtk.Button(_("Save"))
        button.connect("clicked", self.save_habit)
        menu.append(button)

        menu.show_all()
        return menu

    #Save the edited habit
    def save_habit(self, widget):
        if self.title == '':
            self.show_info_banner(widget, _('Habits must have title'))
            return

        #self.mode = kind

        ##get ingredients from the treeview
        ingredient_list = []
        final_ing_list = ''

        if self.ingmodel:
            for row in self.ingmodel:
                amount = row[0]
                unit = row[1]
                ingredient = row[2]
                new_ing = amount + '||' + unit + '||' + ingredient
                ingredient_list.append(new_ing)

        for i in range(len(ingredient_list)):
            final_ing_list += ingredient_list[i]
            if i < len(ingredient_list)-1:
                final_ing_list += '\n'

        #treatment to self.imagefile
        #Create a pixbuf from the original image, and get the binary data
        #of the image from the buffer of a PIL Image
        #Difficult, but it works!
        #Check out if self.imagefile is a real file,
        #this means the image has been defined or changed
        if os.path.exists(self.imagefile):
            pixbuf = gtk.gdk.pixbuf_new_from_file(self.imagefile)
            w, h = self.set_thumbnail_size(pixbuf, 200)
            pixbuf = pixbuf.scale_simple(int(w), int(h), gtk.gdk.INTERP_BILINEAR)
            import Image
            dimensions = pixbuf.get_width(), pixbuf.get_height()
            stride = pixbuf.get_rowstride()
            pixels = pixbuf.get_pixels()
            mode = pixbuf.get_has_alpha() and "RGBA" or "RGB"
            im = Image.frombuffer(mode, dimensions, pixels, "raw", mode, stride, 1)

            import StringIO
            file1 = StringIO.StringIO()
            im.save(file1, "JPEG")
            contents = file1.getvalue()
            file1.close()
            imgtext = '"""' + base64.encodestring(contents) + '"""'
        else:
            imgtext = self.imagefile

        ##dump it to sqlite database
        #if it's a new habit
        if self.mode == 'new':
            try:
                sqlite_cursor = habitdb.cursor()
                sqlite_cursor.execute('INSERT INTO habits VALUES'
                            ' (null, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (self.title, self.cat, self.preptime, self.cooktime,
                            self.servings, final_ing_list, self.instructions,
                            self.notes, imgtext))

                habitdb.commit()

                new_habit_id = sqlite_cursor.lastrowid
                sqlite_cursor.close()

                new_item = [new_habit_id, self.title, self.cat]

                newiter = self.habitlist_model.append()
                self.habitlist_model.set(newiter, 0, new_item[0],
                                1, new_item[1], 2, new_item[2])

                #go to edit mode so further save will update the habit
                #and not create a new one
                self.mode = 'edit'
                self.edit_habit_id = new_habit_id

                self.show_info_banner(widget, _('New habit saved'))
            except:
                logger.exception("Saving new habit")
                self.show_info_banner(widget, _("Error saving habit"))

        #if it's an edited habit
        elif self.mode == 'edit':
            try:
                habit_id = self.edit_habit_id
                sqlite_cursor = habitdb.cursor()
                sqlite_cursor.execute('REPLACE INTO habits VALUES'
                            ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (habit_id,
                            self.title, self.cat, self.preptime, self.cooktime,
                            self.servings, final_ing_list, self.instructions,
                            self.notes, imgtext))

                habitdb.commit()
                sqlite_cursor.close()

                new_item = [habit_id, self.title, self.cat]

                ##update item in habit list treeview
                #FIXME: if it's from search -> not updated the search treeview
                seliter = self.habitlist_model.get_iter_from_string(str(int(habit_id)-1))
                if seliter:
                    habit_id = self.habitlist_model.get_value(seliter, 0)
                    title = self.habitlist_model.get_value(seliter, 1)
                    cat = self.habitlist_model.get_value(seliter, 2)
                    self.habitlist_model.set(seliter, 0, new_item[0],
                                            1, new_item[1], 2, new_item[2])


                else:
                    self.show_info_banner(widget,
                                        _('Error updating the habit list'))

                self.show_info_banner(widget, _('Habit edited'))
            except:
                logger.exception("Editing habit")
                self.show_info_banner(widget, _("Error editing habit"))

        self.imagefile = ''

    #Clear all widgets in the habit editor
    def clear_habit(self, widget):
        confirmation = habitjewel_utils.on_confirmation(self.window,
                        _('Create new habit?'))
        if confirmation == True:
            try:
                if self.ingmodel:
                    self.ingmodel.clear()

                self.initialize_vars()

                self.entitle.set_text(self.title)
                self.catbtn.set_value(self.cat)
                self.preptimebtn.set_value(self.preptime)
                self.cooktimebtn.set_value(self.cooktime)
                self.servingsbtn.set_value(self.servings)

                missing_img = gtk.gdk.pixbuf_new_from_file(imgdir + 'image.png')
                self.image.set_from_pixbuf(missing_img)

                self.show_info_banner(widget, _('New Habit'))
                self.mode = 'new'
            except:
                logger.exception("Clearing habit")
                self.show_info_banner(widget, _("Error initializing habit"))
        else:
            pass

    def edit_instructions(self, widget, kind):
        win = hildon.StackableWindow()
        win.set_title(_("Editing instructions"))

        vbox = gtk.VBox()
        parea = hildon.PannableArea()

        textview = hildon.TextView()
        textview.set_wrap_mode(gtk.WRAP_WORD)
        textview.set_editable(True)
        tbuffer = textview.get_buffer()
        tbuffer.set_text(self.instructions)
        tbuffer.connect("changed", self.change_instructions)

        parea.add(textview)
        vbox.pack_start(parea, True, True, 0)

        win.add(vbox)
        win.show_all()

    def change_instructions(self, textbuffer):
        start, end = textbuffer.get_bounds()
        self.instructions = textbuffer.get_text(start, end)

    def edit_notes(self, widget, kind):
        win = hildon.StackableWindow()
        win.set_title(_("Editing notes"))

        vbox = gtk.VBox()

        parea = hildon.PannableArea()

        textview = hildon.TextView()
        textview.set_wrap_mode(gtk.WRAP_WORD)
        textview.set_editable(True)
        tbuffer = textview.get_buffer()
        tbuffer.set_text(self.notes)
        tbuffer.connect("changed", self.change_notes)
        parea.add(textview)

        vbox.pack_start(parea, True, True, 0)

        win.add(vbox)
        win.show_all()

    def change_notes(self, textbuffer):
        start, end = textbuffer.get_bounds()
        self.notes = textbuffer.get_text(start, end)

    def edit_ingredients(self, widget, kind):
        win = hildon.StackableWindow()
        win.set_title(_("Editing ingredients"))

        vbox = gtk.VBox()

        parea = hildon.PannableArea()
        parea.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

        if not self.ingmodel:
            self.ingmodel = self.create_ingredient_list_model()
        self.ingredients_tv = hildon.GtkTreeView(ui_edit)
        self.ingredients_tv.set_headers_visible(True)
        self.ingredients_tv.set_model(self.ingmodel)
        # add columns to the tree view
        self.add_columns_to_ingredient_list(self.ingredients_tv)

        parea.add(self.ingredients_tv)
        vbox.pack_start(parea, True, True, 0)

        hbox = gtk.HBox()

        button = hildon.Button(fhsize, horbtn)
        #button.set_label("Add")
        img = gtk.Image()
        img.set_from_file(imgdir + "add.png")
        button.set_image(img)
        button.connect("clicked", self.add_ingredient_dlg, "", "", "", False, "")
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        img = gtk.Image()
        img.set_from_file(imgdir + "delete.png")
        button.set_image(img)
        #button.set_label("Delete")
        button.connect("clicked", self.delete_ingredient)
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        img = gtk.Image()
        img.set_from_file(imgdir + "edit.png")
        button.set_image(img)
        #button.set_label("Delete")
        button.connect("clicked", self.edit_one_ingredient)
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        img = gtk.Image()
        img.set_from_file(imgdir + "clear.png")
        button.set_image(img)
        #button.set_label("Clear")
        button.connect("clicked", self.clear_ingredients)
        hbox.pack_start(button, True, True, 0)

        vbox.pack_start(hbox, False, False, 0)

        win.add(vbox)
        win.show_all()

    def edit_one_ingredient(self, widget):
        selection = self.ingredients_tv.get_selection()
        selmodel, seliter = selection.get_selected()

        if seliter:
             amount = self.ingmodel.get_value(seliter, 0)
             unit = self.ingmodel.get_value(seliter, 1)
             ing = self.ingmodel.get_value(seliter, 2)
             print amount, unit, ing
        else:
            self.show_info_banner(widget, _('No selected ingredient'))
            return

        self.add_ingredient_dlg(widget, amount, unit, ing, True, seliter)

    def clear_ingredients(self, widget):
        confirmation = habitjewel_utils.light_confirmation(self.window,
                        _('Clear ingredients?'), _('Clear'))
        if confirmation == True:
            self.ingmodel.clear()

    def delete_ingredient(self, widget):
        confirmation = habitjewel_utils.light_confirmation(self.window,
                        _('Delete ingredient?'), _('Delete'))

        if confirmation == True:
            selection = self.ingredients_tv.get_selection()
            selmodel, seliter = selection.get_selected()

            if seliter:
                selmodel.remove(seliter)
            else:
                self.show_info_banner(widget, _('No selected ingredient'))
                return

    def add_ingredient_dlg(self, widget, amount, unit, ing, edit, seliter):
        if edit:
            title = _("Edit ingredient")
            btnlabel = "Edit"
        else:
            title = _("Add ingredient")
            btnlabel = "Add"

        dlg = gtk.Dialog(title=title, parent=None, flags=0)
        dlg.set_has_separator(False)

        self.ening = hildon.Entry(fhsize)
        self.ening.set_placeholder(_("Ingredient"))
        self.ening.connect("activate", self.on_add_ingredient, dlg, edit,
                            seliter)
        self.ening.set_text(ing)
        dlg.vbox.pack_start(self.ening, False, False, 0)

        self.enamount = hildon.Entry(fhsize)
        self.enamount.connect("activate", self.on_add_ingredient, dlg, edit,
                            seliter)
        self.enamount.set_placeholder(_("Amount"))
        self.enamount.set_text(amount)
        dlg.vbox.pack_start(self.enamount, False, False, 0)

        self.unit_btn = hildon.PickerButton(fhsize, horbtn)
        data = ["", _("can"), _("clove"), _("cup"), _("drop"), "fl oz", _("grains"), "g", "kg", _("large"),
                "l", _("medium"), "mg", "ml", "oz", _("packet"), _("pinch"), "lb",
                "qt", _("slices"), _("small"), "Tbsp", "tsp", _("whole")]
        selector = self.create_selector(data, True)
        self.unit_btn.set_selector(selector)
        self.unit_btn.set_title("Unit")
        self.unit_btn.set_value(unit)

        dlg.vbox.pack_start(self.unit_btn, False, False, 0)

        button = hildon.Button(fhsize, horbtn)
        button.set_label(btnlabel)
        button.connect("clicked", self.on_add_ingredient, dlg, edit, seliter)
        dlg.vbox.pack_start(button, False, False, 0)

        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def on_add_ingredient(self, widget, dlg, edit, seliter):
        ing = self.ening.get_text()

        if ing == '':
            self.show_info_banner(widget, _("Ingredients must have title"))

        unit = self.unit_btn.get_value()
        amount = self.enamount.get_text()
        dlg.destroy()


        item = [amount, unit, ing]
        if edit:
            self.ingmodel.set(seliter, 0, item[0], 1, item[1], 2, item[2])
        else:
            newiter = self.ingmodel.append()
            self.ingmodel.set(newiter, 0, item[0], 1, item[1], 2, item[2])


    def create_ingredient_list_model(self):
        lstore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                                gobject.TYPE_STRING)
        return lstore

    def add_columns_to_ingredient_list(self, treeview):
        model = treeview.get_model()

        column = gtk.TreeViewColumn(_('Amount'), gtk.CellRendererText(), text=0)
        treeview.append_column(column)

        column = gtk.TreeViewColumn(_('Unit'), gtk.CellRendererText(), text=1)
        treeview.append_column(column)

        column = gtk.TreeViewColumn(_('Ingredient'), gtk.CellRendererText(),
                                text=2)
        treeview.append_column(column)

    def get_habit_data(self, habit_id):
        #get id
        self.edit_habit_id = habit_id

        lista = []
        for row in habitdb.execute('select * from habits where id=%s'
                                    % int(self.edit_habit_id)):
            lista.append(row)


        self.title = lista[0][1]
        self.cat = lista[0][2]
        self.preptime = lista[0][3]
        self.cooktime = lista[0][4]
        self.servings = lista[0][5]
        self.instructions = lista[0][7]
        self.notes = lista[0][8]
        self.imagefile = lista[0][9]

        ##tratamiento a ingredientes:
        if lista[0][6] != '':
            il_l = lista[0][6].split('\n')
            #print lista[0][2]
            #new[0]-->amount
            #new[1]-->unit
            #new[2]-->ingredient
            self.ingmodel = self.create_ingredient_list_model()
            self.ingmodel.clear()
            for i in range(len(il_l)):
                new = il_l[i].split('||')
                if new == ['']:
                    pass
                else:
                    item = (new[0], new[1], new[2])
                    newiter = self.ingmodel.append()
                    self.ingmodel.set(newiter, 0, item[0], 1, item[1],
                                    2, item[2])


    #Select image in the habit editor
    def select_image(self, widget):
        m = hildon.FileSystemModel()
        dialog = hildon.FileChooserDialog(self.window,
                                        gtk.FILE_CHOOSER_ACTION_OPEN, m)
        dialog.set_title(_("Browse images"))
        dialog.set_default_response(gtk.RESPONSE_OK)
        folder = HOME + '/MyDocs/.images'
        if os.path.exists(folder):
            dialog.set_current_folder(folder)
        else:
            dialog.set_current_folder(os.path.expanduser("~"))

        dialog.show_all()
        result = dialog.run()
        if result == gtk.RESPONSE_OK:
            try:
                self.set_file_to_pixbuf(dialog.get_filename())
            except:
                print 'No image file selected.'
                result = None
        dialog.destroy()

    def set_file_to_pixbuf(self, filename):
        import gc
        try:
            self.imagefile = filename
            new_pixbuf = gtk.gdk.pixbuf_new_from_file(self.imagefile)
            w, h = self.set_thumbnail_size(new_pixbuf, 200)
            new_pixbuf = new_pixbuf.scale_simple(int(w), int(h),
                            gtk.gdk.INTERP_BILINEAR)
            self.image.set_from_pixbuf(new_pixbuf)
            del new_pixbuf
            gc.collect()
        except:
            logger.exception("Setting image")
            self.show_info_banner(widget, _("Error setting image"))

    #Get all parameters from a selected habit
    def get_habit_from_selection(self, widget, selection):
        if selection.count_selected_rows() == 0:
            self.show_info_banner(widget, _('No selected habit'))
            return None

        selmodel, selected = selection.get_selected_rows()
        iters = [selmodel.get_iter(path) for path in selected]

        lista = []
        try:
            for seliter in iters:
                habit_id = self.habitlist_model.get_value(seliter, 0)
                for row in habitdb.execute('select * from habits where id=%s'
                    % int(habit_id)):
                        lista.append(row)

            return lista
        except:
            logger.exception("Getting habit")
            self.show_info_banner(widget, _("Error getting habit"))
            return lista

    def select_habits_to_export(self, widget):
        win = hildon.StackableWindow()
        win.fullscreen()
        toolbar = hildon.EditToolbar(_("Select habits to export"), _("Export"))
        win.set_edit_toolbar(toolbar)

        vbox = gtk.VBox()
        parea = hildon.PannableArea()
        tv = hildon.GtkTreeView(ui_edit)
        selection = tv.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        tv.set_model(self.habitlist_model)
        self._tv_export_habits_columns(tv)
        parea.add(tv)

        toolbar.connect("button-clicked", self.show_export_dialog, selection)
        toolbar.connect_object("arrow-clicked", gtk.Window.destroy, win)

        vbox.pack_start(parea, True, True, 0)
        win.add(vbox)
        win.show_all()

    def _tv_export_habits_columns(self, treeview):
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=0)
        column.set_visible(False)
        treeview.append_column(column)

        # column for title
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        renderer.set_property('wrap-width', 780)
        column = gtk.TreeViewColumn('Habit title', renderer, text=1)
        column.set_property("expand", True)
        treeview.append_column(column)

    #Show the export dialog with its format options
    def show_export_dialog(self, widget, selection):
        dlg = gtk.Dialog(title=_('Export Formats'), parent=None)

        hbox = gtk.HBox()
        hbox.set_homogeneous(True)

        button = hildon.Button(fhsize, horbtn)
        button.set_title('HTML')
        button.connect("clicked", self.on_export, dlg, 'html', selection)
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.set_title('Gourmet XML')
        button.connect("clicked", self.on_export, dlg, 'gxml', selection)
        hbox.pack_start(button, True, True, 0)

        dlg.vbox.pack_start(hbox, True, True, 0)

        hbox = gtk.HBox()
        hbox.set_homogeneous(True)

        button = hildon.Button(fhsize, horbtn)
        button.set_title('KHabits')
        button.connect("clicked", self.on_export, dlg, 'khabits', selection)
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.set_title('MealMaster')
        button.connect("clicked", self.on_export, dlg, 'mealmaster', selection)
        hbox.pack_start(button, True, True, 0)

        dlg.vbox.pack_start(hbox, True, True, 0)

        dlg.show_all()

        result = dlg.run()
        dlg.destroy()

    #Export the selected habits depending of its chosen format
    def on_export(self, widget, dialog, format, selection):
        dialog.destroy()

        exphabit_list = self.get_habit_from_selection(widget, selection)

        if exphabit_list is None:
            #Not selected habit, go out
            return

        try:
            if format == 'html':
                from filters import html_export
                html_export.HTML(exphabit_list, self.window, widget)
            elif format == 'gxml':
                from filters import gourmet_xml_export as gxml_export
                gxml_export.GourmetXML(exphabit_list, self.window, widget)
            elif format == 'khabits':
                from filters import khabit_export
                khabit_export.KHabits(exphabit_list, self.window, widget)
            elif format == 'mealmaster':
                from filters import mealmaster_export
                mealmaster_export.MM(exphabit_list, self.window, widget)
        except:
            logger.exception("Exporting habit")
            self.show_info_banner(widget, _("Error exporting habit"))



    #Importing habits from some compatible format
    def on_import(self, widget):
        import thread
        filename = habitjewel_utils.show_filechooser_dialog(self.window, 'open',
                    _('Import habit '), '', '', '')

        if filename == None:
            print 'No importing habit.'
            return None
        else:

            winprogind(self.window, 1)
            thread.start_new_thread(self._do_import, (filename, widget))


    def _do_import(self, filename, widget):
        file_ext = os.path.splitext(filename)[1]

        khabits_ext = ['.kreml', '.kre']
        gourmet_ext = ['.grmt', '.xml']
        #mealmaster_ext = ['.mmf']

        try:
            if file_ext in khabits_ext:
                print 'importing as khabits'
                from filters import khabit_import as khabitI
                krec_imp = khabitI.KHabits()
                # habit_info == (title, category, preptime, cooktime, servings,
                # final_ing_list, instructions, notes)
                habits_info = krec_imp.initiation(filename)
            elif file_ext in gourmet_ext:
                print 'importing as gourmet'
                from filters import gourmet_xml_import as gxml_import
                gxml_imp = gxml_import.GourmetXML()
                habits_info = gxml_imp.initiation(filename)
            #elif file_ext in mealmaster_ext:
            #    print 'importing as mealmaster'
            #    from filters import mealmaster_import as mm_import
            #    mm_importer = mm_import.MM()
            #    habits_info = mm_importer.initiation(filename)
            #    print habits_info
            else:
                msg1 = _("Habitjewel doesn't recognize the format of the file\n"
                "It can import only Gourmet and Khabits files")
                winprogind(self.window, 0)
                gtk.gdk.threads_enter()
                habitjewel_utils.info_dialog(self.window, msg1)
                gtk.gdk.threads_leave()
                return

            if habits_info == None:
                return

            habitdb = sqlite3.connect(configdir + 'database')
            sqlite_cursor = habitdb.cursor()
            #img_filename = None yet.

            for i in range(len(habits_info[0])):

                sqlite_cursor.execute('INSERT INTO habits VALUES (null, ?, ?, ?, '
                                    '?, ?, ?, ?, ?, ?)', (habits_info[0][i][1],
                                    habits_info[1][i][1], habits_info[2][i][1],
                                    habits_info[3][i][1], habits_info[4][i][1],
                                    habits_info[5][i][1], habits_info[6][i][1],
                                    habits_info[7][i][1], habits_info[8][i][1]))

                habitdb.commit()

                new_habit_id = sqlite_cursor.lastrowid
                sqlite_cursor.close()

                new_item = [new_habit_id, habits_info[0][i][1], habits_info[1][i][1]]

                newiter = self.habitlist_model.append()
                self.habitlist_model.set(newiter, 0, new_item[0], 1, new_item[1], 2, new_item[2])

            winprogind(self.window, 0)
            gtk.gdk.threads_enter()
            self.show_info_banner(widget, _('New habits imported'))
            gtk.gdk.threads_leave()
        except:
            logger.exception("Importing habit")
            winprogind(self.window, 0)
            gtk.gdk.threads_enter()
            self.show_info_banner(widget, _("Error importing habit"))
            gtk.gdk.threads_leave()

    def show_timer(self, widget):
        import timer
        if self.timer_running:
            self.mytimer.show()
        else:
            self.timer_running = True
            self.mytimer = timer.Timer(imgdir, osso_c)

    #Create shopping list, if it's running show it
    def on_show_shopping_list(self, widget, ings):
        import shopping_list
        if self.shoplist_running:
            #If is from add_ingr_to_shoplist, create a new window
            #if it's from the "Shoplist" menu, show the last created window
            if ings == "":
                self.shoplist.show()
            else:
                self.shoplist = shopping_list.ShopGui(imgdir, ings)
        else:
            self.shoplist_running = True
            self.shoplist = shopping_list.ShopGui(imgdir, ings)

    def add_to_shoplist(self, widget, ings):
        allings = []
        if ings != '':
            il_l = ings.split('\n')
            for i in range(len(il_l)):
                new = il_l[i].split('||')
                if new == ['']:
                    pass
                else:
                    item = (new[0], new[1], new[2], False)
                    allings.append(item)

        self.on_show_shopping_list(widget, allings)

    def create_selector(self, data, entry):
        if entry:
            selector = hildon.TouchSelectorEntry(text=True)
        else:
            selector = hildon.TouchSelector(text=True)

        for i in range(len(data)):
            selector.append_text(data[i])

        return selector

    #Calculate the thumbnail size depending of its actual size
    def set_thumbnail_size(self, pixbuf, size):
        pix_width = pixbuf.get_width()
        pix_height = pixbuf.get_height()

        if pix_width > pix_height:
            w = size
            h = float(pix_height)/float(pix_width) * size
        elif pix_height > pix_width:
            h = size
            w = float(pix_width)/float(pix_height) * size
        elif pix_height == pix_width:
            h = size
            w = size
        else:
            print "Pixbuf size can't be calculated."

        return w, h

    def show_info_banner(self, widget, msg):
        hildon.hildon_banner_show_information(widget, 'qgn_note_infoprint', msg)

    #Increase or decrease the fontsize viewing the habit
    def on_key_press(self, widget, event, *args):
        if event.keyval == hildon.KEY_INCREASE:
            if self.fontsize >= 36:
                self.show_info_banner(widget, _('Maximun font reached'))
                return
            self.fontsize += 2
            self.habit_txtv.modify_font(pango.FontDescription("Monospace "
                                    + str(self.fontsize)))

        elif event.keyval == hildon.KEY_DECREASE:
            if self.fontsize <= 11:
                self.show_info_banner(widget, _('Minimal font reached'))
                return
            self.fontsize -= 2
            self.habit_txtv.modify_font(pango.FontDescription("Monospace "
                                    + str(self.fontsize)))

    def base64_to_pixbuf(self, b64img):
        jpg1 = base64.b64decode(b64img)
        loader = gtk.gdk.PixbufLoader()
        loader.write(jpg1)
        pixbuf = loader.get_pixbuf()
        loader.close()

        return pixbuf

class About:

    def __init__(self, widget):
        self.abdialog = gtk.Dialog()
        self.abdialog.set_title(_("About Habitjewel"))

        notebook = gtk.Notebook()
        notebook.set_show_tabs(False)
        notebook.set_scrollable(False)
        notebook.set_show_border(False)

        # Description page #
        vbox = gtk.VBox()

        label = gtk.Label()
        label.set_markup("<b><big>Habitjewel %s</big></b>" % VERSION)
        vbox.pack_start(label, True, True, 0)

        label = gtk.Label(_("Your cooking habits in your hand"))
        vbox.pack_start(label, True, True, 0)

        label = gtk.Label(_("GNU General Public License"))
        vbox.pack_start(label, True, True, 0)

        url = "http://habitjewel.garage.maemo.org"
        webbtn = gtk.LinkButton(url, "Web")
        vbox.pack_start(webbtn, True, True, 0)
        gtk.link_button_set_uri_hook(self.launch_browser)

        notebook.append_page(vbox, gtk.Label())

        # Credits page #
        vbox = gtk.VBox()
        textview = hildon.TextView()
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        text = """%s Daniel Martin Yerga (dyerga@gmail.com)
%s
%s

%s:
""" % (_("Written by"), _("Some icons used in Habitjewel are from the Allblack iconset by Mandarancio (mandarancio.deviantart.com)"), _("The example habits are using Creative-Commons Attribution-Share Alike 3.0 License. They are available in http://www.nibbledish.com/"), _("Translations"))
        textview.get_buffer().set_text(text)

        parea = hildon.PannableArea()
        parea.add(textview)

        vbox.pack_start(parea, True, True, 0)
        notebook.append_page(vbox, gtk.Label())


        # Donate page #
        vbox = gtk.VBox()

        textview = hildon.TextView()
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        text = _("""Habitjewel is a free software application.
Developing good software takes time and hard work.
Habitjewel's author develops the program in his spare time.
If you like the program and it's helpful, consider donating a small amount of money.
Donations are a great incentive and help the developer feel that the hard work is appreciated.
""")
        textview.get_buffer().set_text(text)

        parea = hildon.PannableArea()
        parea.add(textview)

        button = hildon.Button(fhsize, horbtn)
        button.set_title(_("Make donation"))
        url = "http://habitjewel.garage.maemo.org/donate.html"
        button.connect("clicked", self.launch_browser, url)
        vbox.pack_start(button, False, False, 0)
        vbox.pack_start(parea, True, True, 0)

        notebook.append_page(vbox, gtk.Label())

        # Report page #
        vbox = gtk.VBox()

        textview = hildon.TextView()
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        text = _("""Habitjewel is being improved thanks to bug reports that users have submitted. The author appreciates these reports.
If the application is having an error when you're using it, you have two choices to report this error:
1) Send the log from the button above (if there's an error in the log).
2) Press the button and read how to report a bug.""")
        textview.get_buffer().set_text(text)

        parea = hildon.PannableArea()
        parea.add(textview)

        hbox = gtk.HBox()
        hbox.set_homogeneous(True)

        button = hildon.Button(fhsize, horbtn)
        button.set_title(_("Report error"))
        url = "http://habitjewel.garage.maemo.org/reporting.html"
        button.connect("clicked", self.launch_browser, url)
        hbox.pack_start(button, True, True, 0)

        button = hildon.Button(fhsize, horbtn)
        button.set_title(_("Log"))
        button.connect("clicked", self.on_show_log)
        hbox.pack_start(button, True, True, 0)

        vbox.pack_start(hbox, False, False, 0)
        vbox.pack_start(parea, True, True, 0)

        notebook.append_page(vbox, gtk.Label())

        # Rate page #
        vbox = gtk.VBox()

        textview = hildon.TextView()
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        text = _("""The downloads section in maemo.org has a nice system where you can rate applications.
If you consider Habitjewel a good application (or a bad one too), you could rate it in maemo.org site.""")
        textview.get_buffer().set_text(text)

        button = hildon.Button(fhsize, horbtn)
        button.set_title(_("Rate Habitjewel"))
        url = "http://maemo.org/downloads/product/Maemo5/habitjewel"
        button.connect("clicked", self.launch_browser, url)
        image = gtk.Image()
        image.set_from_file(imgdir + "maemoorg.png")
        vbox.pack_start(button, False, False, 0)
        vbox.pack_start(image, False, False, 5)
        vbox.pack_start(textview, True, True, 0)

        notebook.append_page(vbox, gtk.Label())

        # Buttons #
        self.abdialog.vbox.pack_start(notebook, True, True, 0)

        hbox = gtk.HBox()

        descbutton = hildon.GtkRadioButton(fhsize)
        descbutton.set_mode(False)
        descbutton.set_active(True)
        descbutton.set_label(_('Description'))
        descbutton.connect("toggled", self.change_tab, notebook, 0)
        hbox.pack_start(descbutton, True, True, 0)

        button = hildon.GtkRadioButton(fhsize)
        button.set_mode(False)
        button.set_active(True)
        button.set_label(_('Credits'))
        button.set_group(descbutton)
        button.connect("toggled", self.change_tab, notebook, 1)
        hbox.pack_start(button, True, True, 0)

        button = hildon.GtkRadioButton(fhsize)
        button.set_mode(False)
        button.set_label(_('Donate'))
        button.set_group(descbutton)
        button.connect("clicked", self.change_tab, notebook, 2)
        hbox.pack_start(button, True, True, 0)

        button = hildon.GtkRadioButton(fhsize)
        button.set_mode(False)
        button.set_label(_('Report'))
        button.set_group(descbutton)
        button.connect("clicked", self.change_tab, notebook, 3)
        hbox.pack_start(button, True, True, 0)

        button = hildon.GtkRadioButton(fhsize)
        button.set_mode(False)
        button.set_label(_('Rate'))
        button.set_group(descbutton)
        button.connect("clicked", self.change_tab, notebook, 4)
        hbox.pack_start(button, True, True, 0)

        self.abdialog.vbox.pack_start(hbox, False, False, 0)

        self.abdialog.show_all()
        self.abdialog.run()
        self.abdialog.destroy()

    def change_tab(self, widget, notebook, number):
        notebook.set_current_page(number)

    def launch_browser(self, widget, url):
        import dbus
        bus = dbus.SystemBus()
        proxy = bus.get_object("com.nokia.osso_browser", "/com/nokia/osso_browser/request")
        iface = dbus.Interface(proxy, 'com.nokia.osso_browser')

        self.abdialog.destroy()

        iface.open_new_window(url)

    def on_show_log(self, widget):
        Log(widget, logfile)


class Log:

    def __init__(self, widget, logfile):
        #Log dialog UI
        dialog = gtk.Dialog(title='Log', parent=None)

        dialog.set_size_request(600, 350)

        parea = hildon.PannableArea()
        parea.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)

        textview = hildon.TextView()
        textview.set_property("editable", False)
        textview.set_property("wrap-mode", gtk.WRAP_WORD)

        log = open(logfile, 'r')
        logtext = log.read()
        log.close()

        textview.get_buffer().set_text(logtext)
        parea.add(textview)

        dialog.vbox.pack_start(parea, True, True, 0)

        hbox = gtk.HBox()

        save_btn = hildon.Button(fhsize, horbtn)
        save_btn.set_title("Save")
        save_btn.connect('clicked', self.save, logfile, dialog)

        clear_btn = hildon.Button(fhsize, horbtn)
        clear_btn.set_title("Clear")
        clear_btn.connect('clicked', self.clear, textview, logfile)

        send_btn = hildon.Button(fhsize, horbtn)
        send_btn.set_title('Send')
        send_btn.connect('clicked', self.send, dialog, logfile)

        hbox.pack_start(save_btn, True, True, 0)
        hbox.pack_start(clear_btn, True, True, 0)
        hbox.pack_start(send_btn, True, True, 0)

        dialog.vbox.pack_start(hbox, False, False, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def clear(self, widget, textview, logfile):
        textview.get_buffer().set_text('')
        f = open(logfile, 'w')
        f.close()

    def save(self, widget, logfile, dlg):
        import shutil
        filename = habitjewel_utils.show_filechooser_dialog(dlg, "save",
                    "Save log file", "habitjewel-log", "", "txt")

        if not filename:
            return

        try:
            shutil.copyfile(logfile, filename)
            MainWindow.show_info_banner(widget, 'Log file saved')
        except:
            logger.exception("Saving log file")
            MainWindow.show_info_banner(widget, 'Error saving the log file')

    def send(self, widget, dlg, logfile):
        sendtxt = ("You are going to send the log to the developers.\n"
        "This helps the developers to track problems with the application.\n"
        "It doesn't send any personal information (like passwords or similar).")

        dialog = hildon.hildon_note_new_confirmation(dlg, sendtxt)
        dialog.set_button_texts("Send", "Cancel")
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.do_pre_send(dlg, logfile)

        dialog.destroy()


    def do_pre_send(self, dlg, logfile):
        import thread
        hildon.hildon_gtk_window_set_progress_indicator(dlg, 1)
        thread.start_new_thread(self._do_send, (dlg, logfile))

    def _do_send(self, dlg, logfile):
        import pycurl, shutil, random, commands
        try:
            rname = ''
            for i in random.sample('abcdefghijkl123456789', 18):
                rname += i

            rnamepath = HOME + "/.habitjewel/" + rname
            shutil.copyfile(logfile, rnamepath)

            gtkversion = "%s.%s.%s" % gtk.ver
            if os.path.exists("/etc/maemo_version"):
                mfile = open("/etc/maemo_version", 'r')
                maemoversion = mfile.read()
                mfile.close()
            else:
                maemoversion = ''

            opsystem = ' '.join(os.uname())
            pyversion = os.sys.version
            pid = os.getpid()
            comm = ("awk '/Private_Dirty/{sum+=$2}END{print sum \"kB\"}'"
            " /proc/%s/smaps") % pid
            status, dirtymem = commands.getstatusoutput(comm)

            lfile = open(rnamepath, 'r')
            log = lfile.read()
            lfile.close()

            _version = "Habitjewel 0.2 beta1 rev1"

            log = ("%s\nPython version: %s\nGtk version: %s\n"
            "Maemo version: %sOperating system: %s\n"
            "Dirty Memory: %s\nLog:\n%s") % (_version, pyversion, gtkversion,
            maemoversion, opsystem, dirtymem, log)

            lfile = open(rnamepath, 'w')
            lfile.write(log)
            lfile.close()

            url = "http://yerga.net/logs/uploader.php"
            data = [('uploadedfile', (pycurl.FORM_FILE, rnamepath)),]
            mycurl = pycurl.Curl()
            mycurl.setopt(pycurl.URL, url)
            mycurl.setopt(pycurl.HTTPPOST, data)

            mycurl.perform()
            mycurl.close()
            os.remove(rnamepath)

            gtk.gdk.threads_enter()
            MainWindow.show_info_banner(dlg, 'Log sent')
            gtk.gdk.threads_leave()
            hildon.hildon_gtk_window_set_progress_indicator(dlg, 0)
        except:
            logger.exception("Sending log file")
            gtk.gdk.threads_enter()
            MainWindow.show_info_banner(dlg, 'Error sending the log file')
            gtk.gdk.threads_leave()
            hildon.hildon_gtk_window_set_progress_indicator(dlg, 0)


if __name__ == "__main__":
    MainWindow = MainWindow()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
