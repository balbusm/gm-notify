#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gtalk.py v1.0
# Google Talk mail notification client library
#
# Copyright (c) 2009-2010, Alexander Hungenberg <alexander.hungenberg@gmail.com>
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

from twisted.words.protocols.jabber import xmlstream, client, jid
from twisted.words.xish import domish
from twisted.internet import reactor, task, error, ssl
from twisted.internet.error import TimeoutError, ConnectionRefusedError

from datetime import datetime

GTALK_HOST = "talk.google.com"

_DEBUG = True
COLOR_GREEN = "\033[92m"
COLOR_END = "\033[0m"
def DEBUG(msg):
    if _DEBUG:
        curent_time = datetime.now()
 
        print(COLOR_GREEN + str(curent_time) + " " +str(msg) + COLOR_END)

class GTalkClientFactory(xmlstream.XmlStreamFactory):
    
    def __init__(self, jid, password, settings_provider):
        a = client.XMPPAuthenticator(jid, password)
        xmlstream.XmlStreamFactory.__init__(self, a)
        self.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.clientConnected)
        
        self.jid = jid
        self.reconnect = True
        self.connection_failed = False
        self.connection_lost = False
        self.cb_connection_error = None
        self.settings_provider = settings_provider
        self.port = self.settings_provider.retrieve_preferred_port()
    
    def clientConnectionLost(self, connector, reason):
        DEBUG("clientConnectionLost %s" % str(reason))
        self.connection_lost = True
        if not self.reconnect:
            return
        
        DEBUG("clientConnectionLost: Reconnecting with the same settings (port %d)" % connector.port)
        if self.cb_connection_error : self.cb_connection_error(self.jid.full(), reason)
        # reconnect on the same port as it used to work
        xmlstream.XmlStreamFactory.clientConnectionLost(self, connector, reason)
         
    def clientConnectionFailed(self, connector, reason):
        DEBUG("clientConnectionFailed %s on port: %d reconnecting: %s" % (str(reason), connector.port, str(self.reconnect)))
        self.connection_failed = True
        if not self.reconnect:
            return
        
        DEBUG("clientConnectionFailed: Connection failed");
        if self.cb_connection_error : self.cb_connection_error(self.jid.full(), reason)
    
    def clientConnected(self, xmlstream):
        DEBUG("clientConnected") 
        self.connection_failed = False
        self.connection_lost = False
    
    def getCurrentPort(self):
        return self.port
    
    def hasConnectionFailedOrLost(self):
        return self.connection_failed or self.connection_lost
    
    def setOnConnectionErrorCB(self, cb_connection_error):
        self.cb_connection_error = cb_connection_error


class MailChecker():
    def __init__(self, jid, password, settings_provider, labels=[], cb_new=None, cb_count=None):
        self.host = GTALK_HOST
        self.settings_provider = settings_provider
        self.jid = jid
        self.password = password
        self.cb_new = cb_new
        self.cb_count = cb_count
        self.cb_auth_succeeded = None
        self.cb_auth_failed = None
        self.cb_connection_error = None
        self.cb_connected = None
        
        self.last_tids = {}
        self.labels = labels
        self.labels_iter = iter(self.labels)
        self.count = {}
        self.mails = []
        
        # indicates whether we are in a state ready for complete interaction
        # (Authentication and Usersetting finished)
        # not disconnected, no query running
        self.ready_for_query_state = False
        self.timeout_call_id = None
        self.disconnected = True
        self.running = False
    
    def setOnConnectionErrorCB(self, cb_connection_error):
        self.cb_connection_error = cb_connection_error
    
    def setOnConnectedCB(self, cb_connected):
        self.cb_connected = cb_connected
        
    def setOnAuthFailed(self, cb_auth_failed):
        self.cb_auth_failed = cb_auth_failed

    def setOnAuthSucceeded(self, cb_auth_succeeded):
        self.cb_auth_succeeded = cb_auth_succeeded
    
    def is_running(self):
        return self.running
    
    def die(self):
        DEBUG("Dying...")
        self.factory.reconnect = False
        self.query_task.stop()
        self.connector.disconnect()
        self.running = False
    
    def connect(self):
        self.factory = GTalkClientFactory(self.jid, self.password, self.settings_provider)
        self.factory.setOnConnectionErrorCB(self.cb_connection_error)
        self.factory.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnectCB)
        self.factory.addBootstrap(xmlstream.STREAM_ERROR_EVENT, self.disconnectCB)
        self.factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failedCB)
        self.factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connectedCB)
        self.factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticationCB)
        
        self.factory.reconnect = True
        
        self.query_task = task.LoopingCall(self.queryInbox)
        self.query_task.start(60)
        self.running = True
        
        self.connector = reactor.connectSSL(self.host, self.factory.getCurrentPort(), self.factory, ssl.ClientContextFactory())
    
    def reply_timeout(self):
        DEBUG("reply_timeout")
        self.connector.disconnect() # Our reconnecting factory will try the reconnecting

    def send_callback_handler(self, data, callback=None, **kargs):
        try:
            self.timeout_call_id.cancel()
        except error.AlreadyCalled:
            DEBUG("already called timeout_call_id.cancel()")
            return
        if callback:
            callback(data, **kargs)
        else:
            DEBUG("got no callback in send_callback_handler")
            self.connector.disconnect()
    
    def send(self, data, event, callback, **kargs):
        """Emulates a ping like behaviour - adds a timeout for each response
        
        data: Data to be send - e.g. an IQ object (domish.Element)
        event: Event on which the callback should be called (e.g. "/iq")
        callback: callback that gets called when the event occurs
        """
        
        self.timeout_call_id = reactor.callLater(5, self.reply_timeout)
        self.xmlstream.addOnetimeObserver(event, self.send_callback_handler, callback=callback, **kargs)
        self.xmlstream.send(data)
    
    def disconnectCB(self, xmlstream):
        DEBUG("disconnected")
        self.ready_for_query_state = False
        self.factory.reconnect = False
        self.disconnected = True

    def init_failedCB(self, xmlstream):
        DEBUG("init_failedCB")
        if self.cb_auth_failed: self.cb_auth_failed(self.jid.full(), xmlstream.value)
        self.disconnectCB(xmlstream)
    
    def authenticationCB(self, xmlstream):
        DEBUG("authenticationCB")
        if self.cb_auth_succeeded: self.cb_auth_succeeded(self.jid.full())
        self.factory.resetDelay()
        
        # We set the usersetting mail-notification
        iq = domish.Element((None, "iq"), attribs={"type": "set", "id": "user-setting-3"})
        usersetting = iq.addElement(("google:setting", "usersetting"))
        mailnotifications = usersetting.addElement((None, "mailnotifications"))
        mailnotifications.attributes['value'] = "true"
        self.send(iq, "/iq", self.usersettingIQ)
    
    def usersettingIQ(self, iq):
        DEBUG("usersettingIQ")
        self.ready_for_query_state = True
        self.queryInbox()
    
    def queryInbox(self):
        DEBUG("queryInbox")
        if not(self.ready_for_query_state or self.factory.hasConnectionFailedOrLost()):
            DEBUG("queryInbox: ready for query: %s connection_failed_or_lost: %s" % (str(self.ready_for_query_state), str(self.factory.hasConnectionFailedOrLost())))
            DEBUG("queryInbox: skipping query request")
            return
        if self.disconnected:
            DEBUG("queryInbox: disconnected")
            self.factory.reconnect = True
            self.connector.connect()
            return
        self.ready_for_query_state = False
        
        self.xmlstream.removeObserver("/iq", self.gotNewMail)
        
        iq = domish.Element((None, "iq"), attribs={"type": "get", "id": "mail-request-1"})
        query = iq.addElement(("google:mail:notify", "query"))
        DEBUG("queryInbox: requesting for label")
        self.send(iq, "/iq", self.gotLabel)
    
    def queryLabel(self):
        try:
            label = self.labels_iter.next()
            DEBUG("queryLabel " + label)
            iq = domish.Element((None, "iq"), attribs={"type": "get", "id": "mail-request-1"})
            query = iq.addElement(("google:mail:notify", "query"))
            query.attributes['q'] = "label:%s AND is:unread" % label
            self.send(iq, "/iq", self.gotLabel, label=label)
        except StopIteration:
            DEBUG("queryLabel: end of iteration")
            self.labels_iter = iter(self.labels)
            self.xmlstream.addObserver("/iq", self.gotNewMail)
            if self.cb_count: self.cb_count(self.jid.full(), self.count)
            if self.mails and self.cb_new: self.cb_new(self.jid.full(), self.mails)
            self.mails = []
            self.ready_for_query_state = True
    
    def gotLabel(self, iq, label="inbox"):
        if iq.firstChildElement() and iq.firstChildElement().name == "mailbox":
            mailbox = iq.firstChildElement()
            if label in self.count and self.count[label] < int(mailbox.attributes['total-matched']):
                self.query_new_mail = True
            self.count[label] = int(mailbox.attributes['total-matched'])
            
            # Aggregating titles, summaries etc.
            threads = mailbox.children
            if threads:
                for thread in threads:
                    if not label in self.last_tids or thread['tid'] > self.last_tids[label]:
                        mail = {}
                        for child in thread.children:
                            if child.name == "senders":
                                for sender in child.children:
                                    if "address" in sender.attributes:
                                        mail['sender_address'] = unicode(sender.attributes['address'])
                                    if "name" in sender.attributes:
                                        mail['sender_name'] = unicode(sender.attributes['name'])
                            elif child.name == "labels":
                                mail['labels'] = unicode(child).split("|")
                            elif child.name == "subject":
                                mail['subject'] = unicode(child)
                            elif child.name == "snippet":
                                mail['snippet'] = unicode(child)
                        self.mails.append(mail)
                self.last_tids[label] = unicode(threads[0].attributes['tid'])
                
            self.queryLabel()
        else:
            DEBUG("ERROR: received unexpected iq after querying for INBOX")
            self.connector.disconnect()
    
    def gotNewMail(self, iq=None):
        if not iq or (iq.firstChildElement() and iq.firstChildElement().name == "new-mail"):
            self.xmlstream.removeObserver("/iq", self.gotNewMail)
            
            # Acknowledge iq
            if iq:
                iq = domish.Element((None, "iq"), attribs={"type": "result", "id": iq.attributes['id']})
                self.xmlstream.send(iq)
            
            # Get the new mail
            self.queryInbox()
        else:
            DEBUG("this was no new mail iq / ignoring it")
    
    def gotNewMailQueryResult(self, iq):
        if iq.firstChildElement() and iq.firstChildElement().name == "mailbox":
            mailbox = iq.children[0]
            threads = mailbox.children
            if threads:
                newest = threads[0]
                self.newest_tid = unicode(newest.attributes['tid'])
                
                mails = []
                
                for thread in threads:
                    mail = {}
                    for child in thread.children:
                        if child.name == "senders":
                            for sender in child.children:
                                if "address" in sender.attributes:
                                    mail['sender_address'] = unicode(sender.attributes['address'])
                                if "name" in sender.attributes:
                                    mail['sender_name'] = unicode(sender.attributes['name'])
                        elif child.name == "labels":
                            mail['labels'] = unicode(child).split("|")
                        elif child.name == "subject":
                            mail['subject'] = unicode(child)
                        elif child.name == "snippet":
                            mail['snippet'] = unicode(child)
                    mails.append(mail)
                
                self.cb_new(self.jid.full(), mails)
        
        self.ready_for_query_state = True
        if iq: self.queryInbox()
    
    def rawDataIn(self, buf):
        print("> %s" % buf)
    
    def rawDataOut(self, buf):
        print("< %s" % buf)
    
    def connectedCB(self, xmlstream):
        self.xmlstream = xmlstream
        self.disconnected = False
        if self.cb_connected: self.cb_connected(self.jid.full())
        
        if _DEBUG:
            xmlstream.rawDataInFn = self.rawDataIn
            xmlstream.rawDataOutFn = self.rawDataOut
            
    def getCurrentPort(self):
        return self.factory.getCurrentPort()
