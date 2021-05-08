"""unittests for input.py"""

import asyncio
import builtins
import hashlib
import lomond
from lomond.persist import persist
import mock
import os
import pdb
import requests
import socket
import subprocess
import sys
import time
import unittest
import websockets

from tahoe import Instance, Attribute, Object
from tahoe.identity.config import InputConfig, WebSocketConfig
from tahoe.identity.backend import IdentityBackend, MockIdentityBackend
from tahoe.tests.identity.test_backend import setUpBackend, tearDownBackend

if __name__ != 'input.tests.test_input':
    import sys, os
    J = os.path.join
    sys.path = ['..', J('..','..'), J('..','..','..')] + sys.path
    del sys, os

        
def setUpModule():
    _backend = setUpBackend()
    Instance.set_backend(_backend)

    assert InputConfig._backend is Instance._backend
    assert WebSocketConfig._backend is Instance._backend
    assert isinstance(Instance._backend, (IdentityBackend,MockIdentityBackend))

    # Start a websocket that hosts test data from testdata.json
    builtins.wssrv = subprocess.Popen([sys.executable, "wssrv.py"])

    WebSocketConfig("Jay's Honeypot Amsterdam",
                    "unr_honeypot",  #  change to cowrie
                    "a441b15fe9a3cf56661190a0b93b9dec7d04127288cc8" \
                        "7250967cf3b52894d11",
                    "US/Pacific",
                    "ws://localhost:4042/"
                    )
                

##typetag = ['cowrie', 'apache']
##archive_preprocessors = ['aa', 'bb']


def tearDownModule():
    tearDownBackend(Instance._backend)
    wssrv.kill()


class ArgumentParserTest(unittest.TestCase):

    @mock.patch('requests.post')
    def test_01(self, post_mock):
        out = subprocess.Popen([sys.executable, "..\input.py", "start"])
        args, kwargs = post_mock.call_args
        pass

            
        
if __name__ == '__main__':
    unittest.main()
