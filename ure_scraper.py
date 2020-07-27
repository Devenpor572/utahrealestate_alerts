import shared

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select

import money_parser

import os
import re
import time


def get_next(driver):
    result = None
    try:
        result = shared.wait_for_element_visible(driver, shared.PARAMS['xpath']['next_button'], 3)
    except:
        pass
    return result


def scrape():
    options = Options()
    options.headless = shared.HEADLESS
    options.add_argument("--width=" + shared.PARAMS['scrape']['width'])
    options.add_argument("--height=" + shared.PARAMS['scrape']['height'])
    firefox_profile = webdriver.FirefoxProfile()
    for file in os.listdir(shared.EXTENSIONS_DIR):
        firefox_profile.add_extension(extension=os.path.join(shared.EXTENSIONS_DIR, file))
    if 'firefox_profile_ure' in shared.CONFIG:
        for key, value in shared.CONFIG['firefox_profile_ure'].items():
            firefox_profile.set_preference(key, int(value))
    driver = webdriver.Firefox(firefox_profile=firefox_profile,
                               options=options,
                               executable_path=shared.DRIVER_PATH,
                               service_log_path=shared.CONFIG['constant']['driver_log_file'])
    try:
        driver.set_page_load_timeout(int(shared.CONFIG['search']['driver_timeout']))
        driver.get(shared.PARAMS['scrape']['ure'])
        xpaths = shared.PARAMS['xpath']
        shared.wait_for_element_visible(driver, xpaths['geolocation'])
        driver.find_element_by_xpath(xpaths['geolocation']).send_keys(shared.CONFIG['search']['geolocation'])
        shared.wait_for_element_visible(driver, xpaths['geolocation'])
        driver.find_element_by_xpath(xpaths['geolocation']).send_keys(Keys.RETURN)
        results = driver.find_elements_by_xpath(xpaths['cookie_close_banner'])
        if results:
            driver.execute_script("arguments[0].click();", results[0])
        shared.wait_for_element_visible(driver, xpaths['filter'])
        filter_el = driver.find_element_by_xpath(xpaths['filter'])
        driver.execute_script("arguments[0].click();", filter_el)
        shared.wait_for_element_visible(driver, xpaths['min_price'])
        driver.find_element_by_xpath(xpaths['min_price']).send_keys(shared.CONFIG['search']['min_price'])
        shared.wait_for_element_visible(driver, xpaths['max_price'])
        driver.find_element_by_xpath(xpaths['max_price']).send_keys(shared.CONFIG['search']['max_price'])
        shared.wait_for_element_visible(driver, xpaths['bedrooms_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['bedrooms_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['bedrooms_dropdown'])
        shared.wait_for_element_visible(driver, xpaths['bathrooms_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['bathrooms_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['bathrooms_dropdown'])
        shared.wait_for_element(driver, xpaths['under_contract_checkbox'])
        under_contract_element = driver.find_element_by_xpath(xpaths['under_contract_checkbox'])
        driver.execute_script("arguments[0].click();", under_contract_element)
        shared.wait_for_element_visible(driver, xpaths['square_feet_dropdown'])
        sqft_el = driver.find_element_by_xpath(xpaths['square_feet_dropdown'])
        driver.execute_script("arguments[0].scrollIntoView(true);", sqft_el)
        Select(sqft_el).select_by_visible_text(shared.CONFIG['search']['square_feet_dropdown'])
        shared.wait_for_element_visible(driver, xpaths['acres_dropdown'])
        Select(driver.find_element_by_xpath(xpaths['acres_dropdown'])).select_by_visible_text(
            shared.CONFIG['search']['acres_dropdown'])
        shared.wait_for_element_visible(driver, xpaths['update_search'])
        update_search = driver.find_element_by_xpath(xpaths['update_search'])
        driver.execute_script("arguments[0].click();", update_search)
        shared.wait_for_element_visible(driver, xpaths['results_listings'])
        shared.wait_for_invisible(driver, xpaths['results_spin_wrap'])
        page_sources = [driver.page_source]
        result = get_next(driver)
        while result:
            driver.execute_script("arguments[0].click();", result)
            shared.wait_for_element_visible(driver, xpaths['results_listings'])
            page_sources.append(driver.page_source)
            result = get_next(driver)
    finally:
        driver.quit()
    return page_sources


def match_cache_file(file):
    return re.match(r'.*_(\d+)\.html', file)


def update_cache():
    shared.log_message('Begin URE update cache')
    if shared.UPDATE_CACHE:
        start = time.time()
        sources = scrape()
        end = time.time()
        for file in os.listdir(shared.CACHE_CURRENT_URE_DIR):
            os.remove(os.path.join(shared.CACHE_CURRENT_URE_DIR, file))
        for i, source in enumerate(sources):
            with open(os.path.join(shared.CACHE_CURRENT_URE_DIR, '{}_{}.html'.format(shared.g_timestamp, i)), 'w') as file:
                file.write(source)
        shared.log_message(f'URE cache updated ({len(sources)} pages in {end - start:.2f} seconds) '
                           f'under name {shared.g_timestamp}')
    else:
        shared.log_message('UPDATE_CACHE set to false')


def extract_value(value):
    matches = re.match(r'^(\d*\.?\d+)\+.*$', value)
    return float(matches.group(1))


def extract_results_count(results_str):
    matches = re.match(r'^([\d,]+)\s.*$', results_str)
    return int(matches.group(1).replace(',', ''))


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


def parse_html(source):
    mls_listings = []
    soup = BeautifulSoup(source, 'html.parser')
    count = 0
    results_count_el = soup.select_one(shared.PARAMS['selector']['results_count_ure'])
    expected_count = extract_results_count(results_count_el.text)
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
        image_url = property_card.select_one(shared.PARAMS['selector']['listing_img_ure']).attrs['src']
        # ['mls', 'address', 'price', 'status', 'bedrooms', 'bathrooms', 'sqft', 'agent', 'open_house', 'source',
        # 'image_url']
        listing = shared.MLS(mls, address, list_price, status, bedrooms, bathrooms, sqft, listing_agent, open_house,
                             shared.SOURCE_URE, image_url)
        validate_listing(listing)
        mls_listings.append(listing)
    if count == 0:
        raise ValueError('No listings found')
    return expected_count, mls_listings


def parse_cache():
    shared.log_message('Begin URE parse cache')
    parsed_files = list()
    expected_count = 0
    count = 0
    for filename in sorted(os.listdir(shared.CACHE_CURRENT_URE_DIR)):
        with open(os.path.join(shared.CACHE_CURRENT_URE_DIR, filename), 'r') as file:
            expected_count, mls_listings = parse_html(file.read())
            count += len(mls_listings)
            parsed_files.append(mls_listings)
    if count < expected_count or (count == 500 and expected_count > 500):
        raise ValueError(f'Results count ({count}) does not equal expected count ({expected_count})')
    listings = [item for sublist in parsed_files for item in sublist]
    shared.log_message(f'URE parse cache returned {len(listings)} listings')
    return listings


def get_mls_listings():
    update_cache()
    return parse_cache()


def test():
    shared.log_message('Begin URE_scraper')
    start = time.time()
    update_cache()
    end = time.time()
    shared.log_message(f'Update cache: {end - start:.2f} seconds')
    start = time.time()
    listings = parse_cache()
    end = time.time()
    shared.log_message(f'Parse cache: {end - start:.2f} seconds')
    for listing in listings:
        shared.log_message(shared.prettify_mls_str(listing))
    shared.log_message('End URE_scraper')


def perf_test():
    import traceback
    fail_count = 0
    attempts = 100
    for i in range(attempts):
        try:
            print(f'{i:03} begin')
            scrape()
            print(f'{i:03} success')
        except:
            fail_count += 1
            print(f'{i:03} fail: {traceback.format_exc()}')
        time.sleep(30)
    print(f'{attempts} attempts; {fail_count} failures; {100*((attempts-fail_count)/float(attempts)):2f}% success rate')


if __name__ == '__main__':
    test()
