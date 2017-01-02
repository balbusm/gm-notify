#!/usr/bin/env python
# -*- coding: utf-8 -*-
# imap.py v2.0
# Provides settins to GMail notify
#
# Copyright (c) 2017, Mateusz Balbus <balbusm@gmail.com>
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


import argparse
import imaplib2

from oauth2client import client, tools

from keyring_storage import KeyringStorage

AUTH_SCOPE = "https://mail.google.com/"
SECRET_LOCATION = "data/secret.json"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_AUTH_METHOD = "XOAUTH2"

class ImapMailChecker:
    
    
    def __init__(self, login):
        self.login = login
        pass
  
    def on_fetch(self, cb_arg_list):
        response, cb_arg, error = cb_arg_list
        typ, data = response
        if not data:
            return
        print("New message\n")
        for field in data:
            if type(field) is not tuple:
                continue
            print('Message %s:\n%s\n'
                % (field[0].split()[0], field[1]))
    
    def get_access_token(self):
        # TODO: put storage into encrypted place
        storage = KeyringStorage(self.login)
        credentials = storage.get()
        try:
            if credentials:
                return credentials.get_access_token().access_token
        except client.HttpAccessTokenRefreshError:
            # TODO: add logging
            # refresh token expired go for authentication
            pass
        
        flow = client.flow_from_clientsecrets(
          SECRET_LOCATION,
          scope=AUTH_SCOPE,
          redirect_uri='http://localhost:8080',
          login_hint=self.login)
        parser = argparse.ArgumentParser(parents=[tools.argparser])
        flags = parser.parse_args()

        credentials = tools.run_flow(flow, storage, flags, None)
        # TODO: add check of email address
        return credentials.access_token


    def oauth2(self, response):
        access_token = self.get_access_token()
        return "user=%s\001auth=Bearer %s\001\001" % (self.login, access_token)

    
    def connect(self):
        imapClient = imaplib2.IMAP4_SSL(IMAP_HOST, IMAP_PORT, debug=True)
        imapClient.authenticate(IMAP_AUTH_METHOD, self.oauth2)
        
        imapClient.select(readonly=True)
        typ, data = imapClient.search(None, '(UNSEEN)')
        for num in data[0].split():
            imapClient.fetch(num, '(RFC822)', callback=self.on_fetch)
        imapClient.close()
        imapClient.logout()
        
mailChecker = ImapMailChecker("mail@gmail.com")
mailChecker.connect()
        