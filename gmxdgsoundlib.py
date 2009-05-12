#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gmxdgsoundlib.py v0.9
# simple lib to access the xdg-sound-theme specification and retrieve the message-new-email sound.
#
# Copyright (c) 2009, Alexander Hungenberg <alexander.hungenberg@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

### The currently selected soundtheme is stored in gconf at /desktop/gnome/sound/theme_name
### call findsoundfile(themename) to get the path
import os

def findthemedir(name):
    '''reads environment variables and trys to find a suitable directory for a given
    soundtheme name'''
    
    if "XDG_DATA_DIRS" in os.environ:
        dirs = os.environ["XDG_DATA_DIRS"].split(":")
    else:
        dirs = []
    dirs.append(os.environ["HOME"] + "/.local/share/")
    
    for directory in dirs:
        directory += "sounds/" + name + "/"
        if os.access(directory, os.F_OK):
            return directory
    
    return None

def readthemefile(path):
    '''reads given soundtheme file and extracts parent theme and soundfile directories'''
    
    inherits = None
    directories = "."
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("Inherits="):
                inherits = line.split("=")[1]
            if line.startswith("Directories="):
                # So far we simply choose the first directory - don't know how to choose
                directories = line.split("=")[1].split(",")[0]
    
    return (inherits, directories)

def findsearchdirectories(soundtheme):
    '''finds all search directories - of the given soundtheme and it's parents'''
    
    directories = []
    sounddir = findthemedir(soundtheme)
    while sounddir:
        (inherits, themedirs) = readthemefile(sounddir + "index.theme")
        directories.append(sounddir + themedirs + "/")
        if inherits:
            # set sounddir to the one of the parent theme
            sounddir = findthemedir(inherits)
        else:
            break
    
    # add final freedesktop theme according to the specification
    if findthemedir("freedesktop"):
        directories.append(readthemefile(findthemedir("freedesktop") + "index.theme")[1])
    return directories

def findsoundfile(soundtheme):
    '''Uses findsearchdirectories to find all dirs of the soundtheme, skips through them
    and searches a file starting with "message-new-email" according to the specs. If it
    finds one, the full path is returned'''
    
    directories = findsearchdirectories(soundtheme)
    for onedir in directories:
        for onefile in os.listdir(onedir):
            if onefile.startswith("message-new-email"):
                if onefile == "message-new-email.disabled":
                    return None
                else:
                    return onedir + onefile
    
    return None
