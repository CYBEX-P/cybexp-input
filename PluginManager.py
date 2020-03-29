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


#local
import plugin
import logs
import database as db




loggerName = "PluginManager"
socketLocation = "/home/nacho/cybexp/inputs/"
API_CONFIG_FILE = "config.json"





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
        if exit_tries >= 3:
            sys.exit(0)
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
    if len(plugins_to_run) == 0: # do all 
        configs = inputDB.getValidConfig(select={"_id":0})
    else:
        configs = inputDB.getValidConfig(query={"input_plugin_name": { "$in": plugins_to_run}},select={"_id":0})
    
    return configs

def getValidPlugins():
    inputDB = db.InputDB()
    plugins = inputDB.getValidPlugins()
    return plugins
def setPID(conf_uuid, pid):
   inputDB = db.InputDB()
   return inputDB.setPID(conf_uuid, pid)
def getPID(conf_uuid):
   inputDB = db.InputDB()
   return inputDB.getPID(conf_uuid)

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






def verifyUUID(conf_uuid, sockLocation):
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

def updateSockConfig(sockLocation, config:str):
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

def spawnConfig(apiURL,apiToken,config_str:str): # call runOrUpdateConfig(), handles all cases
    try:
        config = json.loads(config_str)
        if 'uuid' not in config:
            return False
    except:
        return False


    command = ['python3', "PluginHandler.py", apiURL, apiToken, config_str]
    # print(command)
    process = subprocess.Popen(command)#, stdout=subprocess.STDOUT, stderr=subprocess.STDOUT)
    # process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid = process.pid
    print("New process at:",pid)
    setPID(config["uuid"],pid)
    return process

def restartSock(sock_loc):
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

def killSock(sock_loc):
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

def checkRunningConfig(config:str, socket_loc):
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

def runOrUpdateConfig(apiURL, apiToken, config:dict):
    global socketLocation

    if "uuid" not in config:
        print("FLAG 1")
        return False
    conf_uuid = config["uuid"]
    possible_pid = getPID(conf_uuid)

    sock_loc = socketLocation+str(possible_pid)+".sock"

    # try:
    config_str = json.dumps(config)
    # except:
    #     print("FLAG 2")

    #     return False

    if possible_pid:
        if verifyUUID(conf_uuid, sock_loc): # if running and at correct pid, else doesnt exist
            if checkRunningConfig(config_str, sock_loc):
                return possible_pid
            else:
                updateSockConfig(sock_loc, config_str)
                restartSock(sock_loc)
                return possible_pid # maintains same pid
        else:
            return spawnConfig(apiURL, apiToken, config_str).pid
    else:
        return spawnConfig(apiURL, apiToken, config_str).pid




def run_input_plugins(api_config_file, plugins_to_run: Collection[str] = {}):
    logger = logging.getLogger(loggerName)

    config_file = get_config_file(api_config_file)
    api_config = config_file["api_srv"]

    plugins_to_run = list(plugins_to_run) # getConfigs wants a list

    
    # print(list(configs))
    for input_config in getConfigs(plugins_to_run):
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

    # signal.signal(signal.SIGINT, signal_handler) # send signal to all threads
    # signal.signal(signal.SIGTERM, signal_handler) # send signal to all threads
    # signal.signal(signal.SIGUSR1, signal_handler) # send sig to threads, restart

    # print(args.plugins)
    startArgs = args.plugins # important to set global var



    run_input_plugins(API_CONFIG_FILE) 



    def handleChange(change):
        logger = logging.getLogger(loggerName)

        config_file = get_config_file(API_CONFIG_FILE)
        api_config = config_file["api_srv"]

        conf = change["fullDocument"]
        conf.pop("_id", None)
        conf_uuid = conf["uuid"]

        possible_pid = getPID(conf_uuid)
        sock_loc = socketLocation+str(possible_pid)+".sock"



        if change["operationType"] == "delete":
            if possible_pid:
                if verifyUUID(conf_uuid, sock_loc): # if running and at correct pid, else doesnt exist
                    killSock(sock_loc)
        if conf["enabled"] == True:
            # print(change["fullDocument"])
            pid = runOrUpdateConfig(api_config["url"], api_config["token"], conf)
            print(pid)
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


    a = db.InputDB()

    a.changeHandler(handleChange)

# DEFAULT_MONGO = "mongodb://192.168.1.101:30001,192.168.1.101:30002,192.168.1.101:30003/?replicaSet=rs0"

# client = pymongo.MongoClient(DEFAULT_MONGO)
# db = client["InputDB"]
# confCol = db["configs"]

# change_stream = confCol.watch()
# for change in change_stream:
#     print(change)
#     # print(json.dumps(change))
#     print('') # for readability only









# TODO
# add socket manager
# fix indents
# signal handler 
# error loggin
# print to loggin




# start
# update
# kill
# killall
# restart
# restartall
