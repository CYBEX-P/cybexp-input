#!/usr/bin/env python3
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Collection
import importlib
import inspect
import time
import signal

import plugin
import logs
import database as db



plugin_for_type = {
    "misp_api": plugin.misp_api.InputPlugin,
    "misp_file": plugin.misp_file.InputPlugin,
    "websocket": plugin.websocket.InputPlugin,
    "phishtank": plugin.phishtank.InputPlugin,
}

loggerName = "InputLogger"

exit_tries = 0
startArgs = dict()

def send_signals(threads, sig):
    for plg in threads:
        config = plg[0]
        thread = plg[1]
        # print(plg)
        thread.signal_handler(sig)

def signal_handler(sig,frame):
    global threads, exit_tries, startArgs
    print("\nhandled signal {}, {}".format(sig,frame))
    # print(threads.keys())
    if sig == signal.SIGINT or sig == signal.SIGTERM:
        print("EXIT TRIES:",exit_tries)
        exit_tries +=1
        signal_to_send = signal.SIGTERM
        if exit_tries >= 2:
            signal_to_send = signal.SIGKILL
        try:
            send_signals(threads,signal_to_send)
        except:
            pass
    elif sig == signal.SIGUSR1:
        print("recieved user signal 1: restating threads")
        send_signals(threads,signal.SIGTERM)
        time.sleep(1)
        threads = run_input_plugins(startArgs) 
        print("Done restarting")

    # sys.exit(0)

class NoSuchPlugin(Exception):
    pass


def getConfigs(plugins_to_run:list):
    inputDB = db.InputDB()
    configs = inputDB.getValidConfig(query={"input_plugin_name": { "$in": plugins_to_run}},select={"_id":0})
    return configs

def getValidPlugins():
    inputDB = db.InputDB()
    plugins = inputDB.getValidPlugins()
    return plugins

def checkPlugin(name):
    try:
        pluginName = "plugin.{}".format(name)
        # print(pluginName)
        plugin = importlib.import_module(pluginName)

        valid = 'InputPlugin' in inspect.getmembers(plugin)
        del plugin

        return valid

    except ModuleNotFoundError:
        print("Failed to import module")
        # print("Unexpected error:", sys.exc_info()[0])
        return False


def get_config_file(filename="../config.json"):
    with open(filename) as f:
        config_file = json.load(f)

    def validate(config_file):
        # Validate configuration for posting to Cybex-P API
        _api_srv = config_file["api_srv"]

        if (
            not _api_srv
            or not isinstance(_api_srv, dict)
            or ("url", "token") - _api_srv.keys()
        ):
            raise BadConfig("Couldn't find cybexp1 (app server) info in the config.")

        _input = config_file["input"]

        if not _input or not isinstance(_input, list):
            raise BadConfig(
                "Config doesn't have Cybex vulnerability source information."
            )

    validate(config_file)

    return config_file


def config_for_source_type(config_file, source_type, ndx=0):
    """ Get configuration from JSON for `source_type`. 

    Some source types can have multiple possible configs;
        disambiguate with an index.
    """

    i = 0
    for config in config_file["input"]:
        if config["input_plugin_name"] == source_type:
            if i == ndx:
                return config
            i += 1

    raise BadConfig(f"Didn't find the #{ndx} config for source type {source_type}")


def run_input_plugins(plugins_to_run: Collection[str]):
    logger = logging.getLogger(loggerName)

    config_file = get_config_file("config.json")
    api_config = config_file["api_srv"]

    plugins_to_run = list(plugins_to_run)

    
    # print(list(configs))
    threads = list() 
    for input_config in getConfigs(plugins_to_run):
        input_plugin_name = input_config["input_plugin_name"]
        try:
            pluginName = "plugin.{}".format(input_plugin_name)
            myplugin = importlib.import_module(pluginName)
            check = myplugin.inputCheck(input_config)
            if not check:
                logger.error("{} failed input check. This should NOT happen".format(pluginName))

        except ModuleNotFoundError:
            logger.error("Failed to import module, {}.".format(pluginName))
            continue

        try:
            # run the plugin 
            thread = plugin.common.CybexSourceFetcher(
                myplugin.InputPlugin(api_config, input_config)
            )
            thread.start()
            threads.append((input_config,thread))
        except:
            logger.error("Fail to run thread({}).".format(input_plugin_name))

        return threads

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # By default, run all input plugins
    parser.add_argument(
        "-p",
        "--plugins",
        nargs="+",
        help="Names of plugin types to run.",
        default=getValidPlugins(),
    )
    args = parser.parse_args()

    for p in args.plugins:
        if p not in getValidPlugins():
            raise NoSuchPlugin(f"{p} isn't a valid plugin.")

    # Set this up after argparse since it may be helpful to get those errors
    # back to stdout
    logfile = Path("/var/log/cybexp/input.log")

    print(f"Setting up logging to {logfile}")
    logfile.parent.mkdir(parents=True, exist_ok=True, mode=0o777)
    logfile.touch(exist_ok=True, mode=0o666)

    # logging.basicConfig(
    #     filename=logfile,
    #     level=logging.DEBUG,
    #     format=f"[{os.getpid()}] %(asctime)s %(levelname)s:%(message)s",
    # )
    
    logger = logging.getLogger(loggerName)
    formatter = logs.exformatter

    logs.setLoggerLevel(loggerName,logging.DEBUG)
    logs.setup_stdout(loggerName,formatter=formatter)
    logs.setup_file(loggerName,formatter=formatter,fileLoc=logfile)
    # logs.setup_email(loggerName,formatter=formatter,
    #     from_email='ignaciochg@gmail.com',
    #     to=['ignaciochg@nevada.unr.edu'],
    #     subject='Error found!',
    #     cred=('ignaciochg@gmail.com', 'qadytrsyudzkdidu'))

    logger.info("Starting CTI collector...")
    logger.info(f"Running the following plugins: {args.plugins}")

    signal.signal(signal.SIGINT, signal_handler) # send signal to all threads
    signal.signal(signal.SIGTERM, signal_handler) # send signal to all threads
    signal.signal(signal.SIGUSR1, signal_handler) # send sig to threads, restart

    print(args.plugins)
    startArgs = args.plugins # important to set global var

    threads = run_input_plugins(startArgs) 

    print(threads)
    print("All running")


