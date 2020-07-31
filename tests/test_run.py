"""unittests for run.py"""

import builtins
import hashlib
import os
import subprocess
import pdb
import unittest

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
    

def tearDownModule():
    tearDownBackend(Instance._backend)


class ArgumentParserTest(unittest.TestCase):

    def test_01(self):
        out = os.popen("python ..\run.py").read()
        print(out)
        
if __name__ == '__main__':
    unittest.main()
