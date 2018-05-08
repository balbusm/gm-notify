#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# dconf.py v2.0
# Binding with dconf client
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

import ctypes
from ctypes import Structure, POINTER, byref, c_char_p,  c_int, util

from typing import List


class DconfClient:
    def __init__(self):
        self.__dconf_client = _DCONF_LIB.dconf_client_new()

    def list(self, directory: str) -> List[str]:
        length_c = c_int()
        directory_p = c_char_p(directory.encode())
        result_list_c = _DCONF_LIB.dconf_client_list(self.__dconf_client, directory_p, byref(length_c))

        result_list = self.__decode_list(result_list_c, length_c.value)
        return result_list

    def __decode_list(self, list_to_decode_c, length):
        new_list = []
        for i in range(length):
            # convert to str and remove slash at the end
            decoded_str = list_to_decode_c[i].decode().rstrip("/")
            new_list.append(decoded_str)
        return new_list


class _DConfClient(Structure):
    _fields_ = []


_DCONF_LIB = ctypes.CDLL(util.find_library("dconf"))
_DCONF_LIB.dconf_client_new.argtypes = []
_DCONF_LIB.dconf_client_new.restype = POINTER(_DConfClient)
_DCONF_LIB.dconf_client_new.argtypes = []
_DCONF_LIB.dconf_client_list.argtypes = [POINTER(_DConfClient), c_char_p, POINTER(c_int)]
_DCONF_LIB.dconf_client_list.restype = POINTER(c_char_p)

