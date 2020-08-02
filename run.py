"""Cybexp input module `run.py`."""

import argparse
import logging
import os
import pdb
import secrets
import socket
import sys
import time

from tahoe.identity import IdentityBackend

from loadconfig import get_identity_backend, get_apiconfig
from plugin import WebSocket


# Logging
logging.basicConfig(filename = 'input.log') 
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s' \
    ' - %(funcName)() --  %(message)s'
    )


_PLUGIN_CLASS_MAP = {
    "websocket": WebSocket,
}

_RUNNING = dict()
_CONFIG_FILENAME = 'config.json'
_BACKEND = None


def restart_input(plugin_lst=None, name_lst=None):
    stop_input(plugin_lst=None, name_lst=None)
    start_input(plugin_lst=None, name_lst=None)


def start_input(plugin_lst=None, name_lst=None):
    global _RUNNING
    
    try:
        api_config = get_apiconfig(_CONFIG_FILENAME)
    except:
        logging.error("can't load api config from config.json", exc_info=True)
        raise

    for input_config in _BACKEND.get_config(plugin_lst, name_lst):
        name = input_config['data']['name'][0]
        plugin = input_config['data']['plugin'][0]
        print(name)

        if name in _RUNNING:
            logging.info(f"input already running: '{name}'")
            continue
        
        try:
            Plugin = _PLUGIN_CLASS_MAP[plugin] 
            thread =  Plugin(input_config, api_config)
            thread.start()
            _RUNNING[name] = thread
        except:
            logging.error(f"failed to run input: '{name}'", exc_info=True)


def stop_input(plugin_lst=None, name_lst=None):
    global _RUNNING
    
    try:
        api_config = get_apiconfig(_CONFIG_FILENAME)
    except:
        logging.error("can't load api config from config.json", exc_info=True)
    
    for input_config in _BACKEND.get_config(plugin_lst, name_lst):
        name = input_config['data']['plugin'][0]
        plugin = input_config['data']['plugin'][0]
        
        if name not in _RUNNING:
            logging.info(f"input is not running: '{name}'")
            continue

        thread = _RUNNING[name]
        thread.exit_graceful()
        thread.join(3.0)
        if thread.is_alive():
            thread.exit_now()
        _ = _RUNNING.pop(name)
        

if __name__ == "__main__":
    sock = socket.socket()
    sock.bind(('', 0))
    sock.settimeout(5)
    host, port = sock.getsockname()
    nonce = secrets.token_hex(16)     
    with open("runningconfig", "w") as f:
        f.write(f"{host},{port},{nonce}\n")
    sock.listen()

    parser = argparse.ArgumentParser(description='Parse arguments.')
    parser.add_argument(
        'nonce')
    parser.add_argument(
        'command',
        default='start',
        choices = ['start', 'stop', 'restart'],
        help="start, stop, restart")
    parser.add_argument(
        '-c',
        '--config',
        default='config.json',
        help="config file path")
    parser.add_argument(
        "-p",
        "--plugin",
        nargs="+",
        help="plugin names to run",
    )
    parser.add_argument(
        "-n",
        "--name",
        nargs="+",
        help="name of inputs to run",
    )

              
    while True:
        try:
            r = sock.accept()[0] # vulnerability: if an attacker keeps sending wrong nonce continuously, we will be stuck here forever
            r = r.recv(4096)
            r = r.decode()
            r = r.split()

            args = parser.parse_args(r)

            if args.nonce != nonce:
                continue

            _CONFIG_FILENAME = args.config

            _BACKEND = get_identity_backend(_CONFIG_FILENAME)

            if args.plugin is None and args.name is None:
                all_plugin = _BACKEND.get_all_plugin()
                all_plugin = list(set(all_plugin))
                args.plugin = all_plugin

            if args.command == 'start':
                start_input(args.plugin, args.name)
            elif args.command == 'stop':
                stop_input(args.plugin, args.name)
                if not _RUNNING:
                    sock.close()
                    os.remove('runningconfig')
                    break
            elif args.command == 'restart':
                restart_input(args.plugin, args.name)
                

        except KeyboardInterrupt:
            break
        except socket.timeout:
            continue
        except:
            logging.error("unknown error", exc_info=True)
            


                


    



