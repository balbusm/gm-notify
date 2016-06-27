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

import gm_notify_keyring as keyring

from oauth2client.client import Storage, Credentials

class KeyringStorage(Storage):
    def __init__(self, user, lock=None):
        super(KeyringStorage, self).__init__()
        self._user = user
        self._keys = keyring.Keyring("GMail", "mail.google.com", "http")
        

    def locked_get(self):
        """Retrieve the credentials from the dictionary, if they exist.
        Returns: A :class:`oauth2client.client.OAuth2Credentials` instance.
        """
        
        if self._keys.has_credentials(self._user) is False:
            return None

        json_credentials = self._keys.get_credentials(self._user).password
        credentials = Credentials.new_from_json(json_credentials)
        credentials.set_store(self)

        return credentials

    def locked_put(self, credentials):
        """Save the credentials to the dictionary.
        Args:
            credentials: A :class:`oauth2client.client.OAuth2Credentials`
                         instance.
        """
        self._keys.set_credentials(self._user, credentials.to_json())

    def locked_delete(self):
        """Remove the credentials from the dictionary, if they exist."""
        self._keys.delete_credentials(self._user)
