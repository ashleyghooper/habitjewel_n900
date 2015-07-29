## This module contains some functions reused in the pyrecipe application ##

import gtk, gobject
import os
import hildon

fhsize = gtk.HILDON_SIZE_FINGER_HEIGHT
horbtn = hildon.BUTTON_ARRANGEMENT_HORIZONTAL

def show_info_banner(widget, msg):
    hildon.hildon_banner_show_information(widget, 'qgn_note_infoprint', msg)

##Return a ingredient list from the ingredients database
##ingredients database is "amount1||unit1||item1\namount2||unit2||item2\n"
##this function return [(amount1, unit1, item1), (amount2, unit2, item2)]
def ingredients_to_inglist(ingredients):
    if ingredients != '':
        il_l = ingredients.split('\n')
        ing_list = []
        for i in range(len(il_l)):
            new = il_l[i].split('||')
            if new == ['']:
                pass
            else:
                li_l = (new[0], new[1], new[2])
                ing_list.append(li_l)
    else:
        ing_list = []

    return ing_list

##Return the titles and ids of the all recipes in the database
##return a list similar to [(1, 'recipe1'), (2, 'recipe2')]
def get_recipe_list(sqlite_conn):
    lista = []
    #for row in sqlite_conn.execute('select id, title, category from recipes'):
    for row in sqlite_conn.execute('select id, title, category from recipes order by title'):
        lista.append(row)

    recipe_list=[]

    for i in range(len(lista)):
        ids = lista[i][0]
        titles = lista[i][1]
        cats = lista[i][2]
        recipe_ids = (ids, titles, cats)
    #    recipe_ids = (ids, titles)
        recipe_list.append(recipe_ids)

    return recipe_list

def is_portrait():
    width = gtk.gdk.screen_width()
    height = gtk.gdk.screen_height()
    if width > height:
        return False
    else:
        return True

#Show the hildon.filechooser dialog to open/save a file.
def show_filechooser_dialog(window, action, title, name, format, EXT):
    if action == 'open':
        action = gtk.FILE_CHOOSER_ACTION_OPEN
    elif action == 'save':
        action = gtk.FILE_CHOOSER_ACTION_SAVE

    m = hildon.FileSystemModel()
    file_dialog = hildon.FileChooserDialog(window, action, m)
    file_dialog.set_title(title + format)

    portrait = is_portrait()
    if portrait:
        hildon.hildon_gtk_window_set_portrait_flags(file_dialog, 1)

    file_dialog.set_current_name(name)
    HOME = os.path.expanduser("~")

    if os.path.exists(HOME + '/MyDocs/.documents'):
        file_dialog.set_current_folder(HOME + '/MyDocs/.documents')
    else:
        file_dialog.set_current_folder(HOME)

    file_dialog.set_default_response(gtk.RESPONSE_CANCEL)

    result = file_dialog.run()
    if result == gtk.RESPONSE_OK:
        namefile = file_dialog.get_filename()
        if (action==gtk.FILE_CHOOSER_ACTION_SAVE):
            namefile = file_dialog.get_filename()
            namefile, extension = os.path.splitext(namefile)
            namefile = namefile + "." + EXT

    else:
        namefile = None
    file_dialog.destroy()

    return namefile

##Save a file from a xml document ##
def save_xml_file(namefile, xmltext):
    success = False
    try:
        #FIXME: this is a stupid workaround because the < and > in the text
        #are saved as &gt; and &lt;
        file_object = open(namefile, "w")
        file_object.write(xmltext)
        file_object.close()
        file_object = open(namefile, "r")
        text = file_object.read()
        file_object.close()
        a = text.replace("&gt;", ">").replace("&lt;", "<")
        file_object = open(namefile, "w")
        file_object.write(a)
        file_object.close()
    except IOError, (errno, strerror):
        print "Error saving post(%s): %s" % (errno, strerror)
    else:
        success = True

    return success

##Show a confirmation dialog deleting recipes
def on_confirmation(window, msg):
    dialog = hildon.hildon_note_new_confirmation(window, msg)
    dialog.show_all()
    result = dialog.run()
    if result == gtk.RESPONSE_OK:
        dialog.destroy()
        return True

    dialog.destroy()
    return False

def light_confirmation(window, msg, btntext):
    dialog = gtk.Dialog(title='', parent=window,
            buttons=(btntext, gtk.RESPONSE_OK))
    label = gtk.Label(msg)
    dialog.vbox.pack_start(label, True, True, 0)

    dialog.show_all()
    result = dialog.run()
    if result == gtk.RESPONSE_OK:
        dialog.destroy()
        return True
    else:
        dialog.destroy()
        return False


#Show a information dialog
def info_dialog(window, msg):
    dialog = hildon.hildon_note_new_information(window, msg)
    dialog.show_all()
    dialog.run()
    dialog.destroy()
