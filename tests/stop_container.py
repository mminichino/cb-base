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

from tests.common import get_container_id, stop_container

logger = logging.getLogger()

warnings.filterwarnings("ignore")


print("Starting test container")
print("Stopping test container")
container_id = get_container_id()
stop_container(container_id)
time.sleep(1)
