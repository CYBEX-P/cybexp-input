"""unittests for input.py"""

import asyncio
import builtins
import hashlib
import lomond
from lomond.persist import persist
import os
import pdb
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

        
def setUpModule():
    _backend = setUpBackend()
    Instance.set_backend(_backend)

    assert InputConfig._backend is Instance._backend
    assert WebSocketConfig._backend is Instance._backend
    assert isinstance(Instance._backend, (IdentityBackend, MockIdentityBackend))


    builtins.wssrv = subprocess.Popen([sys.executable, "wssrv.py"])


    WebSocketConfig("Jay's Honeypot Amsterdam",
                    "unr_honeypot",  #  change to cowrie
                    "a441b15fe9a3cf56661190a0b93b9dec7d04127288cc87250967cf3b52894d11",
                    "US/Pacific",
                    "ws://localhost:4042/"
                    )
                

##typetag = ['cowrie', 'apache']
##archive_preprocessors = ['aa', 'bb']


    
    

def tearDownModule():
    tearDownBackend(Instance._backend)
    wssrv.kill()


class ArgumentParserTest(unittest.TestCase):

    def test_01(self):

        out = subprocess.Popen([sys.executable, "..\input.py", "start"])
        time.sleep(20)
            
        
if __name__ == '__main__':
    unittest.main()
