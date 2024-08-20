#!/usr/bin/env python3

import warnings
import sys
import os
import logging
import time

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
sys.path.append(current)

from tests.common import start_container, run_in_container, image_name

logger = logging.getLogger()

warnings.filterwarnings("ignore")


print("Starting test container")
platform = f"linux/{os.uname().machine}"
container_id = start_container(image_name, platform)
command = ['/bin/bash', '-c', 'test -f /demo/couchbase/.ready']
while not run_in_container(container_id, command):
    time.sleep(1)
command = ['cbcutil', 'list', '--host', '127.0.0.1', '--wait']
run_in_container(container_id, command)
time.sleep(1)
