"""unittests for run.py"""

import builtins
import multiprocessing
import pdb
import requests
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock
import websockets

from tahoe import Instance, Attribute, Object
from tahoe.identity.config import InputConfig, WebSocketConfig
from tahoe.identity.backend import IdentityBackend, MockIdentityBackend
from tahoe.tests.identity.test_backend import setUpBackend, tearDownBackend


if __name__ != 'input.tests.test_run':
    import os, sys
    J = os.path.join
    sys.path = ['..', J('..','..')] + sys.path

import run

        
def setUpModule():
    _backend = setUpBackend()
    Instance.set_backend(_backend)
    run._IDENTITY_BACKEND = _backend

    assert InputConfig._backend is Instance._backend
    assert WebSocketConfig._backend is Instance._backend
    assert run._IDENTITY_BACKEND is Instance._backend
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

    run._API_CONFIG = {"url": "http://example.com/raw", "token": "TestToken"}


def tearDownModule():
    tearDownBackend(Instance._backend)
    wssrv.kill()


class StartInputTest(unittest.TestCase):

    @mock.patch('run.start_input')
    def test_01(self, post_mock):
        post_mock.return_value.status_code = 247
        run.start_input('test')
        time.sleep(1)
##        run.stop_input()
        print(post_mock.call_args_list)
        args, kwargs = post_mock.call_args
        print(args, kwargs)
##        pdb.set_trace()
            
        
if __name__ == '__main__':
    unittest.main()
