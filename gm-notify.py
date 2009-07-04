#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify.py v0.9
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
import gobject
import pygst
pygst.require("0.10")
import gst
import gconf
from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from email.Header import decode_header


from gmimap import GMail
import keyring
import gmxdgsoundlib as soundlib

_ = gettext.translation('gm-notify', fallback=True).ugettext

class CheckMail():
    def __init__(self):
        '''initiates DBUS-Messaging interface, creates the feedreader and registers with indicator-applet.
        In the end it starts the periodic check timer and a gtk main-loop'''
        
        # Initiate pynotify and Gnome Keyring
        if not pynotify.init(_("GMail Notifier")):
            sys.exit(-1)
        
        keys = keyring.Keyring("GMail", "mail.google.com", "http")
        if keys.has_credentials():
            self.creds = keys.get_credentials()
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
        
        # Retrieve some options and already received mailcount
        self.mailboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
        self.oldmail = {}
        oldlist = self.client.get_list("/apps/gm-notify/oldmail", gconf.VALUE_STRING)
        for old in oldlist:
            old = old.split("!%)")
            self.oldmail[old[0]] = int(old[1])
        
        # Check every xx seconds
        self.checkmail()
        gobject.timeout_add_seconds(checkinterval, self.checkmail)
        reactor.run()
    
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
        self.indicators = []
        if self.client.get_bool("/apps/gm-notify/openclient"):
            command = self.client.get_string("/desktop/gnome/url-handlers/mailto/command").split(" ")[0]
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen("xdg-open "+url, shell=True)
    
    def checkmail(self):
        '''calls getnewmail() to retrieve new mails and presents them via
        libnotify (notify-osd) to the user. Returns True for gobject.add_timeout()'''
        
        # Connect to IMAP - No check for valid credentials. When they edit them manually
        # it's their fault ;-)
        self.playedsound = False
        for mailbox in self.mailboxes:
            gmapi = GMail(*self.creds)
            gmapi.connect().addCallback(self._connected, gmapi, mailbox)
        
        return True
    
    def displaymail(self, newmail, mailbox):
        '''Takes mailbox name and titles of mails, to display notification and add indicators'''
        
        # Mailbox Names:
        mailboxes = {   "INBOX": _("Inbox"),
                        "[Google Mail]/All Mail": _("All Mail"),
                        "[Google Mail]/Starred": _("Starred") }
        
        # aggregate the titles of the messages... cut the string if longer than 20 chars
        titles = ""
        for title in newmail:
            for header, encoding in decode_header(title):
                if encoding is not None:
                    title = header.decode(encoding)
                else:
                    title = header.decode()


            self.addIndicator(title)
            if len(title) > 20:
                title = title[0:20] + "..."
            if len(title) == 0:
                title = _("(no subject)")
            
            if len(titles) == 0:
                titles = title
            else:
                titles += "\n- " + title
        
        # play a sound?
        if len(newmail) > 0 and self.player and not self.playedsound:
            self.player.set_state(gst.STATE_PLAYING)
            self.playedsound = True
        
        # create notifications and play sound
        if mailbox in mailboxes:
            mbox = _("in") + " " + mailboxes[mailbox] + ":\n\n"
        else:
            mbox = _("in label") + " " + mailbox + ":\n\n"
            
        if not "\n" in titles and not titles == "":
            self.showNotification(_("Incoming message"), mbox + titles)
        elif "\n" in titles:
            self.showNotification(str(len(newmail)) + " " + _("new messages"), mbox + "- " + titles)
    
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
    
    def saveoldmails(self):
        '''Save displayed mail count to gconf'''
        
        oldlist = []
        for oldmail in self.oldmail.iteritems():
            oldlist.append("!%)".join([str(e) for e in oldmail]))
        
        self.client.set_list("/apps/gm-notify/oldmail", gconf.VALUE_STRING, oldlist)
    
    def _connected(self, protocol, gmapi, mailbox):
        '''We entered connected state, need to authenticate now'''
        
        gmapi.protocol.login().addCallback(self._logged_in, gmapi, mailbox)
    
    def _logged_in(self, result, gmapi, mailbox):
        '''We are logged in. Examine the given mailbox'''
        
        gmapi.protocol.examine(mailbox).addCallback(self._selected_mailbox, gmapi, mailbox)
    
    def _selected_mailbox(self, result, gmapi, mailbox):
        '''mailbox selected. Ready to fetch new mails'''
        
        if not mailbox in self.oldmail:
            self.oldmail[mailbox] = 0
        if result['EXISTS'] > self.oldmail[mailbox]:
            gmapi.getSubjects(self.oldmail[mailbox] + 1).addCallback(self._got_subjects, gmapi, mailbox)
        else:
            gmapi.protocol.logout()
            gmapi.protocol = None
            
        self.oldmail[mailbox] = result['EXISTS']
        self.saveoldmails()
    
    def _got_subjects(self, result, gmapi, mailbox):
        '''got new subjects. Close connection and pass them to displaymail'''
        
        gmapi.protocol.logout()
        gmapi.protocol = None
        
        titles = [mail[1][0][2][9:].strip("\n\r ") for mail in result.iteritems()]
        titles.reverse()
        self.displaymail(titles, mailbox)

cm = CheckMail()
