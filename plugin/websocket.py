#!/usr/bin/env python3
"""Websocket input plugin."""

import jsons
import lomond
import requests


class WebSocket:
    def __init__(self, input_config, api_config=None):
        if api_config:
            self.post_url = api_config['url']
            self.token = api_config['token']

        self.url = input_config['data']['url'][0]
        self.ws = lomond.WebSocket(self.url)

        self.name = input_config['data']['name'][0]
        self.orgid = input_config['data']['orgid'][0]
        self.typetag = input_config['data']['typetag'][0]
        self.timezone = input_config['data']['timezone'][0]

    def fetch_and_post(self):
        for event in lomond.persist(self.ws):
            if event.name == "text":
                event = event.json
                files = {'file': event.encode()}
                headers = {'Authorization': self.token}

                requests.post(
                    self.post_url,
                    files=files,
                    headers=headers,
                    data={
                        'name': self.name,
                        'orgid': self.orgid,
                        'typetag': self.typetag,
                        'timezone': self.timezone
                        }
                
