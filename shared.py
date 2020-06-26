from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

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
    print('Using config path {}'.format(os.path.join(os.getcwd(), config_path)))
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def get_params():
    params_path = CONFIG['constant']['params_file']
    assert (os.path.exists(params_path))
    params = configparser.ConfigParser()
    params.read(params_path)
    return params


CONFIG = get_config()
PARAMS = get_params()

DRIVER_PATH = CONFIG['constant']['driver_path']
UPDATE_CACHE = bool(strtobool(CONFIG['constant']['update_cache']))
SEND_MESSAGE = bool(strtobool(CONFIG['constant']['send_message']))
HEADLESS = bool(strtobool(CONFIG['constant']['headless']))
CACHE_DIR = CONFIG['constant']['cache_dir']
CACHE_CURRENT_DIR = os.path.join(CACHE_DIR, 'current')
CACHE_CHECKPOINT_DIR = os.path.join(CACHE_DIR, 'checkpoints')
DB_DIR = CONFIG['constant']['db_dir']
DB = os.path.join(DB_DIR, 'mls.db')
DB_CHECKPOINT_DIR = os.path.join(DB_DIR, 'checkpoints')
CHECKPOINT_COUNT = int(CONFIG['constant']['checkpoint_count'])
EXTENSIONS_DIR = CONFIG['search']['extensions_dir']

ACTIVE = PARAMS['str']['active']
BACKUP_OFFER = PARAMS['str']['backup_offer']
UNDER_CONTRACT = PARAMS['str']['under_contract']
OFF_MARKET = PARAMS['str']['off_market']
STATUSES = [ACTIVE, BACKUP_OFFER, UNDER_CONTRACT, OFF_MARKET]

SOURCE_URE = 'ure'
SOURCE_KSL = 'ksl'
CACHE_CURRENT_URE_DIR = os.path.join(CACHE_CURRENT_DIR, SOURCE_URE)
CACHE_CURRENT_KSL_DIR = os.path.join(CACHE_CURRENT_DIR, SOURCE_KSL)

MLS = recordclass('MLS', ['mls_id',
                          'address',
                          'price',
                          'status',
                          'bedrooms',
                          'bathrooms',
                          'sqft',
                          'agent',
                          'open_house',
                          'source'])


def make_dirs(directories):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)


make_dirs([CACHE_DIR, CACHE_CURRENT_DIR, CACHE_CHECKPOINT_DIR, DB_DIR, DB_CHECKPOINT_DIR, CACHE_CURRENT_URE_DIR, CACHE_CURRENT_KSL_DIR, EXTENSIONS_DIR])


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
            old_file_path = os.path.join(directory, old_file)
            if os.path.isdir(old_file_path):
                shutil.rmtree(old_file_path)
            else:
                os.remove(old_file_path)


def make_checkpoint(file, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    checkpoint_path = os.path.join(directory, g_timestamp)
    if os.path.isdir(file):
        shutil.copytree(file, checkpoint_path)
    else:
        shutil.copy(file, checkpoint_path)
    remove_old_files(directory)


def wait_for_element(web_driver, xpath, timeout=60):
    return WebDriverWait(web_driver, timeout).until(
        expected_conditions.presence_of_element_located((By.XPATH, xpath)))


def wait_for_visible(web_driver, element, timeout=60):
    WebDriverWait(web_driver, timeout).until(expected_conditions.visibility_of(element))


def wait_for_element_visible(web_driver, xpath, timeout=60):
    element = wait_for_element(web_driver, xpath, timeout)
    wait_for_visible(web_driver, element, timeout)


def wait_for_invisible(web_driver, xpath, timeout=60):
    WebDriverWait(web_driver, timeout).until(
        expected_conditions.invisibility_of_element_located((By.XPATH, xpath)))


def short_sleep():
    sleep_norm_dist(3, 0.5, 1)


def medium_sleep():
    sleep_norm_dist(10, 1, 5)


def format_listings(listings):
    return {listing.mls_id for listing in listings}, {listing.mls_id: listing for listing in listings}
