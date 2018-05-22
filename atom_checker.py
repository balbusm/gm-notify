#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# atom_checker.py v2.0
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
import time
from datetime import datetime
import argparse
from typing import List, Callable, Optional, NamedTuple

import requests
from requests import Session, Request, Response
from requests.auth import AuthBase

from apscheduler.schedulers.background import BackgroundScheduler

from oauth2client import client, tools
from oauth2client.client import Storage

from rx import Observer

import gm_log
from keyring_storage import KeyringStorage

AUTH_SCOPE = "https://mail.google.com/mail/feed/atom"
SECRET_LOCATION = "data/secret.json"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_AUTH_METHOD = "XOAUTH2"
IDLE_TIME = 3
IDLE_JOB_ID = 'idle'


class AtomChecker:

    def __init__(self, login: str, labels: List[str]=("Inbox",), interval: int = 60, avoid_logging_on_google_page: bool=False):
        self.login = login
        self.labels = labels
        self.interval = interval
        self.avoid_logging_on_google_page = avoid_logging_on_google_page
        self.scheduler = BackgroundScheduler()
        self.observer: Observer = None
        self.session: Session = None
        self.logger = gm_log.get_logger(__name__)

    def connect(self, observer: Observer) -> Callable:
        self.session = requests.session()
        self.observer = observer

        self.scheduler.add_job(self.__send_request,
                               'interval',
                               seconds=self.interval,
                               next_run_time=datetime.now(),
                               max_instances=1)
        self.scheduler.start()

        return self.stop

    def __send_request(self) -> None:
        if self.observer.is_stopped:
            self.logger.debug("Observer stopped. Ignoring send_request")
            return
        for label in self.labels:
            try:
                response = self.session.get("https://mail.google.com/mail/feed/atom/" + label,
                                            auth=OAuth2(self.login, self.avoid_logging_on_google_page))
                self.observer.on_next(AtomMessage(self.login, label, response))
            except Exception as ex:
                self.observer.on_error(ex)

    def stop(self) -> None:
        # rx.disposable cannot throw an exception as it it's swallowed
        try:
            self.logger.debug("Stopping atom checker...")
            self.scheduler.remove_all_jobs()
            self.scheduler.shutdown(wait=False)
            self.logger.debug("Stopping atom checker...Done")
        except Exception as ex:
            self.logger.exception("Exception during stopping", exc_info=ex)


class OAuth2(AuthBase):

    def __init__(self, login: str, only_local: bool=False):
        # setup any auth-related data here
        self.login = login
        self.only_local = only_local
        self.logger = gm_log.get_logger(__name__)

    def __call__(self, r:  Request) -> Request:
        # modify and return the request
        access_token = self.get_access_token()
        r.headers['Authorization'] = "Bearer " + access_token
        return r

    def get_access_token(self) -> str:
        storage = KeyringStorage(self.login)
        access_token = self.get_access_token_from_storage(storage)
        if access_token or self.only_local:
            return access_token

        # TODO: add check of email address
        return self.acquire_access_token(storage)

    def get_access_token_from_storage(self, storage: Storage) -> Optional[str]:
        credentials = storage.get()
        try:
            if credentials:
                return credentials.get_access_token().access_token
        except client.HttpAccessTokenRefreshError as ex:
            # refresh token expired go for authentication
            self.logger.warning("Cannot get access token", exc_info=ex)
            return None

    def acquire_access_token(self, storage: Storage):
        flow = client.flow_from_clientsecrets(
            SECRET_LOCATION,
            scope=AUTH_SCOPE,
            redirect_uri='http://localhost:8080',
            login_hint=self.login)
        parser = argparse.ArgumentParser(parents=[tools.argparser])
        flags = parser.parse_args()

        return tools.run_flow(flow, storage, flags).access_token


class AtomMessage(NamedTuple):
    account_name: str
    label: str
    response: Response
