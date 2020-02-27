#!/usr/bin/env python3
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Collection

import plugin
import logs
import database as db
import importlib

plugin_for_type = {
    "misp_api": plugin.misp_api.input_plugin,
    "misp_file": plugin.misp_file.input_plugin,
    "websocket": plugin.websocket.input_plugin,
    "phishtank": plugin.phishtank.input_plugin,
}

loggerName = "InputLogger"

class NoSuchPlugin(Exception):
    pass


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
    config_file = get_config_file("config.json")
    api_config = config_file["api_srv"]

    plugins_to_run = list(plugins_to_run)

    inputDB = db.InputDB()
    configs = inputDB.getConfig(query={"input_plugin_name": { "$in": plugins_to_run}},select={"_id":0})
    # print(list(configs))

    for input_config in configs:
        input_plugin_name = input_config["input_plugin_name"]
        try:
            pluginName = "plugin.{}".format(input_plugin_name)
            myplugin = importlib.import_module(pluginName)
            check = myplugin.inputCheck(input_config)
            if not check:
                self.logger.error("{} failed input check. This should NOT happen".format(pluginName))

        except ModuleNotFoundError:
            self.logger.error("Failed to import module, {}.".format(pluginName))
            continue

        # run the plugin 
        plugin.common.CybexSourceFetcher(
            myplugin.input_plugin(api_config, input_config)
        ).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # By default, run all input plugins
    parser.add_argument(
        "-p",
        "--plugins",
        nargs="+",
        help="Names of plugin types to run.",
        default=plugin_for_type.keys(),
    )
    args = parser.parse_args()

    for p in args.plugins:
        if p not in plugin_for_type:
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
    logs.setup_file(loggerName,formatter=formatter,fileLoc=logfile)
    # logs.setup_email(loggerName,formatter=formatter,
    #     from_email='ignaciochg@gmail.com',
    #     to=['ignaciochg@nevada.unr.edu'],
    #     subject='Error found!',
    #     cred=('ignaciochg@gmail.com', 'qadytrsyudzkdidu'))

    logger.info("Starting CTI collector...")
    logger.info(f"Running the following plugins: {args.plugins}")

    run_input_plugins(args.plugins)
