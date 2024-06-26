##
##

import os
import tempfile
import multiprocessing
from pathlib import Path

GLOBAL_LOCK = multiprocessing.Lock()

if os.access(Path.home(), os.W_OK):
    ROOT_DIRECTORY = os.path.join(Path.home(), '.config', 'cbcbase')
else:
    tmp_dir = tempfile.gettempdir()
    ROOT_DIRECTORY = os.path.join(tmp_dir, '.config', 'cbcbase')

LOG_DIRECTORY = os.path.join(ROOT_DIRECTORY, 'log')

GREY_COLOR = "\x1b[38;20m"
YELLOW_COLOR = "\x1b[33;20m"
RED_COLOR = "\x1b[31;20m"
BOLD_RED_COLOR = "\x1b[31;1m"
GREEN_COLOR = "\x1b[32;20m"
SCREEN_RESET = "\x1b[0m"
FORMAT_LEVEL = "%(levelname)s"
FORMAT_NAME = "%(name)s"
FORMAT_MESSAGE = "%(message)s"
FORMAT_LINE = "(%(filename)s:%(lineno)d)"
FORMAT_EXTRA = " [%(name)s](%(filename)s:%(lineno)d)"
FORMAT_TIMESTAMP = "%(asctime)s"
