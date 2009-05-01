from twisted.internet import reactor, protocol, ssl, defer
from twisted.mail.imap4 import *

class IMAPClient(IMAP4Client):
    def __init__(self, username, password, callback, errback):
        IMAP4Client.__init__(self, ssl.ClientContextFactory())
        self.username = username
        self.password = password
        self.callback = callback
        self.errback = errback
        
    def connectionMade(self):
        self.login(self.username, self.password).addCallback(self.callback, self).addErrback(self.errback)
    
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
    def __init__(self, username, password, callback, errback):
        self.username = username
        self.password = password
        self.callback = callback
        self.errback = errback
    
    def buildProtocol(self, addr):
        p = IMAPClient(self.username, self.password, self.callback, self.errback)
        
        return p

class GMail():
    def getLabels(self, username, password, callback, errback=None):
        self.username = username
        self.password = password
        self.labelcallback = callback
        self._connect(self._getLabels1, errback)
    
    def _getLabels1(self, result, protocol):
        protocol.getMailboxes().addCallback(self.labelcallback)
    
    def _connect(self, callback, errback=None):
        if not errback:
            errback = self.__default_errback
            
        factory = IMAPFactory(self.username, self.password, callback, errback)
        reactor.connectSSL("imap.gmail.com", 993, factory, ssl.ClientContextFactory())
    
    def __default_errback(self, reason):
        raise Exception(reason)

