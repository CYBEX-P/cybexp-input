import os
import sys
import json
import socket
import signal
import logging 
import argparse
from pathlib import Path


# local
import database as db 
import plugin
import logs



# variables 
# socketLocation = "/run/cybexp/inputs/"
socketLocation = "/home/nacho/cybexp/inputs/"

loggerName = ""
logfile = Path("/var/log/cybexp/input.log")







# Exit codes 

# BAD_PLUGIN_NAME = 2
# BAD_CONFIG_NAME = 3







parser = argparse.ArgumentParser(description='Executes input plugin.')

parser.add_argument('apiURL', type=str,
                    help='URL of the api where data will be sent to. Do not include the path, it will be added internally.')
parser.add_argument('apiToken', type=str,
                    help='Token to authenticate with the api.')
parser.add_argument('config', type=str,
                    help='Configuration as json object, directly from DB. If invalid will return exit code BAD_CONFIG_NAME = 3')




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




def run_input_plugin( URL, token, config):
    logger = logging.getLogger(loggerName)

    api_config = {'url': URL, 'token': token}

    plugins_to_run = list(plugins_to_run)

    
    # print(list(configs))
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
            myplugin.InputPlugin(api_config, config)
        )
        runningPlugin.start()
        return runningPlugin
    except:
        logger.error("Fail to run thread({}).".format(input_plugin_name))
        sys.exit(1)





# commands
EXIT_COMMAND = -1

def commandHandler(data):
    global runningPlugin, args, pid

    response = ""

    if data == "exit":
        runningPlugin.signal_handler(signal.SIGTERM)
        return EXIT_COMMAND
    elif "help" in data:
        helpInfo = """Commands:
close\t\t\tend this connection
exit\t\t\tsend sigterm to plugin and exit
restart\t\t\trestart plugin, will use new settings if avalable
churl <new url>\t\tchange api url. restart required
chtoken <new token>\tchange api token. restart required
chconfig <new config>\tnew config to use
getconfig\t\treturns config
getpid\t\t\treturns pid
getuuid\t\t\treturns uuid of plugin config
verifyuuid <uuid>\treturns whether if input uuid is equal to the uuid of this current config
sigterm\t\t\tsend sigterm to plugin and exit
help\t\t\tthis help menu

"""
        return helpInfo
    elif data == "restart":
        runningPlugin.signal_handler(signal.SIGTERM)
        runningPlugin = run_input_plugin(args['apiURL'], args['apiToken'], args['config'])
        return "done\n"

    elif "chtoken" in data:
        splitData = data.split(' ')
        if len(splitData) == 2:
            args['apiToken'] = splitData[1]
            return "ok. New: {}\n".format(args['apiToken'])
        else:
            return "error\n"
    elif "churl" in data:
        splitData = data.split(' ')
        if len(splitData) == 2:
            args['apiURL'] = splitData[1]
            return "ok. New: {}\n".format(args['apiURL'])
        else:
            return "error\n"
    elif "chconfig" in data:
        splitData = data.split(' ', 1)
        if len(splitData) == 2:
            args['config'] = splitData[1]
            return "ok. New: {}\n".format(args['config'])
        else:
            return "error\n"
    elif data == "getconfig":
        return args['config']+"\n"
    elif data == "getpid":
        return str(pid)+"\n"
    elif data == "getuuid":
        try:
            return str(args['config']['uuid'])+"\n"
        except:
            return "error\n"
    elif "verifyuuid" in data:
        if len(splitData) == 2:
            try:
                isSame = str(args['config']['uuid']) == splitData[1]
                return str(isSame)+"\n"
            except:
                return "error\n"
        else:
            return "error\n"
    elif data == "sigterm":
        runningPlugin.signal_handler(signal.SIGTERM)
        return EXIT_COMMAND
    else:
        return "Not a command: {}\n".format(data)

    return response
# commands
# restart
# change token 
# change url
# change config
# get uuid 
# get config
# verify uuid # check if var equal this instance 
# term
# int
# kill 
# help
# get pid 


####################################
####### Initializing Logger ########
####################################


logfile.parent.mkdir(parents=True, exist_ok=True, mode=0o600)
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




####################################
###### Initial Checks & Inits ######
####################################

args = vars(parser.parse_args())
print(args)

try:
    os.makedirs(socketLocation)
except FileExistsError:
    if not os.path.isdir(socketLocation):
        logger.critical("Failed to create directoty {}, therefore can't create UDS. Will not start configuration {}".format(socketLocation,args['config']))
        sys.exit(1)

pid = str(os.getpid())
pid = "test"
server_address = socketLocation+pid+".sock"
print(pid,server_address)


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

runningPlugin = run_input_plugin(args['apiURL'], args['apiToken'], args['config'])

####################################
###### Post spawm handling #########
######       via UDS       #########
####################################


sock.listen(1) # max of 1, sinve we are not multithreading

while True:

    connection, client_address = sock.accept()
    try:
        print('connection from "{}"'.format(client_address))

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(1024).decode().strip()
            # print('received {!r}'.format(data))
            if data:
                # print('sending data back to the client')
                if data == "close":
                    break
                else:
                    resp = commandHandler(data)
                    print(resp)
                    print(args, pid)
                    if resp == EXIT_COMMAND:
                        connection.close()
                        sys.exit(0)
                    else:
                        connection.sendall(resp.encode())
            else:
                # print('no data from', client_address)
                break

    finally:
        connection.close()







# TODO 
# add signal handler
# make config into json object 

