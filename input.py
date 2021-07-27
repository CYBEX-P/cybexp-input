"""
Use the `input.py` file to control the input module.

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

Usage
-----
::
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
"""

import argparse
import logging
import os
import pdb
import shlex
import socket
import subprocess
import sys
import time


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Parse Input arguments.')
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

    args = parser.parse_args()
    

    host, port, nonce = None, None, None
    try:
        with open('runningconfig', 'r') as f:
            host, port, nonce = f.readline().split(',')
            if host in ['0.0.0.0', 'localhost']:
                host = '127.0.0.1'
            port = int(port)
    except FileNotFoundError:
        pass

    sock = socket.socket()
    try:
        sock.connect((host, port))
    except (ConnectionRefusedError, OSError, TypeError):
        sock.close()
        
        if args.command != 'start':
            print("Input module is not running!")
            sys.exit(1)

        this_dir = os.path.dirname(__file__)
        run_file = os.path.join(this_dir, "run.py")
        proc = subprocess.Popen([sys.executable, run_file])
        pid = proc.pid

        sock = socket.socket()
        starttime = time.time()
        while time.time() - starttime < 5: # Allow run.py 5 seconds to create socket and start listening
            try:
                with open('runningconfig', 'r') as f:
                    host, port, nonce = f.readline().strip().split(',')
                    if host in ['0.0.0.0', 'localhost']:
                        host = '127.0.0.1'
                    port = int(port)
                sock.connect((host, port))

                with open('runningconfig', 'a') as f:
                    f.write(f"{pid}\n")
                break
            except (FileNotFoundError, ConnectionRefusedError,
                    OSError, ValueError):
                continue
                


    cmd = " ".join(map(shlex.quote, sys.argv[1:]))
    cmd = cmd.strip()
    cmd = f"{nonce} {cmd}"
    cmd = cmd.encode()

    sock.send(cmd)
    sock.close()


        
    
        

    



