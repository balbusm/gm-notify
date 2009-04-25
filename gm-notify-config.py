#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify-config.py v0.7
# a simple and lightweight GMail-Notifier for ubuntu starting at 9.04 and preferable notify-osd
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
import gtk, pygtk, gconf
pygtk.require("2.0")
from threading import Thread
import urllib2
import gettext
import gmailatom, keyring

_ = gettext.translation('gm-notify', fallback=True).ugettext

class checkCreds(Thread):
    '''Thread which executes a GmailAtom.refreshInfo() to check if there are any errors
    regarding wrong credentials. Because this call can take some seconds it's threaded to
    keep the UI updating'''
    
    def __init__(self, user, passwd):
        Thread.__init__(self)
        self.user = user
        self.passwd = passwd
        self.result = -1
    
    def run(self):
        atom = gmailatom.GmailAtom(self.user, self.passwd)
        try:
            atom.refreshInfo()
            self.result = 0 # Everything fine
        except urllib2.HTTPError:
            self.result = 1 # Wrong creds
        except:
            self.result = -1 # Other Error - maybe no connection?

class gmnotifyConfig:
    def __init__(self):
        # Check if we already have some credentials to fill the input fields
        self.keys = keyring.Keyring("GMail", "mail.google.com", "http")
        if self.keys.has_credentials():
            creds = self.keys.get_credentials()
        else:
            creds = ("", "")
        
        # Init gconf get initial sound and checkinterval values
        self.client = gconf.client_get_default()
        if self.client.get_string("/apps/gm-notify/checkinterval"):
            checkinterval = float(self.client.get_string("/apps/gm-notify/checkinterval"))
        else:
            checkinterval = 90.0
        
        if self.client.get_string("/apps/gm-notify/soundfile"):
            sound = self.client.get_string("/apps/gm-notify/soundfile")
        else:
            sound = None
        
        ### UI Setup Part
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_border_width(5)
        self.window.set_title(_("GMail Notifier"))
        self.window.set_icon_name("evolution")
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
        
        vbox = gtk.VBox(False, 10)
        hbox_finalbuttons = gtk.HBox(False, 0)
        hbox_checkinterval = gtk.HBox(False, 0)
        table = gtk.Table(3,2)
        self.window.add(vbox)
        
        frame = gtk.Frame(_("Credentials"))
        frame.add(table)
        
        label_user = gtk.Label(_("Username:"))
        label_passwd = gtk.Label(_("Password:"))
        label_checkinterval = gtk.Label(_("Checkinterval:"))
        hsep = gtk.HSeparator()
        self.button_ok = gtk.Button(stock=gtk.STOCK_APPLY)
        self.button_close = gtk.Button(stock=gtk.STOCK_CLOSE)
        self.checkbutton_play = gtk.CheckButton(_("Play Sound on new Mail"))
        self.filechooser_play = gtk.FileChooserButton(_("Choose a soundfile"))
        self.label_status = gtk.Label(_("Please enter credentials"))
        self.input_user = gtk.Entry()
        self.input_passwd = gtk.Entry()
        check_adjustment = gtk.Adjustment(value=checkinterval, lower=20, upper=1000, step_incr=5, page_incr=60)
        self.spinbutton_checkinterval = gtk.SpinButton(check_adjustment)
        self.image_credok = gtk.Image()
        
        table.set_border_width(5)
        table.set_col_spacing(0, 5)
        table.set_row_spacing(0, 2)
        table.set_row_spacing(1, 5)
        if sound:
            self.checkbutton_play.set_active(True)
            self.filechooser_play.set_filename(sound)
        else:
            self.filechooser_play.set_sensitive(False)
        self.input_user.set_text(creds[0])
        self.input_passwd.set_text(creds[1])
        self.input_passwd.set_visibility(False)
        self.image_credok.set_from_icon_name("gtk-no", gtk.ICON_SIZE_MENU)
        
        label_user.show()
        label_passwd.show()
        label_checkinterval.show()
        hsep.show()
        self.button_ok.show()
        self.button_close.show()
        self.checkbutton_play.show()
        self.filechooser_play.show()
        self.label_status.show()
        self.input_user.show()
        self.input_passwd.show()
        self.spinbutton_checkinterval.show()
        self.image_credok.show()
        
        table.show()
        vbox.show()
        hbox_checkinterval.show()
        hbox_finalbuttons.show()
        frame.show()
        self.window.show()
        
        vbox.pack_start(frame, True, True)
        vbox.pack_start(self.checkbutton_play, True, True)
        vbox.pack_start(self.filechooser_play, True, True)
        vbox.pack_start(hsep, True, True)
        vbox.pack_start(hbox_checkinterval, True, True)
        vbox.pack_start(hbox_finalbuttons, True, True)
        hbox_checkinterval.pack_start(label_checkinterval, True, True)
        hbox_checkinterval.pack_start(self.spinbutton_checkinterval, True, True)
        hbox_finalbuttons.pack_start(self.button_ok, True, True)
        hbox_finalbuttons.pack_start(self.button_close, True, True)
        table.attach(label_user, 0, 1, 0, 1, xoptions=gtk.FILL)
        table.attach(label_passwd, 0, 1, 1, 2, xoptions=gtk.FILL)
        table.attach(self.input_user, 1, 2, 0, 1)
        table.attach(self.input_passwd, 1, 2, 1, 2)
        table.attach(self.image_credok, 0, 1, 2, 3)
        table.attach(self.label_status, 1, 2, 2, 3)
        
        # Perform check when user leaves password field
        self.window.connect("delete_event", gtk.main_quit)
        self.input_passwd.connect("focus_out_event", self.check_credentials)
        self.checkbutton_play.connect("toggled", self.toggle_filechooser)
        self.button_ok.connect("clicked", self.save)
        self.button_close.connect("clicked", gtk.main_quit)
        
        # Execute the check once to test the possible existing credentials
        self.check_credentials(None, None)
    
    def save(self, widget, data=None):
        '''saves the entered data and closes the app'''
        
        # Checkinterval
        self.client.add_dir("/apps/gm-notify", gconf.CLIENT_PRELOAD_NONE)
        self.client.set_string("/apps/gm-notify/checkinterval", str(self.spinbutton_checkinterval.get_value()))
        
        # Soundfile
        if self.checkbutton_play.get_active() and self.filechooser_play.get_filename():
            self.client.set_string("/apps/gm-notify/soundfile", self.filechooser_play.get_filename())
        else:
            self.client.set_string("/apps/gm-notify/soundfile", "")
        
        # Credentials
        self.keys.set_credentials((self.input_user.get_text(), self.input_passwd.get_text()))
        
        gtk.main_quit()
    
    def toggle_filechooser(self, widget, data=None):
        '''toggles active state of the filechooser on base of the checkbutton'''
        
        if self.checkbutton_play.get_active():
            self.filechooser_play.set_sensitive(True)
        else:
            self.filechooser_play.set_sensitive(False)
    
    def check_credentials(self, widget, event, data=None):
        '''check the given credentials if they are valid'''
        
        user = self.input_user.get_text()
        passwd = self.input_passwd.get_text()
        self.button_ok.set_sensitive(False)
        
        # Only check if user and password are present
        if len(user) > 0 and len(passwd) > 0:
            # Change status text and disable input fields
            self.image_credok.set_from_file("/usr/share/gm-notify/checking.gif")
            self.label_status.set_text(_("checking..."))
            self.input_user.set_sensitive(False)
            self.input_passwd.set_sensitive(False)
            
            # start Thread. While it's active update UI to display the nice gif animationgconf.client_get_default ()
            thread = checkCreds(user, passwd)
            thread.start()
            while thread.isAlive():
                if gtk.events_pending():
                    gtk.main_iteration()
            
            # Set the status according to the result of the check
            if thread.result == 0:
                self.image_credok.set_from_icon_name("gtk-yes", gtk.ICON_SIZE_MENU)
                self.label_status.set_text(_("OK"))
                self.button_ok.set_sensitive(True)
            elif thread.result == 1:
                self.image_credok.set_from_icon_name("gtk-no", gtk.ICON_SIZE_MENU)
                self.label_status.set_text(_("Wrong credentials"))
            else:
                self.image_credok.set_from_icon_name("gtk-no", gtk.ICON_SIZE_MENU)
                self.label_status.set_text(_("Error! Try again"))
            
            # Last but not least active the input fields
            self.input_user.set_sensitive(True)
            self.input_passwd.set_sensitive(True)
        else:
            self.image_credok.set_from_icon_name("gtk-no", gtk.ICON_SIZE_MENU)
            self.label_status.set_text(_("Please enter credentials"))
            
        return False

wine = gmnotifyConfig()
gtk.main()
