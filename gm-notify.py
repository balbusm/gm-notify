#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify.py v0.8
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
import os
import sys
import subprocess
import gettext

import pynotify
import indicate
import urllib2
import gtk, gobject
import pygst
pygst.require("0.10")
import gst
import gconf

from gmimap import GMail
import keyring
import gmxdgsoundlib as soundlib

_ = gettext.translation('gm-notify', fallback=True).ugettext

class CheckMail():
    def __init__(self):
        '''initiates DBUS-Messaging interface, creates the feedreader and registers with indicator-applet.
        In the end it starts the periodic check timer and a gtk main-loop'''
        
        # Initiate pynotify and Feedreader with Gnome-Keyring Credentials
        if not pynotify.init(_("GMail Notifier")):
            sys.exit(-1)
        
        keys = keyring.Keyring("GMail", "mail.google.com", "http")
        if keys.has_credentials():
            creds = keys.get_credentials()
        else:
            # Start gm-notify-config if no credentials are found
            if os.path.exists("./gm-notify-config.py"):
                gm_config_path = "./gm-notify-config.py"
            elif os.path.exists("/usr/local/bin/gm-notify-config.py"):
                gm_config_path = "/usr/local/bin/gm-notify-config.py"
            elif os.path.exists("/usr/bin/gm-notify-config.py"):
                gm_config_path = "/usr/bin/gm-notify-config.py"

            subprocess.call(gm_config_path)
            sys.exit(-1)
        
        # check if we use Google Apps to start the correct webinterface
        gmail_domains = ['gmail.com','googlemail.com']
        try:
            self.domain = self.creds[0].split('@')[1]
            if self.domain in gmail_domains:
                self.domain = None
        except:
            self.domain = None
        
        # init gconf to read config values
        self.client = gconf.client_get_default()
        if self.client.get_string("/apps/gm-notify/checkinterval"):
            checkinterval = int(float(self.client.get_string("/apps/gm-notify/checkinterval")))
        else:
            checkinterval = 90
        
        # init sound
        soundfile = soundlib.findsoundfile(self.client.get_string("/desktop/gnome/sound/theme_name"))
        if self.client.get_bool("/apps/gm-notify/play_sound"):
            if soundfile:
                self.player = gst.element_factory_make("playbin", "player")
                self.player.set_property("video-sink", gst.element_factory_make("fakesink", "fakesink"))
                self.player.set_property("uri", "file://" + soundfile)
                bus = self.player.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self.gst_message)
            else:
                self.showNotification(_("No sound selected"), _("Please select a new-message sound in the audio settings or unselect the corresponding option."))
                sys.exit(-1)
        else:
            self.player = None
        
        # Register with Indicator-Applet
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.mail")
        self.server.set_desktop_file("/usr/share/applications/gm-notify.desktop")
        self.server.connect("server-display", self.serverClick)
        self.indicators = []
        
        # Create one indicator and instantly delete it to make the server show up in the applet (HACK?)
        self.addIndicator("dummy")
        self.indicators = []
        
        # Check every <checkinterval> seconds
        self.mailboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
        self.oldmail = []
        self.gmapi = GMail(*creds)
        self.checkmail()
        
        gobject.timeout_add_seconds(checkinterval, self.checkmail)
        gtk.main()
    
    def gst_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif message.type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            print "Error: %s - %s" % message.parse_error()
    
    def serverClick(self, server):
        '''called when the server is clicked in the indicator-applet to open the gmail account'''
        if self.domain:
            url = "https://mail.google.com/a/"+self.domain+"/"
        else:
            url = "https://mail.google.com/mail/"
        subprocess.Popen("xdg-open "+url, shell=True)

    
    def filterNewMail(self, imapserver, inbox):
        '''returns the ids of new mails since last check in a list'''
        
        imapserver.select(inbox)
        msgids = imapserver.search(None, "(UNSEEN)")[1][0].split(" ")
        if not len(msgids[0]) > 0:
            msgids = []
        
        # store msgids of messages we already notified about in self.oldmail
        new = []
        for msgid in msgids:
            if not msgid in self.oldmail:
                new.append(msgid)
        
        # regenerate the oldmail-list with all mails we processed yet
        # and because we already processed all mails this is equivalent to the 
        # ones that are yet unread
        self.indicators = []
        self.oldmail = []
        for msgid in msgids:
            self.addIndicator("nothing yet")
            self.oldmail.append(msgid)
        
        return new
    
    def checkmail(self):
        '''calls getnewmail() to retrieve new mails and presents them via
        libnotify (notify-osd) to the user. Returns True for gobject.add_timeout()'''
        
        # Connect to IMAP - No check for valid credentials. When they edit them manually
        # it's their fault ;-)
        self.gmapi.connect().addCallback(self._connected)
    
    def displaymail(self, newmail):
        # FIXME
        # aggregate the titles of the messages... cut the string if longer than 20 chars
        titles = ""
        newmail = self.filterNewMail(imapserver, "INBOX")
        for msgid in newmail:
            title = imapserver.fetch(msgid, "(BODY[HEADER.FIELDS (SUBJECT)])")[1][0][1].strip(" \r\n")[9:]
            if len(title) > 20:
                title = title[0:20] + "..."
            if len(title) == 0:
                title = _("(no subject)")
            
            if len(titles) == 0:
                titles = title
            else:
                titles += "\n- " + title
        
        # Disconnect
        imapserver.close()
        imapserver.logout()
        
        # play a sound?
        if len(newmail) > 0 and self.player:
            self.player.set_state(gst.STATE_PLAYING)
        
        # create notifications and play sound
        if not "\n" in titles and not titles == "":
            self.showNotification(_("Incoming message"), titles)
        elif "\n" in titles:
            self.showNotification(str(len(newmail)) + " " + _("new messages"), "- " + titles)
    
        return True
    
    def showNotification(self, title, message):
        '''takes a title and a message to display the email notification. Returns the
        created notification object'''
        
        n = pynotify.Notification(title, message, "notification-message-email")
        n.show()
        
        return n
    
    def addIndicator(self, msg):
        '''adds a indicator to the indicator-applet which results in the "unread counter"
        increased by one. The indicator is stored in a class-list to keep the reference.
        If you delete this the indicator will be removed from the applet, too'''
        
        new_indicator = indicate.IndicatorMessage()
        new_indicator.set_property("subtype", "mail")
        new_indicator.set_property("sender", msg)
        new_indicator.show()
        self.indicators.append(new_indicator)
    
    def _connected(self, protocol):
        self.gmapi.login().addCallback(self._logged_in)
    
    def _logged_in(self, result):
        print result

cm = CheckMail()
