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
import gobject
#import pygst
#pygst.require("0.10")
#import gst
import gconf
from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from twisted.words.protocols.jabber import jid

from gtalk import MailChecker
import keyring

_ = gettext.translation('gm-notify', fallback=True).ugettext

MAILBOXES_NAMES = { "inbox": _("Inbox") }

MAILBOXES_URLS = {  "inbox": _("inbox") }

class CheckMail():
    def __init__(self):
        '''initiates DBUS-Messaging interface, creates the MailChecker and registers with indicator-applet.
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
        self.jid = jid.JID(self.creds[0])
        if self.jid.host in gmail_domains:
            self.domain = None
        else:
            self.domain = self.jid.host
        
        # init gconf to read config values
        self.client = gconf.client_get_default()
        
        # init sound
#        soundfile = soundlib.findsoundfile(self.client.get_string("/desktop/gnome/sound/theme_name"))
#        if self.client.get_bool("/apps/gm-notify/play_sound"):
#            if soundfile:
#                self.player = gst.element_factory_make("playbin", "player")
#                self.player.set_property("video-sink", gst.element_factory_make("fakesink", "fakesink"))
#                self.player.set_property("uri", "file://" + soundfile)
#                bus = self.player.get_bus()
#                bus.add_signal_watch()
#                bus.connect("message", self.gst_message)
#            else:
#                self.showNotification(_("No sound selected"), _("Please select a new-message sound in the audio settings or unselect the corresponding option."))
#                sys.exit(-1)
#        else:
#            self.player = None
        
        # Register with Indicator-Applet
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.mail")
        self.server.set_desktop_file("/usr/share/applications/gm-notify.desktop")
        self.server.connect("server-display", self.serverClick)
        self.indicators = {}
        
        # Retrieve the mailbox we're gonna check
        self.mailboxes = self.client.get_list("/apps/gm-notify/mailboxes", gconf.VALUE_STRING)
        self.mailboxes.insert(0, "inbox")
        self.initial = True # Prevents draw-attention to be set when started
        self.addMailboxIndicators()
        self.checker = MailChecker(self.jid, self.creds[1], self.mailboxes, self.new_mail, self.update_count)
        
        # Check every xx seconds
        gobject.timeout_add_seconds(60, self.checker.queryInbox)
        reactor.run()
    
#    def gst_message(self, bus, message):
#        if message.type == gst.MESSAGE_EOS:
#            self.player.set_state(gst.STATE_NULL)
#        elif message.type == gst.MESSAGE_ERROR:
#            self.player.set_state(gst.STATE_NULL)
#            print "Error: %s - %s" % message.parse_error()
    
    def serverClick(self, server):
        '''called when the server is clicked in the indicator-applet and performs a Mail Check'''
        for indicator in self.indicators:
            self.indicators[indicator].set_property("draw-attention", "false")
            
        self.checker.queryInbox()
    
    def update_count(self, count):
        for mailbox in count.iteritems():
            i = self.indicators[mailbox[0]]
            if int(i.get_property("count")) < int(mailbox[1]) and not self.initial:
                i.set_property("draw-attention", "true")
            elif int(i.get_property("count")) > int(mailbox[1]):
                i.set_property("draw-attention", "false")
            i.set_property("count", unicode(mailbox[1]))
        self.initial = False
    
    def new_mail(self, mails):
        '''Takes mailbox name and titles of mails, to display notification and add indicators'''
        
        text = ""
        # aggregate the titles of the messages... cut the string if longer than 30 chars
        for mail in mails:
            if "sender_name" in mail: text += mail['sender_name'] + ":\n"
            elif "sender_address" in mail: text += mail['sender_address'] + ":\n"
            
            if "subject" in mail and mail['subject']:
                title = mail['subject']
                if len(title) > 30:
                    title = title[:30] + "..."
            elif "snippet" in mail and mail['snippet']:
                title = mail['snippet'][:30] + "..."
            else:
                title = _("(no content)")
            text += "- " + title + "\n"
            
        self.showNotification(_("Incoming message"), text.strip("\n"))
    
    def labelClick(self, indicator):
        '''called when a label is clicked in the indiicator-applet and opens the corresponding gmail page'''
        if self.domain:
            url = "https://mail.google.com/a/"+self.domain+"/"
        else:
            url = "https://mail.google.com/mail/"
        
        try:
            url += "#%s" % MAILBOXES_URLS[indicator.label]
        except KeyError:
            url += "#label/%s" % indicator.label
        
        indicator.set_property("draw-attention", "false")
        
        # Open mail client
        if self.client.get_bool("/apps/gm-notify/openclient"):
            command = self.client.get_string("/desktop/gnome/url-handlers/mailto/command").split(" ")[0]
            if self.client.get_bool("/desktop/gnome/url-handlers/mailto/needs_terminal"):
                termCmd = self.client.get_string("/desktop/gnome/applications/terminal/exec")
                if termCmd:
                    termCmd += " " + self.client.get_string("/desktop/gnome/applications/terminal/exec_arg") + " "
                else:
                    termCmd = "gnome-terminal -x "
                command = termCmd + command
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen("xdg-open "+url, shell=True)
    
    def showNotification(self, title, message):
        '''takes a title and a message to display the email notification. Returns the
        created notification object'''
        
        n = pynotify.Notification(title, message, "notification-message-email")
        n.show()
        
        return n
    
    def addMailboxIndicators(self):
        for mailbox in reversed(self.mailboxes):
            new_indicator = indicate.Indicator()
                
            try:
                new_indicator.set_property("name", MAILBOXES_NAMES[mailbox])
            except KeyError:
                new_indicator.set_property("name", mailbox)
            new_indicator.set_property("count", "0")
            new_indicator.show()
            new_indicator.label = mailbox
            new_indicator.connect("user-display", self.labelClick)
            self.indicators[mailbox] = new_indicator

cm = CheckMail()
