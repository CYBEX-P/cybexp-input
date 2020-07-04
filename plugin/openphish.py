#!/usr/bin/env python3

from .common import *
import requests


FEED_URL = "https://openphish.com/feed.txt"


def inputCheck(args):
    return True


class InputPlugin(CybexSource):
    def fetch_and_post(self):

        self.logger.info(f"Retrieving events from OpenPhish at {FEED_URL}")
        response = requests.get(FEED_URL)

        if response.ok:

            text = response.text
            count = text.count('\n')
            self.logger.info(f"Retrieved {count} records from OpenPhish.")
            self.post_event_to_cybex_api(text)

        else:
            self.logger.error(
                "api.input.openphishSource.fetch -- \n\t" + response.reason
            )

