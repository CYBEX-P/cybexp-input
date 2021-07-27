# CYBEX-P Input Module

Automatically collects threat data from different sources and 
posts them to _/raw_ endpoint of [CYBEX-API] (https://github.com/CYBEX-P/cybexp-api).


## Install

1. Install and run CYBEX-P API
2. Ensure `config.json` file is in




## Start or Run

Use the _input.py_ file to control the input module.

This file takes commands like start, stop, restart etc. and passes them
to the `run.py` file. The `run.py` file has an websocket in an infinite
loop. It is always listening for new commands. This file (`input.py`)
starts up, takes in a user command, passes that commands to `run.py`
and then shuts down.

This file takes in the arguments and passes them to `run.py`. The
`run.py` file parses those arguments. This file also parses the
arguments just to catch and return any user error.

The `input.py` file communicates (IPC) with the `run.py` file via a
websocket. The `run.py` files sets up a random websocket when it first
starts up. The websocket info (host, port, nonce) is saved in the
`runningconfig` file. `nonce` is like a password so that no one else
can pass commands to the `run.py` file except for the `input.py` file.

The `input.py` file reads the <host, port, nonce> from the file
`runningconfig`. The `runningconfig` file is stored in the working
directory which is ideally the same directory in which the `input.py`
and `run.py` files are. The `runningconfig` file also stores the
process ID of the `run.py` script, so that it can be monitored or
killed.

### Usage of ```input.py``` file

```
    usage: input.py [-h] [-c CONFIG] [-p PLUGIN [PLUGIN ...]]
    [-n NAME [NAME ...]] {start,stop,restart}

    Parse Input arguments.

    positional arguments:
      {start,stop,restart}  start, stop, restart

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG, --config CONFIG
                            config file path
      -p PLUGIN [PLUGIN ...], --plugin PLUGIN [PLUGIN ...]
                            plugin names to run
      -n NAME [NAME ...], --name NAME [NAME ...]
                            name of inputs to run
```



# notes 
https://stackoverflow.com/a/53229370/12044480


process object string 
https://stackoverflow.com/a/39742800/12044480



# TODO replace with JSON schema validation