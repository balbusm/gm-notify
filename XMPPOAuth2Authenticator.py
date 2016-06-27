#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.words.xish import domish, xpath, utility
from twisted.words.protocols.jabber import xmlstream, sasl, error
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber import xmlstream, client, jid
from twisted.words.protocols.jabber.client import CheckVersionInitializer,BindInitializer,SessionInitializer
from twisted.words.protocols.jabber.sasl import NS_XMPP_SASL, SASLNoAcceptableMechanism, get_mechanisms, SASLAuthError, SASLIncorrectEncodingError, fromBase64, b64encode
from twisted.words.protocols.jabber.sasl_mechanisms import ISASLMechanism

from twisted.internet import defer
from twisted.words.protocols.jabber import sasl_mechanisms, xmlstream
from twisted.words.xish import domish

from zope.interface import Interface, Attribute, implements
from keyring_storage import KeyringStorage

import argparse

from oauth2client import client, tools, file

#import json
#import webbrowser

#import httplib2
#import argparse

#from apiclient import discovery
#from oauth2client import client, tools, file
#from oauth2client.client import Storage

class XMPPAuthenticator(xmlstream.ConnectAuthenticator):
    """
    Initializes an XmlStream connecting to an XMPP server as a Client.

    This authenticator performs the initialization steps needed to start
    exchanging XML stanzas with an XMPP server as an XMPP client. It checks if
    the server advertises XML stream version 1.0, negotiates TLS (when
    available), performs SASL authentication, binds a resource and establishes
    a session.

    Upon successful stream initialization, the L{xmlstream.STREAM_AUTHD_EVENT}
    event will be dispatched through the XML stream object. Otherwise, the
    L{xmlstream.INIT_FAILED_EVENT} event will be dispatched with a failure
    object.

    After inspection of the failure, initialization can then be restarted by
    calling L{initializeStream}. For example, in case of authentication
    failure, a user may be given the opportunity to input the correct password.
    By setting the L{password} instance variable and restarting initialization,
    the stream authentication step is then retried, and subsequent steps are
    performed if succesful.

    @ivar jid: Jabber ID to authenticate with. This may contain a resource
               part, as a suggestion to the server for resource binding. A
               server may override this, though. If the resource part is left
               off, the server will generate a unique resource identifier.
               The server will always return the full Jabber ID in the
               resource binding step, and this is stored in this instance
               variable.
    @type jid: L{jid.JID}
    @ivar password: password to be used during SASL authentication.
    @type password: C{unicode}
    """

    namespace = 'jabber:client'

    def __init__(self, jid, password):
        xmlstream.ConnectAuthenticator.__init__(self, jid.host)
        self.jid = jid
        self.password = password


    def associateWithStream(self, xs):
        """
        Register with the XML stream.

        Populates stream's list of initializers, along with their
        requiredness. This list is used by
        L{ConnectAuthenticator.initializeStream} to perform the initalization
        steps.
        """
        xmlstream.ConnectAuthenticator.associateWithStream(self, xs)
        xs.initializers = [CheckVersionInitializer(xs)]
        inits = [ (xmlstream.TLSInitiatingInitializer, False),
                  (OAuth2InitiatingInitializer, True),
                  (BindInitializer, False),
                  (SessionInitializer, False),
                ]

        for initClass, required in inits:
            init = initClass(xs)
            init.required = required
            xs.initializers.append(init)
            

class OAuth2InitiatingInitializer(xmlstream.BaseFeatureInitiatingInitializer):
    """
    Stream initializer that performs SASL authentication.

    The supported mechanisms by this initializer are C{DIGEST-MD5}, C{PLAIN}
    and C{ANONYMOUS}. The C{ANONYMOUS} SASL mechanism is used when the JID, set
    on the authenticator, does not have a localpart (username), requesting an
    anonymous session where the username is generated by the server.
    Otherwise, C{DIGEST-MD5} and C{PLAIN} are attempted, in that order.
    """

    feature = (NS_XMPP_SASL, 'mechanisms')
    _deferred = None

    def setMechanism(self):
        """
        Select and setup authentication mechanism.

        Uses the authenticator's C{jid} and C{password} attribute for the
        authentication credentials. If no supported SASL mechanisms are
        advertized by the receiving party, a failing deferred is returned with
        a L{SASLNoAcceptableMechanism} exception.
        """

        jid = self.xmlstream.authenticator.jid
        password = self.xmlstream.authenticator.password

        mechanisms = get_mechanisms(self.xmlstream)
        if jid.user is not None:
            if 'X-OAUTH2' in mechanisms:
                self.mechanism = OAuth2(jid.user, jid.userhost())
                
            elif 'DIGEST-MD5' in mechanisms:
                self.mechanism = sasl_mechanisms.DigestMD5('xmpp', jid.host, None,
                                                           jid.user, password)
            elif 'PLAIN' in mechanisms:
                self.mechanism = sasl_mechanisms.Plain(None, jid.user, password)
            else:
                raise SASLNoAcceptableMechanism()
        else:
            if 'ANONYMOUS' in mechanisms:
                self.mechanism = sasl_mechanisms.Anonymous()
            else:
                raise SASLNoAcceptableMechanism()


    def start(self):
        """
        Start SASL authentication exchange.
        """

        self.setMechanism()
        self._deferred = defer.Deferred()
        self.xmlstream.addObserver('/challenge', self.onChallenge)
        self.xmlstream.addOnetimeObserver('/success', self.onSuccess)
        self.xmlstream.addOnetimeObserver('/failure', self.onFailure)
        self.sendAuth(self.mechanism.getInitialResponse())
        return self._deferred


    def sendAuth(self, data=None):
        """
        Initiate authentication protocol exchange.

        If an initial client response is given in C{data}, it will be
        sent along.

        @param data: initial client response.
        @type data: C{str} or C{None}.
        """
# <auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl"
#     mechanism="X-OAUTH2"
#     auth:service="oauth2"
#     xmlns:auth="http://www.google.com/talk/protocol/auth">
#   base64("\0" + user_name + "\0" + oauth_token)
# </auth>


        auth = domish.Element((NS_XMPP_SASL, 'auth'))
        auth['mechanism'] = self.mechanism.name
        auth['auth:service'] = "oauth2"
        auth['xmlns:auth'] = "http://www.google.com/talk/protocol/auth"
        
        if data is not None:
            auth.addContent(b64encode(data) or '=')
        self.xmlstream.send(auth)


    def sendResponse(self, data=''):
        """
        Send response to a challenge.

        @param data: client response.
        @type data: C{str}.
        """

        response = domish.Element((NS_XMPP_SASL, 'response'))
        if data:
            response.addContent(b64encode(data))
        self.xmlstream.send(response)


    def onChallenge(self, element):
        """
        Parse challenge and send response from the mechanism.

        @param element: the challenge protocol element.
        @type element: L{domish.Element}.
        """

        try:
            challenge = fromBase64(str(element))
        except SASLIncorrectEncodingError:
            self._deferred.errback()
        else:
            self.sendResponse(self.mechanism.getResponse(challenge))


    def onSuccess(self, success):
        """
        Clean up observers, reset the XML stream and send a new header.

        @param success: the success protocol element. For now unused, but
                        could hold additional data.
        @type success: L{domish.Element}
        """

        self.xmlstream.removeObserver('/challenge', self.onChallenge)
        self.xmlstream.removeObserver('/failure', self.onFailure)
        self.xmlstream.reset()
        self.xmlstream.sendHeader()
        self._deferred.callback(xmlstream.Reset)


    def onFailure(self, failure):
        """
        Clean up observers, parse the failure and errback the deferred.

        @param failure: the failure protocol element. Holds details on
                        the error condition.
        @type failure: L{domish.Element}
        """

        self.xmlstream.removeObserver('/challenge', self.onChallenge)
        self.xmlstream.removeObserver('/success', self.onSuccess)
        try:
            condition = failure.firstChildElement().name
        except AttributeError:
            condition = None
        self._deferred.errback(SASLAuthError(condition))
        
class OAuth2(object):
    """
    Implements the PLAIN SASL authentication mechanism.

    The PLAIN SASL authentication mechanism is defined in RFC 2595.
    """
    implements(ISASLMechanism)

    name = 'X-OAUTH2'

    def __init__(self, authcid, authjid):
        self.authcid = authcid or ''
        self.authjid = authjid or ''
        self.tokenGen =  OAuth2Token(self.authjid)


    def getInitialResponse(self):
        token = self.tokenGen.get_token()
        val = "\x00%s\x00%s" % (self.authcid.encode('utf-8'),
                                    token.encode('utf-8'))
        return val

class OAuth2Token:

  def __init__(self, login):
      self.login = login

  def get_token(self):
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
        'secret.json',
        scope='https://www.googleapis.com/auth/googletalk',
        redirect_uri='http://localhost:8080',
        login_hint=self.login)
      parser = argparse.ArgumentParser(parents=[tools.argparser])
      flags = parser.parse_args()

      credentials = tools.run_flow(flow, storage, flags, None)
      # TODO: add check of email address
      return credentials.access_token
  