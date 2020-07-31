#!/usr/bin/env python3
"""Cybexp input module input.py."""

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
    parser = argparse.ArgumentParser(description='Parse arguments.')
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
            raise ValueError("input module is not running")

        this_dir = os.path.dirname(__file__)
        run_file = "run.py"
        run_file = os.path.join(this_dir, run_file)
        proc = subprocess.Popen([sys.executable, run_file])
        pid = proc.pid

        sock = socket.socket()
        starttime = time.time()
        while time.time() - starttime < 5:
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
            except (ConnectionRefusedError, OSError, ValueError):
                continue
                


    cmd = " ".join(map(shlex.quote, sys.argv[1:]))
    cmd = cmd.strip()
    cmd = f"{nonce} {cmd}"
    cmd = cmd.encode()

    sock.send(cmd)
    sock.close()


        
    
        

    



