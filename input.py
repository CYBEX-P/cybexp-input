#!/usr/bin/env python3
"""Cybexp input module `main`."""

import argparse
import logging
import pdb
import signal
import time

from tahoe.identity import IdentityBackend

from loadconfig import get_identity_backend, get_apiconfig
from plugin import WebSocket


# Logging
##logging.basicConfig(filename = 'input.log') 
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s' \
    ' - %(funcName)() --  %(message)s'
    )


_NAME_TO_PLUGIN_MAP = {
    "websocket": WebSocket,
}

_ALL_THREAD = None
_NUM_EXIT_ATTEMPT = 0
_PLUGINS_TO_RUN = None
_BACKEND = get_identity_backend()


##def send_signals(_ALL_THREAD, sig):
##    for _, thread in _ALL_THREAD:
##        thread.signal_handler(sig)
##
##
##def signal_handler(sig, frame):
##    global _ALL_THREAD, _NUM_EXIT_ATTEMPT, _PLUGINS_TO_RUN
##    
##    logging.info(f"handled signal {sig}, {frame}")
##    
##    if sig in [signal.SIGINT, signal.SIGTERM]:
##        logging.info(f"# EXIT Attempt: {_NUM_EXIT_ATTEMPT}")
##        _NUM_EXIT_ATTEMPT +=1
##        
##        if _NUM_EXIT_ATTEMPT < 2:
##            signal_to_send = signal.SIGTERM
##        else:
##            signal_to_send = signal.SIGKILL
##
##        try:
##            send_signals(_ALL_THREAD, signal_to_send)
##        except:
##            pass
##    elif sig == signal.SIGUSR1:
##        logging.info("restating all input...")
##        send_signals(_ALL_THREAD, signal.SIGTERM)
##        time.sleep(1)
##        _ALL_THREAD = run_input_plugins(_PLUGINS_TO_RUN) 
##        logging.info("successfully restarted all input.")


def run_input_plugin(plugin_name_lst):
    api_config = get_apiconfig()
    
    _ALL_THREAD = list() 
    for input_config in _BACKEND.get_config(plugin_name_lst):
        plugin_name = input_config['data']['plugin'][0]
        try:
            Plugin = _NAME_TO_PLUGIN_MAP[plugin_name] 
            thread =  Plugin(input_config, api_config)
            thread.start()
            _ALL_THREAD.append((input_config, thread))
        except:
            logging.error("Fail to run thread({plugin_name}).")

        return _ALL_THREAD


if __name__ == "__main__":
        
    all_plugin = _BACKEND.get_all_plugin()
        
    parser = argparse.ArgumentParser()

    # By default, run all input plugins
    parser.add_argument(
        "-p",
        "--plugins",
        nargs="+",
        help="Plugins to run.",
        default=all_plugin,
    )
    args = parser.parse_args()

    for plugin_name in args.plugins:
        if plugin_name not in _NAME_TO_PLUGIN_MAP:
            raise NameError(f"invalid plugin: '{plugin_name}'")
        
##    signal.signal(signal.SIGINT, signal_handler) 
##    signal.signal(signal.SIGTERM, signal_handler) 
##    signal.signal(signal.SIGUSR1, signal_handler) 

    _PLUGINS_TO_RUN = args.plugins # important to set global var

    _ALL_THREAD = run_input_plugin(_PLUGINS_TO_RUN) 



