import configparser
import datetime
from distutils.util import strtobool
import os
import random
from recordclass import recordclass
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
CACHE_FILE = CONFIG['constant']['cache_file']
DB = CONFIG['constant']['db_file']


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


LOG_FILE = os.path.join(CONFIG['constant']['log_dir'], '{}.txt'.format(timestamp()))


def sleep_norm_dist(mu, sigma, min):
    while True:
        random_number = random.normalvariate(mu, sigma)
        if random_number > min:
            break
    time.sleep(random_number)


def log_message(msg):
    if type(msg) != str:
        msg = str(msg)
    full_msg = timestamp() + ' - ' + msg
    if os.path.exists(LOG_FILE):
        append_write = 'a'  # append if already exists
    else:
        append_write = 'w'  # make a new file if not
    with open(LOG_FILE, append_write) as log_file:
        log_file.write(full_msg + '\n')
    print(full_msg)
