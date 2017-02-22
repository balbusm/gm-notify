#!/usr/bin/env python
# -*- coding: utf-8 -*-
# worker.py v2.0
# Provides settins to GMail notify
#
# Copyright (c) 2017, Mateusz Balbus <balbusm@gmail.com>
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
import threading
import Queue

from gi.repository import GLib

class Worker:
    
#     @staticmethod
#     def call_on_main(funct):
#         return lambda *args, **kwargs : GLib.idle_add(funct, args, kwargs) 
    
    def __init__(self):
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self.work)
        self.thread.daemon = True
        self.running = False
    
    def start(self):
        self.running = True
        self.thread.start()
    
    def work(self):
        while self.running:
            item = self.queue.get()
            item()
            self.queue.task_done()
    
    def put(self, funct, *args, **kwargs):
        self.queue.put(lambda : funct(*args, **kwargs))
        
    def put_on_main(self, funct, *args, **kwargs):
        GLib.idle_add(funct, args, kwargs) 
        
    def stop(self):
        self.running = False
#         self.queue.join()
