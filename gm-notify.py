#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify.py v0.7
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
import pynotify, indicate, urllib2
import gtk, gobject
import pygst
pygst.require("0.10")
import gst
import gconf
import sys, subprocess
import gettext
import gmailatom, keyring

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
            subprocess.Popen("/usr/local/bin/gm-notify-config.py", shell=True)
            if keys.has_credentials():
                creds = keys.get_credentials()
            else:
                self.showNotification(_("No Credentials"), _("You didn't complete the configuration. To try again, please restart the GMail Notifier"))
                sys.exit(-1)
        
        self.atom = gmailatom.GmailAtom(creds[0], creds[1])
        self.oldmail = []
        
        # Init gconf to read config values
        self.client = gconf.client_get_default()
        if self.client.get_string("/apps/gm-notify/checkinterval"):
            checkinterval = int(float(self.client.get_string("/apps/gm-notify/checkinterval")))
        else:
            checkinterval = 90
        
        # init sound
        if self.client.get_string("/apps/gm-notify/soundfile"):
            self.player = gst.element_factory_make("playbin", "player")
            self.player.set_property("video-sink", gst.element_factory_make("fakesink", "fakesink"))
            self.player.set_property("uri", "file://" + self.client.get_string("/apps/gm-notify/soundfile"))
            bus = self.player.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self.gst_message)
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
        subprocess.Popen("xdg-open 'https://mail.google.com/mail/'", shell=True)
    
    def filterNewMail(self):
        '''returns the ids of new mails since last check in a list'''
        
        try:
            self.atom.refreshInfo()
        except urllib2.HTTPError:
            self.showNotification(_("Wrong credentials"), _("Please use the configuration utility to enter correct credentials."))
            sys.exit(-1)
        except: # No network connection?
            print _("Exception caught while refreshing feed. Check your network connection.")
            return [] # Just indicate that there is nothing new
        
        # generate an almost unique message id for each unread mail and check if
        # it isn't already stored in the oldmail-list, which would mean that
        # we already notified the user of this mail
        new = []
        for i in range(0, self.atom.getUnreadMsgCount()):
            msgid = self.atom.getMsgTitle(i) + ":" + self.atom.getMsgSummary(i)
            if not msgid in self.oldmail:
                new.append(i)
        
        # regenerate the oldmail-list with all mails we processed yet
        # and because we already processed all mails this is equivalent to the 
        # ones that are yet unread
        self.indicators = []
        self.oldmail = []
        for i in range(0, self.atom.getUnreadMsgCount()):
            self.addIndicator(self.atom.getMsgTitle(i))
            self.oldmail.append(self.atom.getMsgTitle(i) + ":" + self.atom.getMsgSummary(i))
        
        return new
    
    def checkmail(self):
        '''calls getnewmail() to retrieve new mails and presents them via
        libnotify (notify-osd) to the user. Returns True for gobject.add_timeout()'''
        
        # agregate the titles of the messages... cut the string if longer than 20 chars
        titles = ""
        newmail = self.filterNewMail()
        for i in newmail:
            title = self.atom.getMsgTitle(i)
            if len(title) > 20:
                title = title[0:20] + "..."
            if len(title) == 0:
                title = _("(no subject)")
            
            if len(titles) == 0:
                titles = title
            else:
                titles += "\n- " + title
        
        # play a sound?
        if len(newmail) > 0 and self.player:
            self.player.set_state(gst.STATE_PLAYING)
        
        # create notifications and play sound
        if not "\n" in titles and not titles == "":
            self.showNotification(_("Incoming Message"), titles)
        elif "\n" in titles:
            self.showNotification(str(len(newmail)) + _(" new Messages"), "- " + titles)
    
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

cm = CheckMail()
