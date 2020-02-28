#!/usr/bin/env python3
from .common import *

from pymisp import PyMISP

def inputCheck(args):
    print(args)
    check_a = isinstance(args["orgs"],list)
    check_b = "seconds_between_fetches" in args
    return check_a and check_b # and ....

class InputPlugin(CybexSource):
    def __init__(self, api_config, input_config):
        super().__init__(api_config, input_config)
        self.misp_orgs = input_config["orgs"]

    def fetch_and_post(self):
        for org in self.misp_orgs:
            # if self.backoffExit.is_set():
            #     break
            misp = PyMISP(self.misp_url, self.misp_key, self.misp_verifycert)
            relative_path = "events/restSearch"
            body = {
                "org": org,
                "withAttachments": "false",
                "returnFormat": "json",
            }
            r = misp.direct_call(relative_path, body)

            if "errors" in r.keys():
                logging.error(
                    "api.input.misp.MISPServerSource.fetch -- \n" + json.dumps(r, indent=4)
                )
            elif "response" in r.keys():
                self.post_event_to_cybex_api(r["response"])
            else:
                logging.error(
                    "api.input.misp.MISPServerSource.fetch -- \n" + json.dumps(r, indent=4)
                )
