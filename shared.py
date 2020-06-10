import configparser
import datetime
from distutils.util import strtobool
import os
import random
from recordclass import recordclass
import shutil
import sys
import time


def get_config():
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = 'config.ini'
    assert(os.path.exists(config_path))
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


CONFIG = get_config()

DRIVER_PATH = CONFIG['constant']['driver_path']
UPDATE_CACHE = bool(strtobool(CONFIG['constant']['update_cache']))
SEND_MESSAGE = bool(strtobool(CONFIG['constant']['send_message']))
CACHE_DIR = CONFIG['constant']['cache_dir']
CACHE_FILE = os.path.join(CACHE_DIR, 'ure.html')
CACHE_CHECKPOINT_DIR = os.path.join(CACHE_DIR, 'checkpoints')
DB_DIR = CONFIG['constant']['db_dir']
DB = os.path.join(DB_DIR, 'mls.db')
DB_CHECKPOINT_DIR = os.path.join(DB_DIR, 'checkpoints')
CHECKPOINT_COUNT = int(CONFIG['constant']['checkpoint_count'])


def get_params():
    params_path = CONFIG['constant']['params_file']
    assert (os.path.exists(params_path))
    params = configparser.ConfigParser()
    params.read(params_path)
    return params


PARAMS = get_params()

MLS = recordclass('MLS', ['mls_id',
                          'address',
                          'price',
                          'status',
                          'bedrooms',
                          'bathrooms',
                          'sqft',
                          'agent',
                          'open_house'])

ACTIVE = PARAMS['str']['active']
BACKUP_OFFER = PARAMS['str']['backup_offer']
UNDER_CONTRACT = PARAMS['str']['under_contract']
OFF_MARKET = PARAMS['str']['off_market']


def timestamp():
    return datetime.datetime.now().replace(microsecond=0).strftime('%y%m%dT%H%M%S')


CONST_TIMESTAMP = timestamp()
g_timestamp = timestamp()


def update_timestamp():
    global g_timestamp
    g_timestamp = timestamp()
    return g_timestamp


def sleep_norm_dist(mu, sigma, min):
    while True:
        random_number = random.normalvariate(mu, sigma)
        if random_number > min:
            break
    time.sleep(random_number)


def log_message(msg):
    log_path = os.path.join(CONFIG['constant']['log_dir'], '{}.txt'.format(CONST_TIMESTAMP))
    if type(msg) != str:
        msg = str(msg)
    full_msg = timestamp() + ' - ' + msg
    if os.path.exists(log_path):
        append_write = 'a'  # append if already exists
    else:
        append_write = 'w'  # make a new file if not
    with open(log_path, append_write) as log_file:
        log_file.write(full_msg + '\n')
    print(full_msg)


def remove_old_files(directory):
    checkpoint_files = sorted(os.listdir(directory), reverse=True)
    if len(checkpoint_files) > CHECKPOINT_COUNT:
        for old_file in checkpoint_files[CHECKPOINT_COUNT:]:
            os.remove(old_file)


def make_checkpoint(file, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    checkpoint_path = os.path.join(directory, g_timestamp)
    shutil.copy(file, checkpoint_path)
    remove_old_files(directory)
