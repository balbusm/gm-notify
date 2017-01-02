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



import imaplib2
class ImapMailChecker:

    def __init_(self):
        pass
  
    def cb(self, cb_arg_list):
        response, cb_arg, error = cb_arg_list
        typ, data = response
        if not data:
            return
        for field in data:
            if type(field) is not tuple:
                continue
            print('Message %s:\n%s\n'
                % (field[0].split()[0], field[1]))
    
    def oauth2(self, response):
        print(response)
    
    def connect(self):
        imapClient = imaplib2.IMAP4_SSL("imap.gmail.com", 993, debug=True)
        imapClient.authenticate("XOAUTH2", self.oauth2)
        
        imapClient.select(readonly=True)
        typ, data = imapClient.search(None, 'ALL')
        for num in data[0].split():
            imapClient.fetch(num, '(RFC822)', callback=self.cb)
        imapClient.close()
        imapClient.logout()
        
mailChecker = ImapMailChecker()
mailChecker.connect()
        