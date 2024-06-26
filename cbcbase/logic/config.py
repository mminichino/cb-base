##
##

import os
import cbcbase.logic.constants as C


def get_base_dir():
    if 'CBC_CONFIG_DIR' in os.environ:
        return os.environ['CBC_CONFIG_DIR']
    else:
        return C.ROOT_DIRECTORY


def get_log_dir():
    if 'CBC_LOG_DIR' in os.environ:
        return os.environ['CBC_LOG_DIR']
    else:
        return C.LOG_DIRECTORY
