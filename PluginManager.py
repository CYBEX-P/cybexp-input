#!/usr/bin/env python3

import pymongo
import json 
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
import socket 
import sys
import subprocess
import threading

#local
import plugin
import logs
import database as db



# do not remove these, used as global vars
loggerName = "PluginManager"

# testing default locations 
# socketLocation = Path("/home/nacho/cybexp/inputs/")
# logfile = Path("/var/log/cybexp/inputManager.log")
# pluginlogfile = Path("/var/log/cybexp/plugin.log")

# production default locations
socketLocation = Path("/run/cybexp/inputs/")
logfile = Path("/var/log/cybexp/inputManager.log")
pluginlogfile = Path("/var/log/cybexp/plugin.log")
email_config = Path("/etc/cybexp/email.conf")



# def send_signals(threads, sig):
#     for plg in threads:
#         config = plg[0]
#         thread = plg[1]
#         # print(plg)
#         thread.signal_handler(sig)

def termSock(sockLocation:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
           sock.connect(sockLocation)
        except socket.error as msg:
            return False
        try:
            command = "sigterm\n".encode()
            sock.sendall(command)

            return True
        except:
            return False

def signal_handler_exit(sig,frame):
    global loggerName, exitEvent

    logger = logging.getLogger(loggerName)

    logger.info("Will terminate as soon as we can.")
    try:
        exitEvent.set()
    except:
        pass


def signal_handler_kill_sockets(sig,frame):
    global loggerName, socketLocation

    logger = logging.getLogger(loggerName)
    logger.info("Will send signals to all plugins.")

    for f in socketLocation.iterdir():
        if f.is_socket():
            termSock(str(f))
            logger.info("Signal {} sent to {}".format(sig , f))

def signal_handler(sig, frame):
    global loggerName

    logger = logging.getLogger(loggerName)
    logger.info("Signal {}, {} recieved.".format(sig,frame))
    
    if sig == signal.SIGTERM or sig == signal.SIGINT:
        signal_handler_exit(sig,frame)
    elif sig == signal.SIGUSR1: # kill all plugins as well
        signal_handler_kill_sockets(signal.SIGTERM, frame)
        signal_handler_exit(sig, frame)

class NoSuchPlugin(Exception):
    pass


def getConfigs(inputDB, plugins_to_run:list=[]):
    if len(plugins_to_run) == 0: # do all 
        configs = inputDB.getValidConfig(select={"_id":0})
    else:
        configs = inputDB.getValidConfig(query={"input_plugin_name": { "$in": plugins_to_run}},select={"_id":0})
    
    return configs

def getValidPlugins(inputDB):
    plugins = inputDB.getValidPlugins()
    return plugins
def setPID(conf_uuid:str, pid:int, inputDB):
   return inputDB.setPID(conf_uuid, pid)
def getPID(conf_uuid:str, inputDB):
   return inputDB.getPID(conf_uuid)

# def checkPlugin(name:str):
#     try:
#         pluginName = "plugin.{}".format(name)
#         # print(pluginName)
#         plugin = importlib.import_module(pluginName)

#         valid = 'InputPlugin' in inspect.getmembers(plugin)
#         del plugin

#         return valid

#     except ModuleNotFoundError:
#         # print("Failed to import module")
#         # print("Unexpected error:", sys.exc_info()[0])
#         return False


def get_api_config_file(filename:str ="api-config.json"):
    with open(filename) as f:
        try:
            config_file = json.load(f)
        except json.decoder.JSONDecodeError:
            logger.critical("Bad configuration on file {}".format(filename))
            sys.exit(1)

    def validate(config_file):
        # Validate configuration for posting to Cybex-P API
        _api_srv = config_file["api_srv"]

        if (
            not _api_srv
            or not isinstance(_api_srv, dict)
            or ("url", "token") - _api_srv.keys()
        ):
            raise BadConfig("Couldn't find cybexp1 (app server) info in the config.")

        # _input = config_file["input"]

        # if not _input or not isinstance(_input, list):
        #     raise BadConfig(
        #         "Config doesn't have Cybex vulnerability source information."
        #     )

    validate(config_file)

    return config_file


def getSockPID(sockLocation:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
           sock.connect(sockLocation)
        except socket.error as msg:
            return False
        try:
            command = "getpid\n".encode()
            sock.sendall(command)

            data = sock.recv(1024)
            data = data.decode().strip()
            try:
                pid = int(data)
                return pid
            except ValueError:
                return False
        except:
            return False



def verifyUUID(conf_uuid:str, sockLocation:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
           sock.connect(sockLocation)
        except socket.error as msg:
            return False
        try:
            command = "verifyuuid {}\n".format(conf_uuid).encode()
            sock.sendall(command)

            data = sock.recv(1024)
            data = data.decode().strip()
            if data == "True":
                return True
            else:
                return False
        except:
            return False

def updateSockConfig(sockLocation:str, config:str):
   with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
      try:
         sock.connect(sockLocation)
      except socket.error as msg:
         return False
      try:
         command = "chconfig {}\n".format(config).encode()
         sock.sendall(command)

         data = sock.recv(1024)
         data = data.decode().strip()
         if "ok." == data[:3]:
            return True
         else:
            return False
      except:
         return False

def spawnConfig(apiURL:str,apiToken:str,config_str:str, inputDB=None): # call runOrUpdateConfig(), handles all cases
    global socketLocation, pluginlogfile

    if inputDB:
        try:
            config = json.loads(config_str)
            if 'uuid' not in config:
                return False
        except:
            return False

    # using sys.executable to keep the virtual environment. {env}/bin/python3 uses the virtenv. else child vont use it
    command = [sys.executable, "PluginHandler.py", "--log-file", str(pluginlogfile), "-s", str(socketLocation) , apiURL, apiToken, config_str]

    # command = ['python3', "PluginHandler.py", "-s", str(socketLocation) , apiURL, apiToken, config_str]
    # print(command)
    process = subprocess.Popen(command)#, stdout=subprocess.STDOUT, stderr=subprocess.STDOUT)
    # process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid = process.pid
    # print("New process at:",pid)
    if inputDB:
        setPID(config["uuid"],pid, inputDB)
    return process

def restartSock(sock_loc:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(sock_loc)
        except socket.error as msg:
            return False
        try:
            command = "restart\n".encode()
            sock.sendall(command)

            resp = sock.recv(1024)
        except:
            pass

def killSock(sock_loc:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(sock_loc)
        except socket.error as msg:
            return False
        try:
            command = "sigterm\n".encode()
            sock.sendall(command)

            resp = sock.recv(1024)
        except:
            pass

def checkRunningConfig(config:str, socket_loc:str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(socket_loc)
        except socket.error as msg:
            return False
        try:
            command = "verifyrunningconfig {}\n".format(config).encode()
            sock.sendall(command)
 
            data = sock.recv(1024)
            data = data.decode().strip()
            if data == "True":
               return True
            else:
               return False
        except:
            return False

def runOrUpdateConfig(apiURL:str, apiToken:str, config:dict, inputDB=None):
    global socketLocation

    
    if inputDB:
        if "uuid" not in config:
        # print("FLAG 1")
            return False
        conf_uuid = config["uuid"]
        possible_pid = getPID(conf_uuid, inputDB)
    else:
        possible_pid = None

    sock_loc = str(socketLocation / "{}.sock".format(possible_pid))

    try:
        config_str = json.dumps(config)
    except:
        # print("FLAG 2")
        return False

    if possible_pid:
        if verifyUUID(conf_uuid, sock_loc): # if running and at correct pid, else doesnt exist
            if checkRunningConfig(config_str, sock_loc):
                return possible_pid
            else:
                updateSockConfig(sock_loc, config_str)
                restartSock(sock_loc)
                return possible_pid # maintains same pid
        else:
            return spawnConfig(apiURL, apiToken, config_str, inputDB).pid
    else:
        return spawnConfig(apiURL, apiToken, config_str, inputDB).pid




def run_input_plugins(api_config_file:str, inputDB, plugins_to_run: Collection[str] = []):
    global loggerName
    logger = logging.getLogger(loggerName)

    config_file = get_api_config_file(api_config_file)
    api_config = config_file["api_srv"]

    plugins_to_run = list(plugins_to_run) # getConfigs wants a list

    
    # print(list(configs))
    for input_config in getConfigs(inputDB, plugins_to_run):
        pid = runOrUpdateConfig(api_config["url"],api_config["token"],input_config, inputDB)
        if not pid:
            try:
                config_str = json.dumps(input_config)
            except:
                try:
                    config_str = str(input_config)
                except:
                    config_str = "ERROR"

            logger.error("Could not run configuration: {}".format(config_str))

        # runOrUpdateConfig()
        # input_plugin_name = input_config["input_plugin_name"]
        # try:
        #     pluginName = "plugin.{}".format(input_plugin_name)
        #     myplugin = importlib.import_module(pluginName)
        #     check = myplugin.inputCheck(input_config)
        #     if not check:
        #         logger.error("{} failed input check. This should NOT happen".format(pluginName))

        # except ModuleNotFoundError:
        #     logger.error("Failed to import module, {}.".format(pluginName))
        #     continue

        # try:
        #     # run the plugin 
        #     thread = plugin.common.CybexSourceFetcher(
        #         myplugin.InputPlugin(api_config, input_config)
        #     )
        #     thread.start()
        #     threads.append((input_config,thread))
        # except:
        #     logger.error("Fail to run thread({}).".format(input_plugin_name))

        # return threads

def getConfigsFromFile(filename:str ="plugin-config.json"):
    with open(filename) as f:
        try:
            config_file = json.load(f)
        except json.decoder.JSONDecodeError:
            logger.critical("Bad configuration on file {}".format(filename))
            sys.exit(1)
    if not isinstance(config_file, list):
        config_file = list()
    return config_file


def run_input_plugins_file(api_config_file:str, configs_filename:str):
    global loggerName
    logger = logging.getLogger(loggerName)

    config_file = get_api_config_file(api_config_file)
    api_config = config_file["api_srv"]

    
    # print(list(configs))
    for input_config in getConfigsFromFile(configs_filename):
        pid = runOrUpdateConfig(api_config["url"],api_config["token"],input_config)
        if not pid:
            try:
                config_str = json.dumps(input_config)
            except:
                try:
                    config_str = str(input_config)
                except:
                    config_str = "ERROR"

            logger.error("Could not run configuration: {}".format(config_str))

def handleChange(change, api_config_file:str, inputDB):
    global loggerName
    logger = logging.getLogger(loggerName)

    config_file = get_api_config_file(api_config_file)
    api_config = config_file["api_srv"]

    conf = change["fullDocument"]
    conf.pop("_id", None)
    conf_uuid = conf["uuid"]

    possible_pid = getPID(conf_uuid, inputDB)
    sock_loc = str(socketLocation / "{}.sock".format(possible_pid))



    if change["operationType"] == "delete":
        if possible_pid:
            if verifyUUID(conf_uuid, sock_loc): # if running and at correct pid, else doesnt exist
                killSock(sock_loc)
    if conf["enabled"] == True:
        # print(change["fullDocument"])
        pid = runOrUpdateConfig(api_config["url"], api_config["token"], conf, inputDB)
        # print(pid)
        if not pid:
            try:
                config_str = json.dumps(change)
            except:
                try:
                    config_str = str(change)
                except:
                    config_str = "ERROR"

            logger.error("Could not reconfigure change: {}".format(config_str))

    else: # if config was disabled then shut it off
        if possible_pid:
            if verifyUUID(conf_uuid, sock_loc): # if running and at correct pid, else doesnt exist
                killSock(sock_loc)



def removeStaleSockets():
    global socketLocation, loggerName

    logger = logging.getLogger(loggerName)

    for f in socketLocation.iterdir():
        if f.is_socket():
            pid = getSockPID(str(f)) 
            if not pid:
                try:
                    os.remove(str(f))
                    logger.info("removing stale UDS: "+str(f))
                except:
                    pass
          


if __name__ == "__main__":
    parser = argparse.ArgumentParser()


    parser.add_argument(
        "api_config_file",
        metavar="api-config-file",
        help="filename of JSON file containing API configuration. [api-config.conf]",
        default="api-config.conf",
    )
    parser.add_argument(
        "--config-file",
        help="filename of JSON file containing array of configs to run. Disables connection to databse and live update.",
        default=None,
    )
    # By default, run all input plugins
    parser.add_argument(
        "-p",
        "--plugins",
        nargs="+",
        help="Names of plugin types to run. Default runs all.",
        default=[],
    )
    parser.add_argument(
        '-r',
        '--remove-stale-sockets',
        help='Remove inactive UDS files before running.',
        action='store_true',
        default=False)
    parser.add_argument(
        '-s',
        '--socket-path',
        help="Location to search and spawn UDS. [{}]".format(socketLocation),
        default=str(socketLocation))
    parser.add_argument(
        '-l',
        '--log-file',
        help="File to store plugin manager's logs. [{}]".format(logfile),
        default=str(logfile))
    parser.add_argument(
        '--plugin-log-file',
        help="File to store plugin's logs. [{}]".format(pluginlogfile),
        default=str(pluginlogfile))
    parser.add_argument(
        '--email-config',
        help="File that stores email logging config. [{}]".format(email_config),
        default=None)
    args = parser.parse_args()


    socketLocation = Path(args.socket_path).resolve()
    socketLocation.mkdir(parents=True, exist_ok=True, mode=0o750)

    if not socketLocation.is_dir():
        parser.error("{} is not a direactory".format(socketLocation))

    # print(args)
    # sys.exit(0)



    # Set this up after argparse since it may be helpful to get those errors
    # back to stdout
    logfile = Path(args.log_file).resolve()
    pluginlogfile = Path(args.log_file).resolve()

    # print(f"Setting up logging to {logfile}")

    logfile.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    pluginlogfile.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    logfile.touch(exist_ok=True, mode=0o640)
    pluginlogfile.touch(exist_ok=True, mode=0o640)

    
    logger = logging.getLogger(loggerName)
    formatter = logs.exformatter

    logs.setLoggerLevel(loggerName,logging.DEBUG)
    logs.setup_stdout(loggerName,formatter=formatter)
    logs.setup_file(loggerName,formatter=formatter,fileLoc=str(logfile))
    if args.email_config:
        email_config = Path(args.email_config).resolve()
        logs.setup_email_from_file(srt(email_config),loggerName,formatter=formatter, level=logging.INFO, subject="Input Manager Error!")

    logger.info("Starting CTI collector...")

    if args.remove_stale_sockets:
        removeStaleSockets()
    logger.info(f"Running the following plugins: {args.plugins}")

    signal.signal(signal.SIGINT, signal_handler) # kill manager
    signal.signal(signal.SIGTERM, signal_handler) # kill manager
    signal.signal(signal.SIGUSR1, signal_handler) # kill all running plugings

    # print(args.plugins)


    if args.config_file:
        logger.info("Running Manager in offline mode (no DB).")
        run_input_plugins_file(args.api_config_file, args.config_file)
        exitEvent = threading.Event()
        exitEvent.wait()
        signal_handler_kill_sockets(signal.SIGUSR1, "")

    else:
        logger.info("Running Manager in online mode (w/ databse).")
        inputDB = db.InputDB(logger=logger)
        if len(args.plugins) > 0:
            for p in args.plugins:
                if p not in getValidPlugins(inputDB):
                    raise NoSuchPlugin(f"{p} isn't a valid plugin.")
            
        run_input_plugins(args.api_config_file, inputDB, args.plugins) 
        inputDB = db.InputDB()
        exitEvent = threading.Event()
        inputDB.changeHandler(handleChange,exitEvent, api_config_file=args.api_config_file, inputDB=inputDB)

    sys.exit(0)




# TODO
# add socket manager

