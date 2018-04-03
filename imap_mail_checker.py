#!/usr/bin/env python
# -*- coding: utf-8 -*-
# imap_mail_checker.py v2.0
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

import argparse
import imaplib2
from email.header import decode_header, make_header
from email.parser import FeedParser
import quopri
import re

from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler

from oauth2client import client, tools

from keyring_storage import KeyringStorage

AUTH_SCOPE = "https://mail.google.com/"
SECRET_LOCATION = "data/secret.json"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_AUTH_METHOD = "XOAUTH2"
IDLE_TIME = 3
IDLE_JOB_ID = 'idle'

class ImapMailChecker:
    
    
    def __init__(self, login, labels = ["Inbox"], callback_worker = None, on_fetch_cb=None, on_auth_succeeded=None):
        self.login = login
        self.running = False
        self.labels = labels
        self.scheduler = BackgroundScheduler()
        # Add call on main thread in callbackworker
        self.on_fetch_cb = on_fetch_cb if on_fetch_cb else self.default_callback
        self.on_auth_succeeded = on_auth_succeeded if on_auth_succeeded else self.default_callback
        self.on_auth_failed = self.default_callback
        self.on_connection_error_cb = self.default_callback
        
    def default_callback(self, *args, **kwargs):
        pass
    
    def set_on_auth_succeeded(self, on_auth_succeeded):
        self.on_auth_succeeded = on_auth_succeeded
        
    def set_on_auth_failed(self, on_auth_failed):
        pass
        
    def set_on_connection_error_cb(self, on_connection_error_cb):
        pass

    def is_running(self):
        return self.running

    def stop(self):
        self.running = False
        self.scheduler.shutdown()
  
        
    def get_access_token(self):
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


    def __oauth2(self, response):
        access_token = self.get_access_token()
        return "user=%s\001auth=Bearer %s\001\001" % (self.login, access_token)

    
    def connect(self):
        if self.is_running():
            return
        self.running = True
        
        self.scheduler.start()
        self.scheduler.add_job(self.__auth)
    
    def __auth(self):
        self.imapClient = imaplib2.IMAP4_SSL(IMAP_HOST, IMAP_PORT, debug=True)

        response = self.imapClient.authenticate(IMAP_AUTH_METHOD, self.__oauth2)
        if response[0] ==  "OK":
            self.on_auth_succeeded(self.login)
            self.imapClient.select(readonly=True)
            self.fetch_inbox()
        else:
            self.on_auth_failed(self.login, response[1])
    
    def __idle_loop(self):
        self.imapClient.idle(callback = self.on_idle_event, cb_arg = self.imapClient.response("IDLE"))
        self.scheduler.add_job(self.__idle_loop, 'interval', minutes = IDLE_TIME, id = IDLE_JOB_ID, replace_existing = True  )
    
    def fetch_inbox(self):
        self.scheduler.add_job(self.__fetch_inbox)
    
    
    def __fetch_inbox(self):
        typ, data = self.imapClient.search(None, '(UNSEEN)')
        for num in data[0].split():
            self.imapClient.fetch(num, '(BODY.PEEK[TEXT] BODY.PEEK[HEADER.FIELDS (SUBJECT MESSAGE-ID Content-Type)])', callback = self.on_fetch_event)
        self.__idle_loop()
        # (BODY.PEEK[TEXT] BODY.PEEK[HEADER.FIELDS (SUBJECT MESSAGE-ID Content-Type)])
    
    def on_fetch_event(self, cb_arg_list):
        response, cb_arg, error = cb_arg_list
        typ, data = response
        if not data:
            return
        
        parser = FeedParser()
        # filtered header
        parser.feed(data[1][1])
        # message body
        parser.feed(data[0][1])
        message = parser.close()
        
        payload = None
        
        if not message.is_multipart():
            payload = message.get_payload(decode = True)
        else:
            for complex_payload in message.get_payload():
                if complex_payload.get_content_type() == "text/html":
                    payload = complex_payload.get_payload(decode = True)
                    break
            if payload is None:
                payload = message.get_payload().get_payload(decode = True)
            
#         header = make_header(decode_header(message.get_payload(1).get_payload()))
#         decoded_string = quopri.decodestring(unicode(h))
            
        soup = BeautifulSoup(re.sub("<head>.*</head>", "", payload) , 'html.parser')
        snippet = soup.get_text()
        self.on_fetch_cb(self.login, unicode(make_header(decode_header(message["subject"]))), snippet)

    
    def on_idle_event(self, idle_result):
        result = idle_result[1][0]
        if result == "TIMEOUT":
            return
        self.__fetch_inbox()
#         imapClient.close()
#         imapClient.logout()
        
# mailChecker = ImapMailChecker("balbusm@gmail.com")
# mailChecker.connect()
        