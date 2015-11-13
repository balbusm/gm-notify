#!/usr/bin/env python
# -*- coding: utf-8 -*-
# settings_provider.py v0.10.3
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
#
from __future__ import print_function

from gi.repository import Gio

def create_settings_provider(username):
    if username:
        return AccountSettingsProvider(username)
    else:
        return DefaultSettingsProvider()

class AccountSettingsProvider:
    def __init__(self, username):
        self.client = Gio.Settings("net.launchpad.gm-notify.account", "/net/launchpad/gm-notify/" + username + "/")
    
    def retrieve_sound_file(self, default_file = None):
        soundfile = self.client.get_string("soundfile")
        if soundfile == '':
            soundfile = default_file
        return soundfile

    def retrieve_sound_enabled(self):
        return self.client.get_boolean("play-sound")
    
    def retrieve_ports_range(self):
        port_range = self.client.get_property("settings-schema").get_key("preferred-port").get_range()
        # cast array to int
        result = list(map(int, port_range[1]))
        return result
    
    def retrieve_preferred_port(self):
        return int(self.client.get_string("preferred-port"))

    def retrieve_ignore_inbox(self):
        return self.client.get_boolean("ignore-inbox")

    
    def retrieve_labels(self):
        return self.client.get_strv("labels")

    
    def retrieve_use_mail_client(self):
        return self.client.get_boolean("openclient")

    def save_labels(self, labels):
        self.client.set_strv("labels", labels)

    
    def save_ignore_inbox(self, ignore_inbox):
        self.client.set_boolean("ignore-inbox", ignore_inbox)

    
    def save_use_mail_client(self, use_mail_client):
        self.client.set_boolean("openclient", use_mail_client)

    
    def save_sound_enabled(self, enabled):
        self.client.set_boolean("play-sound", enabled)

    
    def save_sound_file(self, sound_file):
        self.client.set_string("soundfile", sound_file)

    
    def save_preferred_port(self, preferred_port):
        self.client.set_string("preferred-port", str(preferred_port))
        
    def remove_all_settings(self):
        self.client.reset("")
    
class DefaultSettingsProvider:
    def retrieve_sound_file(self, default_file = None):
        return default_file

    def retrieve_sound_enabled(self):
        return False
    
    def retrieve_ports_range(self):
        return [443]
    
    def retrieve_preferred_port(self):
        return 443

    def retrieve_ignore_inbox(self):
        return False

    def retrieve_labels(self):
        return ''
    
    def retrieve_use_mail_client(self):
        return False
    
    def save_labels(self, mailboxes):
        raise NotImplementedError("Saving not supported") 

    
    def save_ignore_inbox(self, ignore_inbox):
        raise NotImplementedError("Saving not supported")

    
    def save_use_mail_client(self, use_mail_client):
        raise NotImplementedError("Saving not supported")

    
    def save_sound_enabled(self, enabled):
        raise NotImplementedError("Saving not supported")

    
    def save_sound_file(self, sound_file):
        raise NotImplementedError("Saving not supported")

    
    def save_preferred_port(self, preferred_port):
        print("Ignoring save_preferred_port")

    def remove_all_settings(self):
        raise NotImplementedError("Removing not supported")

