#!/usr/bin/env python
# -*- coding: utf-8 -*-
# gscheduler.py v2.0
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

import sys

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.executors.base import BaseExecutor, run_job
from gi.repository import GLib


class GScheduler(BaseScheduler):
    """A scheduler that runs in a GTK+ event loop."""

    _timer = None
    _timeout_id = None
    _idle_id = None

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)

    def shutdown(self, *args, **kwargs):
        super().shutdown(*args, **kwargs)
        self._stop_timer()

    def _start_timer(self, wait_seconds):
        self._stop_timer()
        if wait_seconds is not None:
            self._timeout_id = GLib.timeout_add(wait_seconds * 1000, self._process_jobs)

    def _stop_timer(self):
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        if self._idle_id:
            GLib.source_remove(self._idle_id)
            self._idle_id = None

    def wakeup(self):
        self._stop_timer()
        GLib.idle_add(self._process_jobs)

    def _process_jobs(self):
        wait_seconds = super()._process_jobs()
        self._start_timer(wait_seconds)
        return False # cancel GTK job scheduling

    def _create_default_executor(self):
        return GExecutor()


class GExecutor(BaseExecutor):
    """
    Runs jobs in the GTK+ main thread.

    """

    def start(self, scheduler, alias):
        super().start(scheduler, alias)

    def _do_submit_job(self, job, run_times):
        def call_wrapper(job, jobstore_alias, run_times, logger_name):
            try:
                events = run_job(job, jobstore_alias, run_times, logger_name)
            except:
                self._run_job_error(job.id, *sys.exc_info()[1:])
            else:
                self._run_job_success(job.id, events)

        GLib.idle_add(call_wrapper, job, job._jobstore_alias, run_times, self._logger.name)