#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify-config.py v0.10.1
# GMail Notifier Configuration Utility
#
# Copyright (c) 2009-2010, Alexander Hungenberg <alexander.hungenberg@gmail.com>
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
import sys
import os
import gettext
import subprocess
import shutil

import pynotify
import pygtk
pygtk.require("2.0")
import gtk, gtk.glade
import gconf
from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from twisted.words.protocols.jabber import jid

import keyring
from gtalk import MailChecker

_ = gettext.translation('gm-notify', fallback=True).ugettext
if not pynotify.init(_("GMail Notifier")):
    sys.exit(-1)

class PathNotFound(Exception): pass

def get_executable_path(name):
    path = "%s/%s" % (os.getcwd(), name)
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/local/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    raise PathNotFound("%s not found" % name)

class Window:
    def __init__(self):
        #####
        # GUI initialization
        #####
        self.keys = keyring.Keyring("GMail", "mail.google.com", "http")
        self.client = gconf.client_get_default()
        
        if os.path.exists("gm-config.glade"):
            glade_file = "gm-config.glade"
        elif os.path.exists("/usr/local/share/gm-notify/gm-config.glade"):
            glade_file = "/usr/local/share/gm-notify/gm-config.glade"
        elif os.path.exists("/usr/share/gm-notify/gm-config.glade"):
            glade_file = "/usr/share/gm-notify/gm-config.glade"

        self.wTree = gtk.glade.XML(glade_file, "gmnotify_config_main", "gm-notify")
        self.window = self.wTree.get_widget("gmnotify_config_main")
        self.window.show_all()
        
        #####
        # Init with stored values
        #####
        
        # Credentials
        if self.keys.has_credentials():
            self.creds = self.keys.get_credentials()
        else:
            self.creds = ("", "")
        self.wTree.get_widget("input_user").set_text(self.creds[0])
        self.wTree.get_widget("input_password").set_text(self.creds[1])
        
        self.api = MailChecker("", "")
        self.api.cb_auth_successful = self.credentials_valid
        self.api.cb_auth_failed = self.credentials_invalid
        
        self.check_credentials(None, None)
        
        # Sound
        self.wTree.get_widget("checkbutton_sound").set_active(self.client.get_bool("/apps/gm-notify/play_sound"))
        if self.client.get_string("/apps/gm-notify/soundfile"):
            self.wTree.get_widget("fcbutton_sound").set_filename(self.client.get_string("/apps/gm-notify/soundfile"))
        self.on_checkbutton_sound_toggled(self.wTree.get_widget("checkbutton_sound"))
        
        # ClickAction
        if self.client.get_bool("/apps/gm-notify/openclient"):
            self.wTree.get_widget("radiobutton_openclient").set_active(True)
        else:
            self.wTree.get_widget("radiobutton_openweb").set_active(True)
        
        # Mailboxes
        mailboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
        self.wTree.get_widget("entry_labels").set_text(", ".join(mailboxes))

        # Autorun
        if os.path.exists("data/gm-notify.desktop"):
            self.gm_notify_autostart_file = "data/gm-notify.desktop"
        elif os.path.exists("/usr/local/share/applications/gm-notify.desktop"):
            self.gm_notify_autostart_file = "/usr/local/share/applications/gm-notify.desktop"
        elif os.path.exists("/usr/share/applications/gm-notify.desktop"):
            self.gm_notify_autostart_file = "/usr/share/applications/gm-notify.desktop"
        self.autostart_file = os.path.expanduser("~/.config/autostart/gm-notify.desktop")
        self.wTree.get_widget("checkbutton_autostart").set_active(os.path.exists(self.autostart_file))
        
        signals = { "gtk_main_quit": self.terminate,
                    "on_button_apply_clicked": self.save,
                    "on_input_password_focus_out_event": self.check_credentials,
                    "on_checkbutton_sound_toggled": self.on_checkbutton_sound_toggled,
        }
        self.wTree.signal_autoconnect(signals)
    
    def save(self, widget, data=None):
        '''saves the entered data and closes the app'''
        
        self.client.add_dir("/apps/gm-notify", gconf.CLIENT_PRELOAD_NONE)
        
        # Credentials
        self.keys.delete_credentials()
        self.keys.set_credentials(( self.wTree.get_widget("input_user").get_text(), 
                                    self.wTree.get_widget("input_password").get_text()))
        
        # Mailboxes
        mailboxes = []
        for label in self.wTree.get_widget("entry_labels").get_text().split(","):
            mailboxes.append(label.strip())
        self.client.set_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING, mailboxes)
        
        # ClickAction
        self.client.set_bool("/apps/gm-notify/openclient", self.wTree.get_widget("radiobutton_openclient").get_active())

        # Soundfile
        if self.wTree.get_widget("checkbutton_sound").get_active() and self.wTree.get_widget("fcbutton_sound").get_filename():
            self.client.set_bool("/apps/gm-notify/play_sound", True)
            self.client.set_string("/apps/gm-notify/soundfile", str(self.wTree.get_widget("fcbutton_sound").get_filename()))
        else:
            self.client.set_bool("/apps/gm-notify/play_sound", False)

        # Autorun
        if self.wTree.get_widget("checkbutton_autostart").get_active():
            if not os.path.exists(self.autostart_file):
                try:
                    os.makedirs(os.path.expanduser("~/.config/autostart"))
                except OSError:
                    pass

                try:
                    shutil.copyfile(self.gm_notify_autostart_file, self.autostart_file)
                    os.chmod(self.autostart_file, 0700)
                except IOError:
                    print "Warning: cannot write to path", self.autostart_file
        else:
            if os.path.exists(self.autostart_file):
                try:
                    os.unlink(self.autostart_file)
                except:
                    print "Warning: cannot delete", self.autostart_file

        # Start gm-notify itself
        subprocess.Popen(get_executable_path("gm-notify.py"))
    
    def terminate(self, widget):
        reactor.stop()
    
    def on_checkbutton_sound_toggled(self, widget):
        self.wTree.get_widget("fcbutton_sound").set_sensitive(self.wTree.get_widget("checkbutton_sound").get_active())
    
    def check_credentials(self, widget, event, data=None):
        '''check if the given credentials are valid'''
        
        input_user = self.wTree.get_widget("input_user")
        input_password = self.wTree.get_widget("input_password")
        image_credentials = self.wTree.get_widget("image_credentials")
        label_credentials = self.wTree.get_widget("label_credentials")
        button_apply = self.wTree.get_widget("button_apply")
        button_apply.set_sensitive(False)
        
        # Change status text and disable input fields
        if input_user.get_text() and input_password.get_text():
            image_credentials.set_from_file("/usr/share/gm-notify/checking.gif")
            label_credentials.set_text(_("checking..."))
            input_user.set_sensitive(False)
            input_password.set_sensitive(False)
            
            self.api.jid = jid.JID(input_user.get_text())
            self.api.password = input_password.get_text()
            self.api.connect()
        return False
    
    def credentials_valid(self):
        input_user = self.wTree.get_widget("input_user")
        input_password = self.wTree.get_widget("input_password")
        image_credentials = self.wTree.get_widget("image_credentials")
        label_credentials = self.wTree.get_widget("label_credentials")
        button_apply = self.wTree.get_widget("button_apply")
        
        image_credentials.set_from_icon_name("gtk-yes", gtk.ICON_SIZE_MENU)
        label_credentials.set_text(_("Valid credentials"))
        button_apply.set_sensitive(True)
        input_user.set_sensitive(True)
        input_password.set_sensitive(True)
        
        self.api.die()
    
    def credentials_invalid(self):
        input_user = self.wTree.get_widget("input_user")
        input_password = self.wTree.get_widget("input_password")
        image_credentials = self.wTree.get_widget("image_credentials")
        label_credentials = self.wTree.get_widget("label_credentials")
        
        image_credentials.set_from_icon_name("gtk-stop", gtk.ICON_SIZE_MENU)
        label_credentials.set_text(_("Invalid credentials"))
        input_user.set_sensitive(True)
        input_password.set_sensitive(True)
        
        self.api.die()

t = Window()
reactor.run()
