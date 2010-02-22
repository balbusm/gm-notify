from twisted.words.protocols.jabber import xmlstream, client, jid
from twisted.words.xish import domish
from twisted.internet import reactor

COLOR_GREEN = "\033[92m"
COLOR_END = "\033[0m"
def DEBUG(msg):
    print COLOR_GREEN + msg + COLOR_END

class MailChecker():
    def __init__(self, jid, password, labels, cb_new, cb_count):
        self.host = "talk.google.com"
        self.port = 5222
        self.jid = jid
        self.password = password
        self.cb_new = cb_new
        self.cb_count = cb_count
        
        self.last_tid = "0"
        self.labels = labels
        self.labels_iter = iter(self.labels)
        self.count = {}
        # True: use mailbox to fill labels with unread count
        # False: Got new mail: query since tid and display notification

        self.factory = client.XMPPClientFactory(jid, password)
        self.factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connectedCB)
        self.factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticationCB)
        reactor.connectTCP(self.host, self.port, self.factory)

    def authenticationCB(self, xmlstream):
        xmlstream.addOnetimeObserver("/iq", self.usersettingIQ)
        
        # We set the usersetting mail-notification
        iq = domish.Element((None, "iq"), attribs={"type": "set", "id": "user-setting-3"})
        usersetting = iq.addElement(("google:setting", "usersetting"))
        mailnotifications = usersetting.addElement((None, "mailnotifications"))
        mailnotifications.attributes['value'] = "true"
        xmlstream.send(iq)
    
    def usersettingIQ(self, iq):
        self.queryInbox()
    
    def queryInbox(self):
        self.xmlstream.removeObserver("/iq", self.gotNewMail)
        self.xmlstream.addOnetimeObserver("/iq", self.gotLabel)
        
        iq = domish.Element((None, "iq"), attribs={"type": "get", "id": "mail-request-1"})
        query = iq.addElement(("google:mail:notify", "query"))
        self.xmlstream.send(iq)
    
    def queryLabel(self):
        try:
            label = self.labels_iter.next()

            self.xmlstream.addOnetimeObserver("/iq", self.gotLabel, label=label)
            
            iq = domish.Element((None, "iq"), attribs={"type": "get", "id": "mail-request-1"})
            query = iq.addElement(("google:mail:notify", "query"))
            query.attributes['q'] = "label:%s AND is:unread" % label
            self.xmlstream.send(iq)
        except StopIteration:
            self.labels_iter = iter(self.labels)
            self.xmlstream.addObserver("/iq", self.gotNewMail)
            self.cb_count(self.count)
    
    def gotLabel(self, iq, label="inbox"):
        if iq.firstChildElement() and iq.firstChildElement().name == "mailbox":
            mailbox = iq.firstChildElement()
            self.count[label] = unicode(mailbox.attributes['total-matched'])
            
            if label == "inbox":
                if mailbox.firstChildElement():
                    self.last_tid = mailbox.firstChildElement().attributes['tid']
            
            self.queryLabel()
        else:
            DEBUG("ERROR: received unexpected iq after querying for INBOX")
    
    def gotNewMail(self, iq):
        if iq.firstChildElement() and iq.firstChildElement().name == "new-mail":
            self.xmlstream.removeObserver("/iq", self.gotNewMail)
            
            # Acknowledge iq
            iq = domish.Element((None, "iq"), attribs={"type": "result", "id": iq.attributes['id']})
            self.xmlstream.send(iq)
            
            # Get the new mail
            self.xmlstream.addOnetimeObserver("/iq", self.gotNewMailQueryResult)
            
            iq = domish.Element((None, "iq"), attribs={"type": "get", "id": "mail-request-1"})
            query = iq.addElement(("google:mail:notify", "query"))
            query.attributes['newer-than-tid'] = self.last_tid
            self.xmlstream.send(iq)
        else:
            DEBUG("ERROR: This was no new mail iq")
    
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
                
                self.cb_new(mails)
        
        self.queryInbox()
    
    def rawDataIn(self, buf):
        print u"< %s" % unicode(buf, "utf-8")
    
    def rawDataOut(self, buf):
        print u"> %s" % unicode(buf, "utf-8")
    
    def connectedCB(self, xmlstream):
        self.xmlstream = xmlstream
        
        xmlstream.rawDataInFn = self.rawDataIn
        xmlstream.rawDataOutFn = self.rawDataOut