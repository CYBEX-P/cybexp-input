#!/usr/bin/env python3

import bz2, gzip

from .common import *

URL = "http://data.phishtank.com/data/"
COMPRESS_ALGO = ".bz2"  # need '.' for string fmt

decompress_algos = {".bz2": bz2.decompress, ".gz": gzip.decompress}

def inputCheck(args):
    check_a = "seconds_between_fetches" in args
    return check_a


class InputPlugin(CybexSource):
    def fetch_and_post(self):
        logging.info(f"Retrieving events from Phishtank at {URL}")
        response = requests.get(
            f"{URL}/{self.phishtank_api_key}/online-valid.json{COMPRESS_ALGO}"
        )

        if "exceeded the request rate limit" in response.text:
            return
        if COMPRESS_ALGO:
            logging.info(
                f"Decompressing API response from Phishtank with {COMPRESS_ALGO}"
            )
            print(response.content)
            text = decompress_algos[COMPRESS_ALGO](response.content)
        else:
            text = response.text

        events = json.loads(text)
        logging.info(f"Retrieved {len(events)} records from PhishTank.")
        self.post_event_to_cybex_api(events)
