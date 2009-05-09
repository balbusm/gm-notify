from twisted.internet import reactor, protocol, ssl, defer
from twisted.internet.protocol import ClientCreator
from twisted.mail.imap4 import *

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
                self.labels.append(onebox[2])
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
    
    def login(self):
        '''Login to Account'''
        
        return self.protocol.login()
    
    def getIDs(self):
        return self.factory.protocol.search(Query(all=True))
    
    def getLabels(self):
        '''returns a deferred with a list of all Labels in the connected Account'''
        
        return self.protocol.getMailboxes()
    
    def _gotProtocol(self, protocol, d):
        '''Called when connection is successfully established and stores a reference to the protocol'''
        
        self.protocol = protocol
        self.protocol.gmail = self
        d.callback(protocol)

