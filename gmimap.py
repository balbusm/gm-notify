#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gmimap.py v0.9
# simple, twisted based, IMAP4 Client class to access Gmail
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
from twisted.internet import reactor, protocol, ssl, defer
from twisted.internet.protocol import ClientCreator
from twisted.mail.imap4 import MessageSet, IMAP4Client, decoder

class IMAPClient(IMAP4Client):
    def login(self):
        return IMAP4Client.login(self, self.gmail.username, self.gmail.password)
    
    def getMailboxes(self):
        d = defer.Deferred()
        self.list("", "*").addCallback(self.gotMailboxes, d)
        return d
    
    def gotMailboxes(self, result, deferred):
        self.labels = []
        for onebox in result:
            if not onebox[2].startswith("[Google Mail]") \
               and not onebox[2].startswith("[Gmail]") \
               and not onebox[2] == "INBOX":
                self.labels.append(decoder(onebox[2])[0])
        deferred.callback(self.labels)

class GMail():
    def __init__(self, username, password):
        self.username = username
        self.password = password
    
    def connect(self):
        '''Connect with IMAP Server'''
        
        d = defer.Deferred()
        c = ClientCreator(reactor, IMAPClient)
        c.connectSSL("imap.gmail.com", 993, ssl.ClientContextFactory()).addCallback(self._gotProtocol, d)
        
        return d
    
    def getSubjects(self, oldcount):
        return self.protocol.fetchSpecific(str(oldcount) + ":*", headerType="HEADER.FIELDS", headerArgs=["SUBJECT"])
    
    def getLabels(self):
        '''returns a deferred with a list of all Labels in the connected Account'''
        
        return self.protocol.getMailboxes()
    
    def _gotProtocol(self, protocol, d):
        '''Called when connection is successfully established and stores a reference to the protocol'''
        
        self.protocol = protocol
        self.protocol.gmail = self
        d.callback(protocol)
