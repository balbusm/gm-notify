#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify-config.py v0.9
# GMail Notifier Configuration Utility
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
import sys
import os
import gettext
import subprocess

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
#        self.wTree.get_widget("checkbutton_sound").set_active(self.client.get_bool("/apps/gm-notify/play_sound"))
#        self.on_checkbutton_sound_toggled(self.wTree.get_widget("checkbutton_sound"))
        
        # ClickAction
        if self.client.get_bool("/apps/gm-notify/openclient"):
            self.wTree.get_widget("radiobutton_openclient").set_active(True)
        else:
            self.wTree.get_widget("radiobutton_openweb").set_active(True)
        
        # Inboxes
#        inboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
#        if inboxes:
#            self.wTree.get_widget("checkbutton_inbox").set_active("INBOX" in inboxes)
#            self.wTree.get_widget("checkbutton_allmail").set_active("[Google Mail]/All Mail" in inboxes)
#            self.wTree.get_widget("checkbutton_starred").set_active("[Google Mail]/Starred" in inboxes)
#        else:
#            self.wTree.get_widget("checkbutton_inbox").set_active(True)
        
        signals = { "gtk_main_quit": self.terminate,
                    "on_button_apply_clicked": self.save,
                    "on_input_password_focus_out_event": self.check_credentials,
#                    "on_button_sound_clicked": self.on_button_sound_clicked,
#                    "on_checkbutton_sound_toggled": self.on_checkbutton_sound_toggled,
#                    "on_radiobutton_checkcustom_toggled": self.on_radiobutton_checkcustom_toggled
        }
        self.wTree.signal_autoconnect(signals)
    
    def save(self, widget, data=None):
        '''saves the entered data and closes the app'''
        
        self.client.add_dir("/apps/gm-notify", gconf.CLIENT_PRELOAD_NONE)
        
        # Credentials
        self.keys.delete_credentials()
        self.keys.set_credentials(( self.wTree.get_widget("input_user").get_text(), 
                                    self.wTree.get_widget("input_password").get_text()))
        
        # Inboxes
        inboxes = []
        for child in self.wTree.get_widget("vbox_expanderlabels").get_children():
            if child.get_active():
                inboxes.append(child.get_label())
        self.client.set_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING, inboxes)
        
        # ClickAction
        self.client.set_bool("/apps/gm-notify/openclient", self.wTree.get_widget("radiobutton_openclient").get_active())

        # Soundfile
#        if self.wTree.get_widget("checkbutton_sound").get_active():
#            if soundlib.findsoundfile(self.client.get_string("/desktop/gnome/sound/theme_name")):
#                self.client.set_bool("/apps/gm-notify/play_sound", True)
#                reactor.stop()
#            else:
#                pynotify.Notification(_("No sound selected"), _("Please select a new-message sound in the audio settings or unselect the corresponding option."), "notification-message-email").show()
#        else:
#            self.client.set_bool("/apps/gm-notify/play_sound", False)
#            reactor.stop()

        # Start gm-notify itself
        if os.path.exists("./gm-notify.py"):
            gm_path = "./gm-notify.py"
        elif os.path.exists("/usr/local/bin/gm-notify.py"):
            gm_path = "/usr/local/bin/gm-notify.py"
        elif os.path.exists("/usr/bin/gm-notify.py"):
            gm_path = "/usr/bin/gm-notify.py"
        subprocess.call("killall gm-notify.py", shell=True)
        subprocess.Popen(gm_path)
    
    def terminate(self, widget):
        reactor.stop()
        
#    def on_checkbutton_sound_toggled(self, widget, data=None):
#        button = self.wTree.get_widget("button_sound")
#        if widget.get_active():
#            button.set_sensitive(True)
#        else:
#            button.set_sensitive(False)
#    
#    def on_button_sound_clicked(self, widget, data=None):
#        self.window.set_sensitive(False)
#        while gtk.events_pending():
#            gtk.main_iteration()
#        subprocess.call("gnome-sound-properties", shell=True)
#        self.window.set_sensitive(True)
    
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
    
    def fillLabels(self, labels):
        expander_labels = self.wTree.get_widget("expander_labels")
        vbox_expanderlabels = self.wTree.get_widget("vbox_expanderlabels")
        inboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
        
        for child in vbox_expanderlabels.get_children():
            vbox_expanderlabels.remove(child)
        
        expander_labels.set_sensitive(True)
        
        for label in labels:
            checkbutton = gtk.CheckButton(label=label)
            checkbutton.set_active(label in inboxes)
            vbox_expanderlabels.pack_start(checkbutton, expand=False)
        vbox_expanderlabels.show_all()
    
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
        expander_labels = self.wTree.get_widget("expander_labels")
        vbox_expanderlabels = self.wTree.get_widget("vbox_expanderlabels")
        
        image_credentials.set_from_icon_name("gtk-stop", gtk.ICON_SIZE_MENU)
        label_credentials.set_text(_("Invalid credentials"))
        expander_labels.set_sensitive(False)
        input_user.set_sensitive(True)
        input_password.set_sensitive(True)
        
        for child in vbox_expanderlabels.get_children():
            vbox_expanderlabels.remove(child)
        
        self.api.die()

t = Window()
reactor.run()
