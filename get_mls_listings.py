import shared

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

import money_parser

import re
import sys


def failure(web_driver):
    shared.log_message('Failed!')
    web_driver.quit()
    sys.exit()


def wait_for_element(web_driver, xpath):
    try:
        WebDriverWait(web_driver, 60).until(
            expected_conditions.presence_of_element_located((By.XPATH, xpath)))
    except TimeoutException:
        failure(web_driver)


def short_sleep():
    shared.sleep_norm_dist(3, 0.5, 1)


def medium_sleep():
    shared.sleep_norm_dist(10, 1, 5)


def scrape():
    options = Options()
    options.headless = False
    options.add_argument("--width=" + shared.PARAMS['scrape']['width'])
    options.add_argument("--height=" + shared.PARAMS['scrape']['height'])
    driver = webdriver.Firefox(options=options, executable_path=shared.DRIVER_PATH,
                               service_log_path=shared.CONFIG['constant']['driver_log_file'])
    try:
        driver.get(shared.PARAMS['scrape']['url'])

        xpaths = shared.PARAMS['xpath']

        medium_sleep()
        wait_for_element(driver, xpaths['geolocation'])
        driver.find_element_by_xpath(xpaths['geolocation']).send_keys(shared.CONFIG['search']['geolocation'])
        short_sleep()
        wait_for_element(driver, xpaths['geolocation'])
        driver.find_element_by_xpath(xpaths['geolocation']).send_keys(Keys.RETURN)
        medium_sleep()
        results = driver.find_elements_by_xpath(xpaths['cookie_close_banner'])
        if results and len(results) == 1:
            driver.execute_script("arguments[0].click();", results[0])
        short_sleep()
        wait_for_element(driver, xpaths['filter'])
        filter_el = driver.find_element_by_xpath(xpaths['filter'])
        driver.execute_script("arguments[0].click();", filter_el)
        medium_sleep()
        wait_for_element(driver, xpaths['min_price'])
        driver.find_element_by_xpath(xpaths['min_price']).send_keys(shared.CONFIG['search']['min_price'])
        short_sleep()
        wait_for_element(driver, xpaths['max_price'])
        driver.find_element_by_xpath(xpaths['max_price']).send_keys(shared.CONFIG['search']['max_price'])
        short_sleep()
        wait_for_element(driver, xpaths['bedrooms_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['bedrooms_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['bedrooms_dropdown'])
        short_sleep()
        wait_for_element(driver, xpaths['bathrooms_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['bathrooms_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['bathrooms_dropdown'])
        short_sleep()
        wait_for_element(driver, xpaths['under_contract_checkbox'])
        under_contract_element = driver.find_element_by_xpath(xpaths['under_contract_checkbox'])
        driver.execute_script("arguments[0].click();", under_contract_element)
        short_sleep()
        wait_for_element(driver, xpaths['square_feet_dropdown'])
        sqft_el = driver.find_element_by_xpath(xpaths['square_feet_dropdown'])
        driver.execute_script("arguments[0].click();", sqft_el)
        Select(sqft_el).select_by_visible_text(shared.CONFIG['search']['square_feet_dropdown'])
        short_sleep()
        wait_for_element(driver, xpaths['acres_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['acres_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['acres_dropdown'])
        short_sleep()
        wait_for_element(driver, xpaths['update_search'])
        update_search = driver.find_element_by_xpath(xpaths['update_search'])
        driver.execute_script("arguments[0].click();", update_search)
        medium_sleep()
        page_source = driver.page_source
    finally:
        driver.quit()
    return page_source


def update_cache():
    if shared.UPDATE_CACHE:
        source = scrape()
        with open(shared.CACHE_FILE, 'w') as file:
            file.write(source)
        shared.log_message('Cache updated')
    else:
        shared.log_message('UPDATE_CACHE set to false')


def extract_value(value):
    matches = re.match(r'^(\d*\.?\d+)\+.*$', value)
    return float(matches.group(1))


def validate_listing(listing):
    min_price = int(shared.CONFIG['search']['min_price'])
    if listing.price < min_price:
        raise ValueError('Listing {} is less than ${:,}'.format(listing.mls_id, min_price))
    max_price = int(shared.CONFIG['search']['max_price'])
    if listing.price > max_price:
        raise ValueError('Listing {} is more than ${:,}'.format(listing.mls_id, max_price))
    bedrooms = extract_value(shared.CONFIG['search']['bedrooms_dropdown'])
    if listing.bedrooms < bedrooms:
        raise ValueError('Listing {} contains fewer than {} bedrooms'.format(listing.mls_id, bedrooms))
    bathrooms = extract_value(shared.CONFIG['search']['bathrooms_dropdown'])
    if listing.bathrooms < bathrooms:
        raise ValueError('Listing {} contains fewer than {} bathrooms'.format(listing.mls_id, bathrooms))
    square_feet = extract_value(shared.CONFIG['search']['square_feet_dropdown'])
    if listing.sqft < square_feet:
        raise ValueError('Listing {} is less than {} square feet'.format(listing.mls_id, square_feet))


def format_listings(listings):
    return {listing.mls_id for listing in listings}, {listing.mls_id: listing for listing in listings}


def parse_html(source):
    mls_listings = []
    mls_listings_dict = {
        shared.ACTIVE: [],
        shared.BACKUP_OFFER: [],
        shared.UNDER_CONTRACT: []
    }
    soup = BeautifulSoup(source, 'html.parser')
    count = 0
    for property_card in soup.select(shared.PARAMS['selector']['property_card']):
        if not ('class' in property_card.attrs and
                shared.PARAMS['selector']['property_card_class'] in property_card.attrs['class']):
            continue
        count += 1
        mls = int(property_card.attrs['listno'])
        openhouse_label_el = property_card.select_one(shared.PARAMS['selector']['openhouse_label'])
        if openhouse_label_el:
            open_house = openhouse_label_el.text
            open_house = " ".join(open_house.split())
        else:
            open_house = ''
        property_details = property_card.select(shared.PARAMS['selector']['property_details'])[0]
        status = property_details.select_one(shared.PARAMS['selector']['status']).contents[2].strip()
        listing_details_el = property_details.select_one(shared.PARAMS['selector']['listing_details'])
        list_price_el = listing_details_el.select_one(shared.PARAMS['selector']['list_price'])
        list_price_str = list_price_el.text
        list_price = int(money_parser.price_str(list_price_str))
        details_str = listing_details_el.contents[2].strip()
        bedrooms = int(re.match(r'^(\d+) bds .*', details_str).group(1))
        bathrooms = int(re.match(r'.* (\d+) ba .*', details_str).group(1))
        sqft = int(re.match(r'.* (\d+) SqFt\.$', details_str).group(1))
        address = property_details.select_one(shared.PARAMS['selector']['address']).text.strip()
        address = " ".join(address.split())
        listing_agent = property_details.select_one(shared.PARAMS['selector']['listing_agent']).text.strip()
        # ['mls', 'address', 'price', 'status', 'bedrooms', 'bathrooms', 'sqft', 'agent', 'open_house']
        listing = shared.MLS(mls, address, list_price, status, bedrooms, bathrooms, sqft, listing_agent, open_house)
        validate_listing(listing)
        mls_listings.append(listing)
        mls_listings_dict[status].append(listing)
    if count == 0:
        raise ValueError('No listings found')
    return format_listings(mls_listings), {key: format_listings(value) for key, value in mls_listings_dict.items()}


def parse_cache():
    with open(shared.CACHE_FILE, 'r') as file:
        return parse_html(file.read())


def get_mls_listings():
    update_cache()
    return parse_cache()


def test():
    assert extract_value('0.20+') == 0.2
    assert extract_value('.20+') == 0.2
    assert extract_value('1500+') == 1500
    assert extract_value('3+') == 3
    assert extract_value('2+') == 2
    assert extract_value('2414.241+') == 2414.241


if __name__ == '__main__':
    test()
