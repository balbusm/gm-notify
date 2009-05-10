#!/usr/bin/env python

from distutils.core import setup
import subprocess

setup(  name='gm-notify',
        version='0.9',
        description='Highly Ubuntu 9.04 integrated GMail Notifier',
        author='Alexander Hungenberg',
        author_email='alexander.hungenberg@gmail.com',
        py_modules=['gmimap', 'keyring', 'gmxdgsoundlib'],
        scripts=['gm-notify.py', 'gm-notify-config.py'],
        data_files=[('/usr/share/applications', ['data/gm-notify.desktop']),
                    ('/usr/share/applications', ['data/gm-notify-config.desktop']),
                    ('/usr/share/gm-notify', ['data/checking.gif']),
                    ('/usr/share/gm-notify', ['gm-config.glade']),
                    ('/etc/gconf/schemas', ['data/gm-notify.schemas']),
                    ('/usr/share/locale/da/LC_MESSAGES', ['po/da/gm-notify.mo']),
                    ('/usr/share/locale/de/LC_MESSAGES', ['po/de/gm-notify.mo']),
                    ('/usr/share/locale/ca/LC_MESSAGES', ['po/ca/gm-notify.mo'])] )
