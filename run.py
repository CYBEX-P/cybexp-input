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
    """
    Restarts the input systems. Calls stop_input() then start_input()

    Parameters
    ----------
    List of the plugins that will be passed to the identity backend object
        Default: NULL
    name_lst: List of Strings
        List of names of the files that will be used to input data for tahoe
        Default: NULL

    """
    stop_input(plugin_lst=None, name_lst=None)
    start_input(plugin_lst=None, name_lst=None)


def start_input(plugin_lst=None, name_lst=None):
    """
    Executes command to start an input thread.
    Retrieves the api configurations and checks for any current running inputs.
    Otherwise, a new input thread is executed and stored in global variable '_RUNNING'.

    Parameters
    ----------
    plugin_lst: List of Strings
        List of the plugins that will be passed to the identity backend object
        Default: NULL
    name_lst: List of Strings
        List of names of the files that will be used to input data for tahoe
        Default: NULL

    Raises
    ------
    Api Error
        raises a logging error with "can't api config from config.json" for improper api configurations in the json config file
    Input Error
        logs a 'run input error' with the name of the file.
        

    """
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
            Plugin = _PLUGIN_CLASS_MAP[plugin] #Assume it transfer Websocket
            thread =  Plugin(input_config, api_config)  #thread object
            thread.start() #start active input thread
            _RUNNING[name] = thread
        except:
            logging.error(f"failed to run input: '{name}'", exc_info=True)


def stop_input(plugin_lst=None, name_lst=None):
    """
    Executes commands to terminate the current Input Process.
    Checks first if there is a running process to terminate.
    Otherwise, the thread current running in '_RUNNING' is transferred and exitted gracefully.

    Parameters
    ----------
    plugin_lst: List of Strings
        List of the plugins that will be passed to the identity backend object
        Default: NULL
    name_lst: List of Strings
        List of names of the files that will be used to input data for tahoe
        Default: NULL

    Raises
    ------
    Api Error
        raises a logging error with "can't api config from config.json" for improper api configurations in the json config file
   


    """
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

            print('Input received')

            args = parser.parse_args(r)

            if args.nonce != nonce:
                continue

            _CONFIG_FILENAME = args.config

            #_BACKEND becomes a identity_backend object
            _BACKEND = get_identity_backend(_CONFIG_FILENAME)

            #check available plugins and retreive defaults
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
            elif args.command == 'status':
                pass
                

        except KeyboardInterrupt:
            break
        except socket.timeout:
            continue
        except:
            logging.error("unknown error", exc_info=True)
            


                


    



