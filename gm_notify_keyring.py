from __future__ import print_function

__version__ = "$Revision: 14294 $"

from gi.repository import GnomeKeyring, Gtk

def attributes(d):
  """Converts a dictionary to a GnomeKeyring.Attribute array"""
  attrs = GnomeKeyring.Attribute.list_new()
  for key in d:
    GnomeKeyring.Attribute.list_append_string(attrs, key, str(d[key]))
  return attrs

def dict_from_attributes(attrs):
  """Converts item results back into a dictionary"""
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
    
    def has_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if result in (GnomeKeyring.Result.NO_MATCH, GnomeKeyring.Result.DENIED):
            return False
        return len(items) > 0

    def get_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
        result, items = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if len(items) == 0:
            raise KeyringException("Credentials not found")
        d = dict_from_attributes(items[0].attributes)
        return (d["user"], items[0].secret)
    
    def delete_credentials(self):
        attrs = attributes({"server": self._server, "protocol": self._protocol})
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
