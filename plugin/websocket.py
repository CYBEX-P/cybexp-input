#!/usr/bin/env python3
"""Websocket input plugin."""

import logging
import lomond
from lomond.persist import persist
import pdb
import time

from .common import InputPlugin

class WebSocket(InputPlugin):
    def __init__(self, input_config, api_config=None):
        self.url = input_config['data']['url'][0]
        self.ws = lomond.WebSocket(self.url)
        super().__init__(input_config, api_config)

    def fetch(self):
        events = []
        count = 0
        start = time.time()
        for event in persist(self.ws):
            if self.exit_graceful.is_set():
                break
            
            if event.name == "text":
                events.append(event.json)
                count += 1
            else:
                logging.info(event.name + " " + str(self))

            if count == 10:
                break
            if time.time() - start > 15:
                break

        self.ws.close()
        return events
            
