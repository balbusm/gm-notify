#!/usr/bin/env python

from distutils.core import setup

setup(  name='gm-notify',
        version='0.10',
        description='Highly Ubuntu integrated GMail Notifier',
        author='Alexander Hungenberg',
        author_email='alexander.hungenberg@gmail.com',
        py_modules=['gtalk', 'keyring'],
        scripts=['gm-notify.py', 'gm-notify-config.py'],
        data_files=[('/usr/share/applications', ['data/gm-notify.desktop']),
                    ('/usr/share/applications', ['data/gm-notify-config.desktop']),
                    ('/usr/share/indicators/messages/applications', ['data/gm-notify']),
                    ('/usr/share/gm-notify', ['data/checking.gif']),
                    ('/usr/share/icons/hicolor/16x16/apps/', ['data/icons/hicolor/16x16/apps/gm-notify.png']),
                    ('/usr/share/icons/hicolor/48x48/apps/', ['data/icons/hicolor/48x48/apps/gm-notify.png']),
                    ('/usr/share/icons/hicolor/scalable/apps/', ['data/icons/hicolor/scalable/apps/gm-notify.svg']),
                    ('/usr/share/gm-notify', ['gm-config.glade']),
                    ('/usr/share/gm-notify', ['gm-notify-autostart.desktop']),
                    ('/etc/gconf/schemas', ['data/gm-notify.schemas']),
                    ('/usr/share/locale/da/LC_MESSAGES', ['po/da/gm-notify.mo']),
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
                    ('/usr/share/locale/sl/LC_MESSAGES', ['po/sl/gm-notify.mo']),] )
