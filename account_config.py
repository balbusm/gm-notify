#!/usr/bin/env python
# -*- coding: utf-8 -*-
# account_config.py v0.10.3
# Provides settins to GMail notify
#
# Copyright (c) 2015, Mateusz Balbus <balbusm@gmail.com>
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
from __future__ import print_function

import os
import gettext

from gi.repository import Gio, Gtk
from twisted.words.protocols.jabber import jid

from gtalk import MailChecker

_ = gettext.translation('gm-notify', fallback=True).ugettext

class AccountConfig:
    def __init__(self, keys, client, creds):
        self.keys = keys
        self.client = client
        self.creds = creds
    
    def init_window(self, parent):
        if os.path.exists("gm-config.ui"):
            builder_file = "gm-config.ui"
        elif os.path.exists("/usr/local/share/gm-notify/gm-config.ui"):
            builder_file = "/usr/local/share/gm-notify/gm-config.ui"
        elif os.path.exists("/usr/share/gm-notify/gm-config.ui"):
            builder_file = "/usr/share/gm-notify/gm-config.ui"

        self.wTree = Gtk.Builder.new()
        self.wTree.add_from_file(builder_file)
        self.wTree.set_translation_domain("gm-notify")
        self.window = self.wTree.get_object("gmnotify_add_account")

        self.window.set_transient_for(parent)
        self.window.set_modal(True)
        self.window.set_destroy_with_parent(True)
        
        self.window.show_all()

        self.wTree.get_object("notebook_main").set_current_page(0)
        
        self.input_user = self.wTree.get_object("input_user")
        self.input_password = self.wTree.get_object("input_password")
        self.image_credentials = self.wTree.get_object("image_credentials")
        self.label_credentials = self.wTree.get_object("label_credentials")
        self.button_apply = self.wTree.get_object("button_apply")

        self.window.connect("delete_event", self.close)
        self.wTree.get_object("button_close").connect("clicked", self.close)
        self.button_apply.connect("clicked", self.apply)
        self.input_password.connect("focus-out-event", self.check_credentials)
        self.input_user.connect("focus-out-event", self.check_user)
        self.wTree.get_object("checkbutton_sound").connect("toggled", self.on_checkbutton_sound_toggled)

        #####
        # Init with stored values
        #####
        
        # Credentials

        self.input_user.set_text(self.creds.username)
        self.input_password.set_text(self.creds.password)
         
        self.api = MailChecker("", "", self.client)
        self.api.setOnAuthSucceeded(self.credentials_valid)
        self.api.setOnAuthFailed(self.credentials_invalid)
        self.api.setOnConnectionErrorCB(self.connection_error)
         
        self.check_credentials(None, None)
        
        # Sound
        self.wTree.get_object("checkbutton_sound").set_active(self.client.retrieve_sound_enabled())
        sound_file = self.client.retrieve_sound_file()
        if sound_file:
            self.wTree.get_object("fcbutton_sound").set_filename(sound_file)
        self.on_checkbutton_sound_toggled(self.wTree.get_object("checkbutton_sound"))
         
        # ClickAction
        if self.client.retrieve_use_mail_client():
            self.wTree.get_object("radiobutton_openclient").set_active(True)
        else:
            self.wTree.get_object("radiobutton_openweb").set_active(True)
         
        # Mailboxes
        self.wTree.get_object("checkbutton_inbox").set_active(self.client.retrieve_ignore_inbox())
        mailboxes = self.client.retrieve_mailboxes()
        self.wTree.get_object("entry_labels").set_text(", ".join(mailboxes))

        
        
        return self.window
    
    def close(self, widget = None, event = None):
        if self.api.is_running():
            self.api.die()
        self.window.close()
    
    def apply(self, widget):
        self.save()
        self.close()
    
    def save(self):
        '''saves the entered data and closes the app'''
        # Credentials
        self.keys.delete_credentials(self.creds.username)
        user = self.input_user.get_text()
        self.keys.set_credentials(user,
                                  self.input_password.get_text())
        
        # Mailboxes
        mailboxes = []
        for label in self.wTree.get_object("entry_labels").get_text().split(","):
            mailboxes.append(label.strip())
        self.client.save_mailboxes(mailboxes)
        self.client.save_ignore_inbox(self.wTree.get_object("checkbutton_inbox").get_active())
        
        # ClickAction
        self.client.save_use_mail_client(self.wTree.get_object("radiobutton_openclient").get_active())

        # Soundfile
        if self.wTree.get_object("checkbutton_sound").get_active() and self.wTree.get_object("fcbutton_sound").get_filename():
            self.client.save_sound_enabled(True)
            self.client.save_sound_file(str(self.wTree.get_object("fcbutton_sound").get_filename()))
        else:
            self.client.save_sound_enabled(False)

    def on_checkbutton_sound_toggled(self, widget):
        self.wTree.get_object("fcbutton_sound").set_sensitive(self.wTree.get_object("checkbutton_sound").get_active())
    
    def check_user(self, widget, event):
        user = self.input_user.get_text()
        if not has_mail_postfix(user):
            self.input_user.set_text(user + "@gmail.com")
    
    def has_mail_postfix(self, user):
        return len(user) == 0 or "@" in user
    
    def check_credentials(self, widget, event, data=None):
        '''check if the given credentials are valid'''
        
        self.button_apply.set_sensitive(False)
        
        # Change status text and disable input fields
        if self.input_user.get_text() and self.input_password.get_text():
            self.image_credentials.set_from_file("/usr/share/gm-notify/checking.gif")
            self.label_credentials.set_text(_("checking..."))
            self.input_user.set_sensitive(False)
            self.input_password.set_sensitive(False)
            
            self.api.jid = jid.JID(self.input_user.get_text())
            self.api.password = self.input_password.get_text()
            self.api.connect()
        return False
    
    def credentials_valid(self):
        self.on_credentials_checked("gtk-yes", "Valid credentials", True)

    def credentials_invalid(self):
        self.on_credentials_checked("gtk-stop", "Invalid credentials")
        
    def connection_error(self, reason):
        self.on_credentials_checked("gtk-stop", "Connection error")
        
    def on_credentials_checked(self, icon_name, text, valid = False):
        self.image_credentials.set_from_icon_name(icon_name, Gtk.IconSize.MENU)
        self.label_credentials.set_text(_(text))
        self.input_user.set_sensitive(True)
        self.input_password.set_sensitive(True)
        self.button_apply.set_sensitive(valid)

        self.api.die()
        