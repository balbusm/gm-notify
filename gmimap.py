from twisted.internet import reactor, protocol, ssl, defer
from twisted.mail.imap4 import *

class IMAPClient(IMAP4Client):
    def login(self):
        return self.login(self.factory.username, self.factory.password)
    
    def mailboxesReceived(self, result, deferred):
        self.labels = []
        for onebox in result:
            if not onebox[2].startswith("[Gmail]") and not onebox[2] == "INBOX":
                self.labels.append(onebox[2])
        deferred.callback(self.labels)
    
    def getMailboxes(self):
        d = defer.Deferred()
        self.list("", "*").addCallback(self.mailboxesReceived, d)
        return d

class IMAPFactory(protocol.ClientFactory):
    def __init__(self, username, password):
        self.username = username
        self.password = password
    
    def buildProtocol(self, addr):
        self.protocol = IMAPClient()
        
        return self.protocol

class GMail():
    def __init__(self, username, password):
        self.factory = IMAPFactory(username, password)
        reactor.connectSSL("imap.gmail.com", 993, self.factory, ssl.ClientContextFactory())
    
    def login(self):
        return self.factory.protocol.login()
    
    def getData(self, function, callback, errback=None):
        '''get some data. To use pass the desired "after-connect" method to this
        and a callback when this has been finished'''
        print dir(self.factory)
    
    def getIDs(self):
        self.factory.protocol.search(Query(all=True))
    
    def getLabels(self, result, protocol):
        protocol.getMailboxes().addCallback(self.callback)
    
    def __default_errback(self, reason):
        raise Exception(reason)

