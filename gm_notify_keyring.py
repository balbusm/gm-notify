__version__ = "$Revision: 14294 $"

import gtk # ensure that the application name is correctly set
import gnomekeyring as gkey


class Keyring(object):
    def __init__(self, name, server, protocol):
        self._name = name
        self._server = server
        self._protocol = protocol
        self._keyring = gkey.get_default_keyring_sync()
    
    def has_credentials(self):
        try:
            attrs = {"server": self._server, "protocol": self._protocol}
            items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
            return len(items) > 0
        except (gkey.DeniedError, gkey.NoMatchError):
            return False

    def get_credentials(self):
        attrs = {"server": self._server, "protocol": self._protocol}
        items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
        return (items[0].attributes["user"], items[0].secret)
    
    def delete_credentials(self):
        attrs = {"server": self._server, "protocol": self._protocol}
        try:
            items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
            for item in items:
                gkey.item_delete_sync(None, item.item_id)
        except (gkey.DeniedError, gkey.NoMatchError):
            pass
    
    def set_credentials(self, (user, pw)):
        attrs = {
                "user": user,
                "server": self._server,
                "protocol": self._protocol,
            }
        gkey.item_create_sync(gkey.get_default_keyring_sync(),
                gkey.ITEM_NETWORK_PASSWORD, self._name, attrs, pw, True)