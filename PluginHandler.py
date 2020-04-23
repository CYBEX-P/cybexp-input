import os
import sys
import json
import socket
import signal
import logging 
import argparse
from pathlib import Path
import threading
import importlib

# local
import database as db 
import plugin
import logs



# variables 
socketLocation = Path("/run/cybexp/inputs/")
# socketLocation = Path("/home/nacho/cybexp/inputs/")

loggerName = "PluginHandler"
logfile = Path("/var/log/cybexp/plugin.log")

# info https://pymotw.com/3/socket/uds.html


# Exit codes 

# BAD_PLUGIN_NAME = 2
# BAD_CONFIG_NAME = 3


#gobal var
DRY_RUN = False

parser = argparse.ArgumentParser(description='Executes input plugin.')

parser.add_argument('apiURL', type=str,
                    help='URL of the api where data will be sent to. Do not include the path, it will be added internally.')
parser.add_argument('apiToken', type=str,
                    help='Token to authenticate with the api.')
parser.add_argument('config', type=str,
                    help='Configuration as json object, directly from DB. If invalid will return exit code BAD_CONFIG_NAME = 3')
parser.add_argument(
    '-s',
    '--socket-path',
    help="Location to search and spawn UDS. [{}]".format(socketLocation),
    default=str(socketLocation))
parser.add_argument(
    "-d",
    "--dry-run",
    help="enable dry run mode. configuration will not be executed.",
    action='store_true',
    default=False
    )
parser.add_argument(
    '-l',
    '--log-file',
    help="File to store plugin manager's logs. [{}]".format(logfile),
    default=str(logfile))

def signal_handler(signal,frame):
    global loggerName

    logger = logging.getLogger(loggerName)
    logger.debug("Signal {} recieved.".format(signal))
    exit_handler()

def exit_handler():
    global runningPlugin, connection
    try:
        runningPlugin.signal_handler(signal.SIGTERM)
    except:
        pass
    try:
        connection.close()
    except:
        pass
    sys.exit(0)


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




def run_input_plugin( URL:str, token:str, config:str):
    global DRY_RUN, loggerName

    logger = logging.getLogger(loggerName)

    api_config = {'url': URL, 'token': token}

    
    # print(list(configs))
    if not DRY_RUN:
        try:
            config = json.loads(config)
            input_plugin_name = config["input_plugin_name"]
        except json.decoder.JSONDecodeError:
            logger.critical("Can not initiate plugin with bad configuration: {}".format(config))
            sys.exit(1)
        try:
            pluginName = "plugin.{}".format(input_plugin_name)
            myplugin = importlib.import_module(pluginName)
            check = myplugin.inputCheck(config)
            if not check:
                logger.critical("{} failed input check. This should NOT happen".format(pluginName))
                sys.exit(1)

        except ModuleNotFoundError:
            logger.critical("Failed to import module, {}.".format(pluginName))
            sys.exit(1)

        try:
            # run the plugin 
            runningPlugin = plugin.common.CybexSourceFetcher(
                myplugin.InputPlugin(api_config, config, loggername=loggerName),
                loggername=loggerName
            )
            if not DRY_RUN:
                runningPlugin.start()
            return runningPlugin
        except:
            logger.error("Fail to run thread({}).".format(input_plugin_name))
            sys.exit(1)

    else:
        return None



EXIT_COMMAND = -1

def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj

def commandHandler(data):
    global runningPlugin, args, pid

    response = ""

    if data == "exit":
        try:
            runningPlugin.signal_handler(signal.SIGTERM)
        except:
            pass
        return EXIT_COMMAND
    elif "help" in data:
        helpInfo = """Commands:
close\t\t\t\tend this connection
exit\t\t\t\tsend sigterm to plugin and exit
restart\t\t\t\trestart plugin, will use new settings if avalable
churl <new url>\t\t\tchange api url. restart required
chtoken <new token>\t\tchange api token. restart required
chconfig <new config>\t\tnew config to use
getconfig\t\t\treturns config
getpid\t\t\t\treturns pid
getuuid\t\t\t\treturns uuid of plugin config
verifyuuid <uuid>\t\treturns whether if input uuid is equal to the uuid of this current config
sigterm\t\t\t\tsend sigterm to plugin and exit
verifyrunningconfig <config>\t\tcheck if config if running in this process
help\t\t\tthis help menu

"""
        return helpInfo
    elif data == "restart":
        try:
            runningPlugin.signal_handler(signal.SIGTERM)
        except NameError:
            pass
        runningPlugin = run_input_plugin(args['apiURL'], args['apiToken'], args['config'])
        return "done\n"

    elif "chtoken" in data:
        splitData = data.split(' ')
        if len(splitData) == 2:
            args['apiToken'] = splitData[1]
            return "ok. New: {}\n".format(args['apiToken'])
        else:
            return "error1\n"
    elif "churl" in data:
        splitData = data.split(' ')
        if len(splitData) == 2:
            args['apiURL'] = splitData[1]
            return "ok. New: {}\n".format(args['apiURL'])
        else:
            return "error2\n"
    elif "chconfig" in data:
        splitData = data.split(' ', 1)
        if len(splitData) == 2:
            args['config'] = splitData[1]
            return "ok. New: {}\n".format(args['config'])
        else:
            return "error3\n"
    elif data == "getconfig":
        return args['config']+"\n"
    elif data == "getpid":
        return str(pid)+"\n"
    elif data == "getuuid":
        try:
            conf = json.loads(args["config"])
            return str(conf['uuid'])+"\n"
        except:
            return "error4\n"
    elif "verifyuuid" in data:
        splitData = data.split(' ', 1)
        if len(splitData) == 2:
            try:
                uuidToCheck = splitData[1].strip()
                a = json.loads(args["config"])
                isSame = a['uuid'] == uuidToCheck
                return str(isSame)+"\n"
            except:
                return "error5\n"
        else:
            return "error6\n"
    elif data == "sigterm":
        try:
            runningPlugin.signal_handler(signal.SIGTERM)
        except NameError:
            pass
        return EXIT_COMMAND
    
    elif "verifyrunningconfig" in data:
        try:
            splitted = data.split(' ',1)
            configToCheck = splitted[1]
            a = json.loads(args["config"])
            b = json.loads(configToCheck)

            if ordered(a) == ordered(b):
                return "True\n"
            else:
                return "False\n"
        except:
            return "False\n"
    else:
        return "Not a command: {}\n".format(data)

    return response


####################################
####### Initializing Logger ########
####################################

args = vars(parser.parse_args()) # required step to edit this
# print(args)

logfile = Path(args["log_file"]).resolve()
pid = str(os.getpid())
loggerName = loggerName+str(pid)

logfile.parent.mkdir(parents=True, exist_ok=True, mode=0o600)
logfile.touch(exist_ok=True, mode=0o666)

logger = logging.getLogger(loggerName)
formatter = logs.exformatter

logs.setLoggerLevel(loggerName,logging.DEBUG)
logs.setup_stdout(loggerName,formatter=formatter)
logs.setup_file(loggerName,formatter=formatter,fileLoc=str(logfile))
# logs.setup_email(loggerName,formatter=formatter,
#     from_email='ignaciochg@gmail.com',
#     to=['ignaciochg@nevada.unr.edu'],
#     subject='Error found!',
#     cred=('ignaciochg@gmail.com', 'qadytrsyudzkdidu'))




####################################
###### Initial Checks & Inits ######
####################################


DRY_RUN = args["dry_run"]

socketLocation = Path(args["socket_path"]).resolve()
socketLocation.mkdir(parents=True, exist_ok=True, mode=0o750)

if not socketLocation.is_dir():
        logger.critical("{} not a direactory or failed to create it, therefore can't create UDS. Will not start configuration {}".format(socketLocation,args['config']))
        parser.error("{} is not a direactory".format(socketLocation))



# pid = "test"
server_address = str(socketLocation / "{}.sock".format(pid))
logger.info("New plugin, PID: {}, Loc: {}".format(pid,server_address))



# Make sure the socket does not already exist
try:
    os.unlink(server_address)
except OSError:
    if os.path.exists(server_address):
        logger.critical("Failed to create UDS {}. Could not clear location.".format(socketLocation,args['config']))
        sys.exit(1)

# Create a UDS socket
try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    logger.info('Starting UDS on {}'.format(server_address))
    sock.bind(server_address)
except:
    logger.critical("Failed to create UDS with config: {}. ".format(socketLocation,args['config']))
    sys.exit(1)


####################################
##### Initial Spawn of Plugin ######
####################################

# signal handlers defined here because after the thread is spun up we need to manage it, 
#  before this point we dont care if this process dies
signal.signal(signal.SIGINT, signal_handler) # send signal to all threads
signal.signal(signal.SIGTERM, signal_handler) # send signal to all threads

runningPlugin = run_input_plugin(args['apiURL'], args['apiToken'], args['config'])

####################################
###### Post spawm handling #########
######       via UDS       #########
####################################

sock.listen(1) # max of 1, since we are not multithreading this piece of code

while True:
    connection, client_address = sock.accept()
    try:
        while True:
            data = connection.recv(1024)
            if len(data) > 0: # also handles client disconnects (will return 0)
                while "\n" not in data.decode():
                    data = data + connection.recv(1024)
            data = data.decode().strip()
            if data:
                if data == "close":
                    break
                else:
                    resp = commandHandler(data)
                    logger.debug("resp: {}".format(resp))
                    logger.debug("{} {}".format(args, pid))
                    if resp == EXIT_COMMAND:
                        connection.close()
                        sys.exit(0)
                    else:
                        connection.sendall(resp.encode())
            else:
                break # close it
    except KeyboardInterrupt:
        exit_handler()
    finally:
        connection.close()



