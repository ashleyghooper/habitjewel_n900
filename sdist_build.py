#!/usr/bin/python
# -*- coding: utf-8 -*-
  
#habitjewel Setup File
 
import sys
reload(sys).setdefaultencoding("UTF-8")
 
try:
    from sdist_maemo import sdist_maemo as _sdist_maemo
except:
    _sdist_maemo = None
    print 'sdist_maemo command not available'
 
from distutils.core import setup
# import khweeteur
 
#Remove pyc and pyo file
import glob,os
for fpath in glob.glob('*/*.py[c|o]'):
    os.remove(fpath)
 
changes = '* Most basic functionality working'
 
setup(name='habitjewel',
      version='0.2.0',
      license='GNU GPLv3',
      description='Record and track your progress in achieving your daily habits.',
      long_description='HabitJewel is an application to track regular habits and their accomplishment. It allows habits that should repeat daily, or on specific days of the week, as well as habits that repeat each week, or some number of weeks. Ultimately it will keep track of accomplishment of the habits, award points, and allow some statistics and graphing.',
      author='Ashley Hooper',
      author_email='ashleyghooper@gmail.com',
      maintainer=u'Ashley Hooper',
      maintainer_email='ashleyghooper@gmail.com',
      requires=['python','hildondesktop', 'libpythonpluginloader' ],
      url='',
      packages= ['habitjewel'],
      package_data = {'habitjewel': ['icons/*.png']},
      data_files=[('/opt/habitjewel', ['habitjewel.py','habitjewel_utils.py','cell_renderer_clickable_pixbuf.py','n900_maemo5_portrait.py']),
                  ('/usr/share/applications/hildon', ['habitjewel.desktop']),
                 ],
      scripts=[''],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: Other",
        "Operating System :: Other OS",
        "Intended Audience :: End Users/Desktop",],
      cmdclass={'sdist_maemo': _sdist_maemo},
      options = { 'sdist_maemo':{
      'debian_package':'habitjewel',
      'buildversion':'1',
      'depends':'python2.5, python-hildondesktop, hildon-desktop-python-loader',
      'conflicts':'',
      'XSBC_Bugtracker':'',
      'XB_Maemo_Display_Name':'HabitJewel',
      'XB_Maemo_Icon_26':'/usr/share/icons/hicolor/48x48/hildon/calendar_todo.png',
      'XB_Maemo_Upgrade_Description':'%s' % changes,
      'section':'user/office',
      'changelog':changes,
      'architecture':'any',
#      'preinst':"""#!/bin/sh
#""",
      'postinst':"""#!/bin/sh
chown root:root /usr/share/applications/hildon/habitjewel.desktop
chmod 644       /usr/share/applications/hildon/habitjewel.desktop
chown root:root /usr/share/icons/hicolor/48x48/apps/habitjewel.png
chmod 644       /usr/share/icons/hicolor/48x48/apps/habitjewel.png
chown -R root:root       /opt/habitjewel
chmod -R u=rwX,g=rX,o=rX /opt/habitjewel
chmod 755 /opt/habitjewel/habitjewel.py
""",
#      'postre':"""#!/bin/sh
#""",
      },
      'bdist_rpm':{
      'requires':'python',
      'conflicts':'',
      'icon':'',
      'group':'Network',}}
     )
