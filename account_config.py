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

import os
import gettext

from gi.repository import GLib, Gtk

from imap_mail_checker import ImapMailChecker
import account_settings_provider

_ = gettext.translation('gm-notify', fallback=True).gettext


class AccountConfig:
    def __init__(self, keys, creds):
        self.keys = keys
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
        
        #self.label_credentials = self.wTree.get_object("label_credentials")
        
        #self.image_credentials = self.wTree.get_object("image_credentials")
        self.button_apply = self.wTree.get_object("button_apply")

        self.window.connect("delete_event", self.close)
        self.wTree.get_object("button_close").connect("clicked", self.close)
        self.button_apply.connect("clicked", self.apply)
        self.wTree.get_object("checkbutton_sound").connect("toggled", self.on_checkbutton_sound_toggled)

        #####
        # Init with stored values
        #####
        
        # Credentials

        settings_provider = account_settings_provider.create_settings_provider(self.creds.username)

        if self.creds.username:
            self.input_user.set_text(self.creds.username)
            self.input_user.set_sensitive(False)
            
        
        self.messagedialog = None
        self.api = self.setupApi()

        # Sound
        self.wTree.get_object("checkbutton_sound").set_active(settings_provider.retrieve_sound_enabled())
        sound_file = settings_provider.retrieve_sound_file()
        if sound_file:
            self.wTree.get_object("fcbutton_sound").set_filename(sound_file)
        self.on_checkbutton_sound_toggled(self.wTree.get_object("checkbutton_sound"))
         
        # ClickAction
        if settings_provider.retrieve_use_mail_client():
            self.wTree.get_object("radiobutton_openclient").set_active(True)
        else:
            self.wTree.get_object("radiobutton_openweb").set_active(True)
         
        # Mailboxes
        self.wTree.get_object("checkbutton_inbox").set_active(settings_provider.retrieve_ignore_inbox())
        labels = settings_provider.retrieve_labels()
        self.wTree.get_object("entry_labels").set_text(", ".join(labels))

        return self.window
    
    def setupApi(self, login = None):
        api = ImapMailChecker(login)
        api.set_on_auth_succeeded(self.credentials_valid)
        api.set_on_auth_failed(self.credentials_invalid)
        api.set_on_connection_error_cb(self.connection_error)
        return api
    
    def close(self, widget = None, event = None):
        if self.api.is_running():
            self.api.stop()
        self.window.close()
        

    def message_cb(self, action, text, buttons = Gtk.ButtonsType.OK_CANCEL):
        # a Gtk.MessageDialog
        messagedialog = Gtk.MessageDialog(parent=self.window,
                                          flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.WARNING,
                                          buttons=buttons,
                                          message_format=_(text))
        # connect the response (of the button clicked) to the function
        # dialog_response()
        dialog_action = lambda widget, response_id: self.dialog_close(action, widget, response_id)
        messagedialog.connect("response", dialog_action)
        # show the messagedialog
        messagedialog.show()
        return messagedialog
    
    def dialog_close(self, action, widget, response_id):
        if action is not None:
            action(widget, response_id)
        widget.close()
    
    def apply(self, widget):
        self.check_user()
        if not self.check_credentials():
            self.message_cb(None, "Provide email account", Gtk.ButtonsType.OK)
    
    def save(self):
        '''saves the entered data and closes the app'''
        user = self.input_user.get_text()

        
        settings_provider = account_settings_provider.create_settings_provider(user)
        # Mailboxes
        labels = []
        for label in self.wTree.get_object("entry_labels").get_text().split(","):
            labels.append(label.strip())
        settings_provider.save_labels(labels)
        settings_provider.save_ignore_inbox(self.wTree.get_object("checkbutton_inbox").get_active())
        
        # ClickAction
        settings_provider.save_use_mail_client(self.wTree.get_object("radiobutton_openclient").get_active())
        
        # Port
        settings_provider.save_preferred_port(settings_provider.retrieve_preferred_port())
        
        # Soundfile
        if self.wTree.get_object("checkbutton_sound").get_active() and self.wTree.get_object("fcbutton_sound").get_filename():
            settings_provider.save_sound_enabled(True)
            settings_provider.save_sound_file(str(self.wTree.get_object("fcbutton_sound").get_filename()))
        else:
            settings_provider.save_sound_enabled(False)

    def on_checkbutton_sound_toggled(self, widget):
        self.wTree.get_object("fcbutton_sound").set_sensitive(self.wTree.get_object("checkbutton_sound").get_active())
    
    def check_user(self):
        user = self.input_user.get_text()
        if not self.has_mail_postfix(user):
            self.input_user.set_text(user + "@gmail.com")
    
    def has_mail_postfix(self, user):
        return len(user) == 0 or "@" in user
    
    def check_credentials(self, event=None):
        '''check if the given credentials are valid'''
        # Change status text and disable input fields
        if self.input_user.get_text():
            self.messagedialog = self.message_cb(self.on_check_credentials_cancel, "Please verify your account on Google page", Gtk.ButtonsType.CANCEL)
            image = Gtk.Image()
            image.set_from_file("/usr/share/gm-notify/checking.gif")
            image.show()
            self.messagedialog.set_image(image)
            self.api = self.setupApi(self.input_user.get_text())
            self.api.connect()
            return True
        return False
        
    def on_check_credentials_cancel(self, widget, response_id):
        if response_id == Gtk.ResponseType.CANCEL:
            widget.close()
            self.api.stop()
    
    def credentials_valid(self, username):
        self.on_credentials_checked("gtk-yes", "Valid credentials", True)

    def credentials_invalid(self, username, reason):
        self.on_credentials_checked("gtk-stop", "Invalid credentials")
        
    def connection_error(self, username, reason):
        self.on_credentials_checked("gtk-stop", "Connection error")
        
    def on_credentials_checked(self, icon_name, text, valid = False):
        if self.messagedialog is not None:
            self.messagedialog.close()
            self.messagedialog = None
#         self.image_credentials.set_from_icon_name(icon_name, Gtk.IconSize.MENU)
#         self.label_credentials.set_label(_(text))
#         self.button_validate.set_sensitive(True)
        editing = bool(self.creds.username)
        self.input_user.set_sensitive(not editing)
        self.api.stop()
        
        if not editing and valid:
            self.check_account_already_saved()
            
    def check_account_already_saved(self):    
        # Doesn't work since account has been just added in OAuth2 Get token
        if self.keys.has_credentials(self.input_user.get_text()):
            self.message_cb(self.should_override, "Account already exists. Override?", Gtk.ButtonsType.YES_NO)
        else: self.save()
        
    def should_override(self, widget, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.save()
        
        