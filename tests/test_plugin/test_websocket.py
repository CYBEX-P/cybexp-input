"""unittests for run.py"""

import builtins
import pdb
import subprocess
import sys
import unittest
from unittest import mock

from tahoe.identity.config import WebSocketConfig

if __name__ != 'input.tests.plugin.test_websocket':
    import os, sys
    J = os.path.join
    sys.path = [J('..','..','..'), J('..','..',), '..'] + sys.path

from plugin import WebSocket

        
def setUpModule():
    # Start a websocket that hosts test data from testdata.json
    builtins.wssrv = subprocess.Popen([sys.executable, "wssrv.py"])

    builtins.input_config = WebSocketConfig(
        "Jay's Honeypot Amsterdam",
        "unr_honeypot",  #  change to cowrie
        "a441b15fe9a3cf56661190a0b93b9dec7d04127288cc8" \
             "7250967cf3b52894d11",
        "US/Pacific",
        "ws://134.122.58.51:5000/"
##        "ws://localhost:4042/"
    )

    builtins.api_config = {"url": "http://example.com/raw",
                           "token": "TestToken"}


def tearDownModule():
    wssrv.kill()


class FetchTest(unittest.TestCase):

    def test_01(self):
        thread = WebSocket(input_config.doc, api_config)
        events = thread.fetch()
        print(events)
        pdb.set_trace()
            
        
if __name__ == '__main__':
    unittest.main()
