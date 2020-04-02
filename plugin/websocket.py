#!/usr/bin/env python3
from .common import *

from lomond import WebSocket
from lomond.persist import persist

def inputCheck(args):
    return True

class InputPlugin(CybexSource):
    def __init__(self, api_config, input_config, loggername):
        super().__init__(api_config, input_config, loggername)
        self.ws = WebSocket(self.url)

    def __str__(self):
        return "Websocket input, orgid = {}, typtag = {}, timezone = {}, url = {}".format(
            self.orgid, self.archive_processing_typetag, self.timezone, self.url
        )

    def fetch_and_post(self):
        for event in persist(self.ws):
            if event.name == "text":
                rr = self.post_event_to_cybex_api(event.json)
                [
                    self.logger.exception(str(r[0]) + " " + r[1])
                    for r in rr
                    if not r[0] == 200
                ]
            else:
                self.logger.info(event.name + " " + str(self))
