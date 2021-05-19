"""
Cybexp input module `run.py`.

Use this script to interact with the input module including start/stop.
"""

import argparse
import logging
import os
import pdb
import secrets
import socket
import sys
import time

from tahoe.identity import IdentityBackend

from loadconfig import get_identity_backend, get_config
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

_RUNNING = dict()  # names of inputs running now
_API_CONFIG = None
_IDENTITY_BACKEND = None  # IdentityBackend


def configure(config_filename='config.json'):
    global _API_CONFIG, _IDENTITY_BACKEND
    
    _IDENTITY_BACKEND = get_identity_backend(config_filename)
    _API_CONFIG = get_config(config_filename, 'api')


def restart_input(plugin_lst=None, name_lst=None):
    stop_input(plugin_lst, name_lst)
    start_input(plugin_lst, name_lst)


def start_input(plugin_lst=None, name_lst=None):
    global _RUNNING, _API_CONFIG, _IDENTITY_BACKEND, _PLUGIN_CLASS_MAP

    if _API_CONFIG is None:
        raise ValueError("API config is None!")
    api_raw_url = _API_CONFIG['url'] + '/raw'

    all_input_config = _IDENTITY_BACKEND.get_config(plugin_lst, name_lst)

    for input_config in all_input_config:
        try:
            name = input_config['data']['name'][0]
            if name in _RUNNING:
                logging.info(f"Input already running: '{name}'!")
                continue
        except:
            logging.error(f"Failed to run input: '{input_config}'!",
                          exc_info=True)

        try:
            orgid = input_config['data']['orgid'][0]
            org = _IDENTITY_BACKEND.find_org(_hash=orgid, parse=True)
            if org is None:
                raise ValueError(f"Unknown orgid={orgid} for input name={name}!")

            api_token = org.token
        
        
            plugin = input_config['data']['plugin'][0]
            Plugin = _PLUGIN_CLASS_MAP[plugin]
            
            thread =  Plugin(input_config, api_raw_url, api_token)
            thread.start()

            _RUNNING[name] = thread
        except:
            logging.error(f"Failed to run input: '{name}'!", exc_info=True)


def stop_input(plugin_lst=None, name_lst=None):
    global _RUNNING, _IDENTITY_BACKEND
    
    all_input_config = _IDENTITY_BACKEND.get_config(plugin_lst, name_lst)

    for input_config in all_input_config:
        name = input_config['data']['name'][0]
        plugin = input_config['data']['plugin'][0]
        
        if name not in _RUNNING:
            logging.info(f"input is not running: '{name}'!")
            continue

        thread = _RUNNING[name]
        thread.exit_graceful()
        thread.join(3.0)
        if thread.is_alive():
            thread.exit_now()
        _ = _RUNNING.pop(name)


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'nonce')
    parser.add_argument(
        'command',
        default = 'start',
        choices = ['start', 'stop', 'restart', 'status'],
        help = "start, stop, restart, 'status'")
    parser.add_argument(
        '-c',
        '--config',
        default = 'config.json',
        help = "config file path")
    parser.add_argument(
        "-p",
        "--plugin",
        nargs = "+",
        help = "plugin names to run")
    parser.add_argument(
        "-n",
        "--name",
        nargs="+",
        help="name of inputs to run")

    return parser.parse_args(args)


def create_socket():
    sock = socket.socket()
    sock.bind(('', 0))
    sock.settimeout(5)
    sock.listen()
    host, port = sock.getsockname()
    nonce = secrets.token_hex(16)     
    with open("runningconfig", "w") as f:
        f.write(f"{host},{port},{nonce}\n")
    

    return sock, nonce
        
def main():
    global _IDENTITY_BACKEND
    
    sock, nonce = create_socket()

    while True:
        try:
            res = sock.accept()[0] # vulnerability: if an attacker keeps sending wrong nonce continuously, we will be stuck here forever
            res = res.recv(4096)
            res = res.decode()
            res = res.split()

            args = parse_args(res)

            if args.nonce != nonce:
                continue

            if _API_CONFIG is None:  # Only configure at startup
                configure(args.config)

            if args.plugin is None and args.name is None:
                all_plugin = _IDENTITY_BACKEND.get_all_plugin()
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
            elif args.command == 'status':
                print(_RUNNING)
                

        except KeyboardInterrupt:
            break
        except socket.timeout:
            continue
        except:
            logging.error("Unknown error!", exc_info=True)
    

if __name__ == "__main__": # debug
    main()

    
              
    
            


                


    



