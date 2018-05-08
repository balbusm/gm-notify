#!/usr/bin/env python
# -*- coding: utf-8 -*-
# gm_log.py v2.0
# Provides settins to GMail notify
#
# Copyright (c) 2018, Mateusz Balbus <mate_ob@yahoo.com>
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

# Open a connection in IDLE mode and wait for notifications from the
# server.

import logging

logging.basicConfig(level=logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger("gm_notify." + name)