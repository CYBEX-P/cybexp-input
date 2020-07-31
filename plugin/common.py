#!/usr/bin/env python3
"""InputPlugin base class."""

import json
import logging
import random
import requests
import threading
import time

def exponential_backoff(n):
    s = min(3600, (2 ** n) + (random.randint(0, 1000) / 1000))
    time.sleep(s)


class InputPlugin(threading.Thread):
    """
    Base class for CYBEX-P Input Plugins.

    All plugins must inherit this class and implement the method
    ``fetch(self)``. See ``InputPlugin.fetch(self)`` for more.
    """
    
    timezone = 'UTC'
    post_url = ''
    token = ''
    delay = 0  # seconds_between_fetches
    
    def __init__(self, input_config, api_config=None):
        if api_config:
            self.post_url = api_config['url']
            self.token = api_config['token']
        self.name_ = input_config['data']['name'][0]
        self.plugin = input_config['data']['plugin'][0]
        self.orgid = input_config['data']['orgid'][0]
        self.typetag = input_config['data']['typetag'][0]
        self.timezone = input_config['data']['timezone'][0]
        if 'delay' in input_config['data']:
            self.delay = input_config['data']['delay'][0]
        
        self.exit_graceful = threading.Event()
        self.exit_now = threading.Event()
        super().__init__()


    def __str__(self):
        return (
            f"Cybexp input: post url = {self.post_url}, "
            f"name_ = {self.name_}, orgid = {self.orgid}, "
            f"typetag = {self.typetag}, timezone = {self.timezone}."
            )

    def fetch(self):
        """
        Fetch vulnerability data from this Cybex source.

        Each plugin class must implement this method.

        Returns
        -------
        events : dict or str or bytes or list
            If `events` is ``dict``, ``json.dumps(events)`` must not
            raise error. If `events` is ``list``, it may contain
            ``dict, str, bytes`` but nothing else. `events` cannot
            be empty.
        """
        
        raise NotImplementedError
    

    def post(self, events):
        """
        Post one or more events to the CYBEX-P API.

        Parameters
        ----------
        events : dict or str or bytes or list
            If `events` is `dict`, `json.dumps(events)` must not
            raise error. If `events` is `list`, it may contain
            `dict, str, or bytes` but nothing else. `events` cannot
            be empty.

        Returns
        -------
        api_response : list
            Response of API for posting each event.

        Notes
        -----
        General error-handling, including exponential backoff,
        is done in ``self.run()``.
        """

        if not events:
            return
        if not isinstance(events, list):
            events = [events]

        logging.info(f"posting '{len(events)}' events from '{self.name_}'")

        headers = {"Authorization": self.token}
        data = {'name': self.name_, 'orgid': self.orgid,
                'typetag': self.typetag, 'timezone': self.timezone}


        for i, e in enumerate(events):
            if self.exit_now.is_set():
                break
            
            if isinstance(e, dict):
                e = json.dumps(e)
            if isinstance(e, str):
                e = e.encode()
            elif isinstance(event, bytes):
                pass
            else:
                raise TypeError(f"events = '{type(events)}'")

            
            files = {'file': e}
            with requests.post(self.post_url, files=files,
                               headers=headers, data=data) as r:
                if r.status_code >= 400:
                    logging.error((
                        f"error posting: name = {self.name_}, "
                        f"status_code = '{r.status_code}', "
                        f"API response = '{r.content.decode()}'"))
                    raise Exception

                r.close() # redundant?


    def run(self):
        """
        Fetch and post events.
        
        Basically does the following::
            events = self.fetch()
            apis_response = self.post(events)

        Notes
        -----
        Does general error handling. Exponentially backs off (1hr max)
        if either ``self.fetch()`` or ``self.post()`` fails.
        """

        events = self.fetch()
        api_response = self.post(events)

        while True:
            if self.exit_graceful.is_set() or self.exit_now.is_set():
                break

            n_failed_fetch = 0
            while True:
                if self.exit_now.is_set():
                    break
                
                try:
                    events = self.fetch()
                    break
                except KeyboardInterrupt:
                    self.exit()
                except NotImplementedError:
                    logging.error("fetch() not implemented: '{self.plugin}'")
                    self.exit()
                except:
                    logging.error("error fetching '{self.name_}'", exc_info=True)
                    n_failed_fetch += 1

                if n_failed_fetch > 0:
                    exponential_backoff(n_failed_fetch)

            n_failed_post = 0
            while True:
                if self.exit_now.is_set():
                    break
            
                try:
                    api_response = self.post(events)
                    break
                except KeyboardInterrupt:
                    self.exit()
                except:
                    logging.error("error posting: '{self.name_}'", exc_info=True)
                    n_failed_post += 1

                if n_failed_post > 0:
                    exponential_backoff(n_failed_post)
        

    def exit_graceful(self):
        self.exit_graceful.set()
        
    def exit_now(self):
        self.exit_now.set()

        
        





        
