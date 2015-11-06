from __future__ import print_function

__version__ = "$Revision: 14294 $"

from gi.repository import GnomeKeyring, Gtk
from collections import namedtuple
Credentials = namedtuple("Credentials", ["username", "password"])
Credentials.__new__.__defaults__ = ("", "")

def attributes(d):
    '''Converts a dictionary to a GnomeKeyring.Attribute array'''
    attrs = GnomeKeyring.Attribute.list_new()
    for key in d:
        GnomeKeyring.Attribute.list_append_string(attrs, key, str(d[key]))
    return attrs

def dict_from_attributes(attrs):
    '''Converts item results back into a dictionary'''
    result = {}
    for attr in GnomeKeyring.Attribute.list_to_glist(attrs):
        result[attr.name] = attr.get_string()
    return result

class KeyringException(Exception):
  pass

class Keyring(object):
    def __init__(self, name, server, protocol):
        self._name = name
        self._server = server
        self._protocol = protocol
        result, self._keyring = GnomeKeyring.get_default_keyring_sync()
    
    def has_any_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if result in (GnomeKeyring.Result.NO_MATCH, GnomeKeyring.Result.DENIED):
            return False
        return len(items) > 0

    def get_all_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if len(items) == 0:
            raise KeyringException("Credentials not found")
        credentials_list = []
        for item in items:
            d = dict_from_attributes(item.attributes)
            credentials_list.append(Credentials(d["user"], item.secret))
        return credentials_list
    
    def get_all_users(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if len(items) == 0:
            raise KeyringException("Credentials not found")
        users_list = []
        for item in items:
            d = dict_from_attributes(item.attributes)
            users_list.append(d["user"])
        return users_list
    
    def get_credentials(self, user):
        attrs = attributes({
                            "user" : user,
                            "server": self._server,
                            "protocol": self._protocol
                            })
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if len(items) == 0:
            raise KeyringException("Credentials not found")
        d = dict_from_attributes(items[0].attributes)
        return Credentials(d["user"], items[0].secret) 
    
    def delete_all_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        for item in items:
            GnomeKeyring.item_delete_sync(self._keyring, item.item_id)

    def delete_credentials(self, user):
        attrs = attributes({
                            "user": user,
                            "server": self._server,
                            "protocol": self._protocol
                            })
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        for item in items:
            GnomeKeyring.item_delete_sync(self._keyring, item.item_id)

    
    def set_credentials(self, user, pw):
        attrs = attributes({
                "user": user,
                "server": self._server,
                "protocol": self._protocol,
            })
        GnomeKeyring.item_create_sync(self._keyring,
                GnomeKeyring.ItemType.NETWORK_PASSWORD, self._name, attrs, pw, True)
