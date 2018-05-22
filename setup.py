#!/usr/bin/env python3

from distutils.core import setup

setup(name='gm-notify',
      version='2.0.0',
      description='Highly Ubuntu integrated GMail Notifier',
      author='Mateusz Balbus',
      author_email='balbusmg@gmail.com',
      py_modules=['__version'
                  'account_config',
                  'account_settings_provider',
                  'atom_checker'
                  'dconf',
                  'gm_log'
                  'gm_notify_keyring',
                  'keyring_storage'],
      scripts=['gm-notify', 'gm-notify-config'],
      data_files=[('/usr/share/applications', ['data/gm-notify-config.desktop']),
                  ('/usr/share/applications', ['data/gm-notify.desktop']),
                  ('/usr/share/gm-notify', ['data/checking.gif']),
                  ('/usr/share/gm-notify', ['data/notification-message-email.svg']),
                  ('/usr/share/gm-notify', ['data/secret.json']),
                  ('/usr/share/gm-notify', ['gm-config.ui']),
                  ('/usr/share/gm-notify', ['gm-list.ui']),
                  ('/usr/share/glib-2.0/schemas', ['data/net.launchpad.gm-notify.gschema.xml']),
                  ('/usr/share/locale/da/LC_MESSAGES', ['po/da/gm-notify.mo']),
                  ('/usr/share/locale/bg/LC_MESSAGES', ['po/bg/gm-notify.mo']),
                  ('/usr/share/locale/de/LC_MESSAGES', ['po/de/gm-notify.mo']),
                  ('/usr/share/locale/ca/LC_MESSAGES', ['po/ca/gm-notify.mo']),
                  ('/usr/share/locale/el/LC_MESSAGES', ['po/el/gm-notify.mo']),
                  ('/usr/share/locale/es/LC_MESSAGES', ['po/es/gm-notify.mo']),
                  ('/usr/share/locale/fr/LC_MESSAGES', ['po/fr/gm-notify.mo']),
                  ('/usr/share/locale/he/LC_MESSAGES', ['po/he/gm-notify.mo']),
                  ('/usr/share/locale/hu/LC_MESSAGES', ['po/hu/gm-notify.mo']),
                  ('/usr/share/locale/it/LC_MESSAGES', ['po/it/gm-notify.mo']),
                  ('/usr/share/locale/nl/LC_MESSAGES', ['po/nl/gm-notify.mo']),
                  ('/usr/share/locale/pl/LC_MESSAGES', ['po/pl/gm-notify.mo']),
                  ('/usr/share/locale/pt/LC_MESSAGES', ['po/pt/gm-notify.mo']),
                  ('/usr/share/locale/pt_BR/LC_MESSAGES', ['po/pt_BR/gm-notify.mo']),
                  ('/usr/share/locale/ro/LC_MESSAGES', ['po/ro/gm-notify.mo']),
                  ('/usr/share/locale/ru/LC_MESSAGES', ['po/ru/gm-notify.mo']),
                  ('/usr/share/locale/sk/LC_MESSAGES', ['po/sk/gm-notify.mo']),
                  ('/usr/share/locale/sl/LC_MESSAGES', ['po/sl/gm-notify.mo'])])
