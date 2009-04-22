#!/usr/bin/env python

from distutils.core import setup

setup(  name='gm-notify',
        version='0.5',
        description='Highly Ubuntu 9.04 integrated GMail Notifier',
        author='Alexander Hungenberg',
        author_email='alexander.hungenberg@gmail.com',
        py_modules=['gmailatom', 'keyring'],
        scripts=['gm-notify.py', 'set-gmail-password.py'],
        data_files=[('/usr/share/applications', ['data/gm-notify.desktop']),
                    ('/usr/share/locale/de/LC_MESSAGES', ['po/gm-notify-de.mo'])] )
