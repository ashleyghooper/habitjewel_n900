#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
import pypackager
import os
p=pypackager.PyPackager("habitjewel") #package name
p.display_name = 'HabitJewel' #package display name in HAM
p.version = '0.1.2' #package version
p.buildversion = '1' #package build version
p.description="""HabitJewel is an application to track regular habits and their accomplishment. It allows habits that should repeat daily, or on specific days of the week, as well as habits that repeat each week, or some number of weeks.

Ultimately it will keep track of accomplishment of the habits, award points, and allow some statistics and graphing.""" #package description
p.author='Ashley Hooper' #package author
p.maintainer='Ashley Hooper' #package maintainer
p.email='ashleyghooper@gmail.com' #package maintainer email
p.depends = "python2.5, python-hildondesktop, hildon-desktop-python-loader" #package dependancies
p.section="user/office" #package section
p.arch="armel" #package arch
p.urgency="low" #package urgency
p.distribution="fremantle" #package distribution
p.repository="extras-devel" #package repository
p.bugtracker = 'ashleyghooper@gmail.com' #bug tracker field (could be a link http://bugs.maemo.org)
#p.preinstall="""#!/bin/sh
#"""
p.postinstall="""#!/bin/sh
chown root:root /usr/share/applications/hildon/habitjewel.desktop
chmod 644       /usr/share/applications/hildon/habitjewel.desktop
chown root:root /usr/share/icons/hicolor/48x48/apps/habitjewel.png
chmod 644       /usr/share/icons/hicolor/48x48/apps/habitjewel.png
chown -R root:root       /opt/habitjewel
chmod -R u=rwX,g=rX,o=rX /opt/habitjewel
chmod 755 /opt/habitjewel/habitjewel.py
""" # A post install script to set +x flag

#p.postremove="""#!/bin/sh
#"""
p.changelog ="""
v0.1.2
  * Fixed rotation, graphical checkboxes, refactor, etc
v0.1.1
  * Fixed display bugs
v0.1.0
  * Initial release to Maemo 5 Fremantle repositories (Nokia N900).
""" # the changelog
dir_name='src' #src directory name
#Here we will loop in all files, directory in src to add it to pkg
for root, dirs, files in os.walk(dir_name):
  real_dir = root[len(dir_name):]
  fake_file = []
  for f in files:
      fake_file.append(root + os.sep + f + "|" + f)
  if len(fake_file) > 0:
      p[real_dir] = fake_file
#Generate a package src
print p.generate(build_binary=False,build_src=True)
#Generate a binary src
print p.generate(build_binary=True,build_src=False)
