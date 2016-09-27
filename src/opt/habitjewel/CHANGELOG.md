## [Unreleased]
### Added

### Changed
## [0.8.0] - 2016-09-26
### Changed
- Fixed schema upgrade bug that caused habits table to be recreated without primary key

## [0.7.5] - 2016-09-19
### Changed
- Ditched gstreamer for calling aplay via os.system() to try to fix battery drain issue

## [0.7.4] - 2016-09-18
### Changed
- Tweaks to timer to address potential battery drain issue

## [0.7.3] - 2016-09-15
### Changed
- Changed wording of Target time label on timer page to be less ambiguous

## [0.7.2] - 2016-09-15
### Changed
- Fixed crash when exiting timer that is running

## [0.7.1] - 2016-09-13
### Added
- Icon on timer start/stop button

### Changed
- Nicer formatting and colouring of habits in day habits list
- Other display tweaks
- Moved change log from main script to CHANGELOG.md (this file)

## [0.7.0] - 2016-09-12
### Added
- Countdown timer with audible alarm, accessible for time-based habits on current date only

## [0.6.1] - 2016-09-11
### Changed
- Refactored history gathering
- Tweaked mini bar graph display
- Disabled main menu Stats button (for now)

## [0.6.0] - 2016-09-11
### Added
- Mini bar-graphs next to each habit which display completion status for previous days

### Changed
- Created HabitJewelDB class and moved all database functions there
- Added schema version check and upgrade script for schema vers 0.4 and 0.5
- Bumped minor version number due to schema changes

## [0.5.0] - 2016-09-01
### Added
- New Habit button and 'clone habit' tap and hold option in Master Habits List
- Habit parameters preview on habit editing screen

### Changed
- Bumped minor version number due to schema changes

## [0.4.0] - 2016-09-01
### Added
- Priority to the Edit Habits screen
- 'Null Measure' flag for habits which don't have any associated measure
- Fixed startup in portrait orientation using Khertan's patch to thp's FremantleRotation
- Schema version history table, version will be inserted on database creation.
  Future versions with incompatible schema changes can use this to determine the
  version so as to know how to migrate to their newer schemas
- Timezone setting

### Changed
- Renamed habitjewel_utils.py to habitjewel_db.py
- Moved database creation code to habitjewel_db.py and took out most of my sample habits
- Changed frequency field/column to weekly quota/quota (easier to make sense of)
- Fixed module path include code
- Cleaned up unused code
- Bumped minor version number due to schema changes

## [0.3.0] - 2016-08-31
### Added
- Habits audit table (habits_a) to record changes to habit parameters

### Changed
- Fixed incorrect dependency on portrait.py for FremantleRotation
- Changed habit schedules to based on frequency (repetitions) per weekly cycle - no more
  daily or monthly habits, just habits with desired weekly frequencies
- Bumped minor version number due to schema changes

## [0.2.10] - 2016-08-30
### Added
- Function to generate context menus from dictionary (get_generated_hildon_context_menu() ),
  while still enabling hildon integration (unlike Gtk.UIManager)

### Changed
- Removed Gtk.UIManager setup
- Enhanced Master Habits List

## [0.2.9] - 2016-08-30
### Added
- Un/delete and Un/pause buttons on habit editing screen
- Package build script

## [0.2.8] - 2016-08-29
### Changed
- Improved redrawing of Master Habits List on screen orientation change
- Removed window stack, tried various ways to only handle rotation for visible window,
  but failed so reverted to blanket rotation.

## [0.2.7] - 2016-08-29
### Added
- Window stack list to track currently visible window to better handle rotation for windows
- Date utility functions

### Changed
- Use a copy of the habit dict when editing habit (and clean up on editing window destroy)

## [0.2.6] - 2016-08-28
### Added
- Un/delete and Un/pause options on habit editing screen

### Changed
- Fixed annoying repeating problem with inotify-wait in auto_deploy.sh script
- Removed unsed dependency on dateutil

## [0.2.5] - 2016-08-28
### Added
- Delete and Pause of habits via tap and hold on habit in day habits list
- Master Habits List view to see all habits (including deleted/paused)

## [0.2.4] - 2016-08-28
### Added
- Delete and Pause of habits via tap and hold on habit in day habits list
- Master Habits List view to see all habits (including deleted/paused)

## [0.2.3] - 2016-08-27
### Added
- Context popup menus which vary according to whether tap and hold on habit or checkbox

### Changed
- Code refactoring

## [0.2.2] - 2016-08-26
### Added
- Ability to set partial completion from habit context menu
- Icons for partial habit completion (20% increments)

### Changed
- Visual tweaks to other icons
- Day habits view sorts by completion status (completed habits sort to bottom)

## [0.2.1] - 2016-08-26
### Added
- Go To Date and Prev/Next Month buttons in calendar
- About page

### Changed
- Code clean-up
- Updates to build scripts

## [0.2.0] - 2016-08-25
### Added
- Habit editing page
- Main Menu "Go To Date" feature to jump to a date
- Goals (not exposed in UI yet - in database only)
- Scripts to auto-deploy code to N900 on change (auto_deploy.sh and auto_restart.sh)

### Changed
- Change from manual longpress detection (ugh!) to using widget.tap_and_hold_setup() 
- Code clean-up
- Updates to build scripts
- Use $HOME in local project path for portability between systems
- Removed points display from day habits list
- Moved view_date variable from global to MainWindow property
- Tweaked build scripts (Maemo Garage was rejecting)
- Bumped minor version number due to schema changes

## [0.1.3] - 2016-08-01
### Changed
- Fixed bug with pixmaps dir when running from /opt tree

## [0.1.2] - 2016-07-31
### Added
- Reworking display for Portrait orientation
- Screen orientation detection/change handling
- Graphical checkboxes which toggle (using CellRendererClickablePixbuf)

### Changed
- Disable changing completion status of habits in future

## [0.1.1] - 2016-07-31
### Added
- Some minimal functionality implemented
- Can set tasks completed

## [0.1.0] - 2016-07-29
### Added
- Initial commit - begin mutating Pyrecipe into Habit Jewel
