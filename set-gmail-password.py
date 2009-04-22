#!/usr/bin/env python
# -*- coding: utf-8 -*-

# set-gmail-password.py v1
# stupid script to set gmail credentials in the gnome keyring
#
# Copyright (c) 2009, Alexander Hungenberg <alexander.hungenberg@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import sys
import keyring

if len(sys.argv) < 3:
    print "usage: set-gmail-password.py username password"
else:
    keys = keyring.Keyring("GMail", "mail.google.com", "http")
    keys.set_credentials((sys.argv[1], sys.argv[2]))
    print "success"

