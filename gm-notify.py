#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gm-notify.py v0.5
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
import sys, subprocess
import gettext
import gmailatom, keyring

########
### Edit this to change the check interval (value counted in seconds)
########

checkinterval = 90

########
### End of config
########

_ = gettext.translation('gm-notify-de', fallback=True).ugettext

class CheckMail():
    def __init__(self):
        '''initiates DBUS-Messaging interface, creates the feedreader and registers with indicator-applet.
        In the end it starts the periodic check timer and a gtk main-loop'''
        
        # Initiate pynotify and Feedreader with Gnome-Keyring Credentials
        if not pynotify.init("GMail Notifier"):
            sys.exit(-1)
        
        keys = keyring.Keyring("GMail", "mail.google.com", "http")
        if keys.has_credentials():
            creds = keys.get_credentials()
        else:
            self.showNotification(_("No crendentials"), _("Please add credentials for mail.google.com (http) to the gnome keyring (via set-gmail-password.py script) and allow gm-notify accessing it."))
            sys.exit(-1)
        
        self.atom = gmailatom.GmailAtom(creds[0], creds[1])
        self.oldmail = []
        
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
    
    def serverClick(self, server):
        '''called when the server is clicked in the indicator-applet to open the gmail account'''
        subprocess.Popen("xdg-open 'https://mail.google.com/mail/'", shell=True)
    
    def filterNewMail(self):
        '''returns the ids of new mails since last check in a list'''
        
        try:
            self.atom.refreshInfo()
        except urllib2.HTTPError:
            self.showNotification(_("Wrong credentials"), _("please reenter your credentials with the set-gmail-password.py script."))
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
        
        # create notifications
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
