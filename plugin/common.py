#!/usr/bin/env python3
"""InputPlugin base class."""

import json
import logging
import random
import requests
import threading
import time




class InputPlugin(threading.Thread):
    """
    Base class for all CYBEX-P Input Plugins.

    An input plugin fetches data from an input source. It then posts
    the fetched data to CYBEX-P API, specifically the `raw/` endpoint
    of the CYBEXP-API.

    All plugins must inherit this class and implement the method
    ``fetch()``. See the method ``fetch()`` for more. 

    Attributes
    ----------
    post_url : str
        URL of the CYBEX-P API 'raw' endpoint.
    token : str
        Bearer (JWT) token to authorize with API.
    name_ : str
        Human readable name and unique identifier.
    plugin : str
        Plugin name or type of plugin.

        Users can spin up two different instances of the same plugin.
        They will have different `name_` but same value for `plugin`.
        
        For example an `WebSocket` plugin fetches data from an URL.
        You can spin up two instances of the WebSocket plugin two
        bring data from two different URLs. Those two instances will
        have `plugin=websocket` but different values for `name_`.
    
    """
    
    def __init__(self, input_config, api_raw_url, api_token):
        self.post_url = api_raw_url
        self.token = "Bearer " + api_token
        self.name_ = input_config['data']['name'][0]
        self.plugin = input_config['data']['plugin'][0]
        self.orgid = input_config['data']['orgid'][0]
        self.typetag = input_config['data']['typetag'][0]
        self.timezone = input_config['data']['timezone'][0]
        try:
            self.period = input_config['data']['period'][0]
        except KeyError:
            self.period = 0     # wait seconds between fetches
        
        self.exit_graceful_event = threading.Event()
        self.exit_now_event = threading.Event()

        self.headers = {"Authorization": self.token}
        self.data = {'name': self.name_, 'orgid': self.orgid,
            'typetag': self.typetag, 'timezone': self.timezone}
        
        super().__init__()


    def __str__(self):
        return (
            f"CYBEX-P Input: post url = {self.post_url}, "
            f"name = {self.name_}, plugin = {self.plugin},"
            f"orgid = {self.orgid}, typetag = {self.typetag}, "
            f"timezone = {self.timezone}, period = {self.period}.")

    def exponential_backoff(self, n):
        s = min(3600, (2 ** n) + (random.randint(0, 1000) / 1000))
        self.exit_graceful_event.wait(s)

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


        for e in events:
            if self.exit_now_event.is_set():
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
                               headers=self.headers, data=self.data) as r:
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

        while True:
            if self.exit_graceful_event.is_set() or \
                    self.exit_now_event.is_set():
                break

            n_failed_fetch = 0
            while True:
                if self.exit_now_event.is_set():
                    break
                
                try:
                    events = self.fetch()
                    break
                except KeyboardInterrupt:
                    self.exit()
                except NotImplementedError:
                    logging.error("fetch() not implemented: '{self.plugin}'!")
                    self.exit()
                except:
                    logging.error("error fetching '{self.name_}'!",
                                  exc_info=True)
                    n_failed_fetch += 1

                if n_failed_fetch > 0:
                    self.exponential_backoff(n_failed_fetch)

            n_failed_post = 0
            while True:
                if self.exit_now_event.is_set():
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
                    self.exponential_backoff(n_failed_post)

            self.exit_graceful_event.wait(self.period)
        

    def exit_graceful(self):
        "Shutdown the input plugin gracefully."""
        
        self.exit_graceful_event.set()
        
    def exit_now(self):
        """Shutdown the input plugin immediately."""
        
        self.exit_graceful_event.set()
        self.exit_now_event.set()

        
        





        
