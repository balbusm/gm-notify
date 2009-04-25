#!/usr/bin/env python

from distutils.core import setup

setup(  name='gm-notify',
        version='0.7',
        description='Highly Ubuntu 9.04 integrated GMail Notifier',
        author='Alexander Hungenberg',
        author_email='alexander.hungenberg@gmail.com',
        py_modules=['gmailatom', 'keyring'],
        scripts=['gm-notify.py', 'gm-notify-config.py'],
        data_files=[('/usr/share/applications', ['data/gm-notify.desktop']),
                    ('/usr/share/applications', ['data/gm-notify-config.desktop']),
                    ('/usr/share/gm-notify', ['data/checking.gif']),
                    ('/usr/share/locale/de/LC_MESSAGES', ['po/de/gm-notify.mo'])] )
