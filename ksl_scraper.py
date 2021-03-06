import shared

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import money_parser

import os
import re
import time


# https://stackoverflow.com/questions/48850974/selenium-scroll-to-end-of-page-in-dynamically-loading-webpage
def scroll_down(driver):
    """A method for scrolling the page."""
    # Get scroll height.
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to the bottom.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Wait to load the page.
        shared.wait_for_loader(driver, shared.PARAMS['xpath']['loader'])
        # Calculate new scroll height and compare with last scroll height.
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def scrape():
    options = Options()
    options.headless = shared.HEADLESS
    options.add_argument("--width=600")
    options.add_argument("--height=800")
    firefox_profile = webdriver.FirefoxProfile()
    for file in os.listdir(shared.EXTENSIONS_DIR):
        firefox_profile.add_extension(extension=os.path.join(shared.EXTENSIONS_DIR, file))
    if 'firefox_profile_ksl' in shared.CONFIG:
        for key, value in shared.CONFIG['firefox_profile_ksl'].items():
            firefox_profile.set_preference(key, int(value))
    driver = webdriver.Firefox(firefox_profile=firefox_profile,
                               options=options,
                               executable_path=shared.DRIVER_PATH,
                               service_log_path=shared.CONFIG['constant']['driver_log_file'])
    try:
        driver.set_page_load_timeout(int(shared.CONFIG['search']['driver_timeout']))
        driver.get(shared.CONFIG['search'][shared.SOURCE_KSL])
        shared.wait_for_element_visible(driver, '//*[@id="search-app"]')
        scroll_down(driver)
        sources = [driver.page_source]
    finally:
        driver.quit()
    return sources


def match_cache_file(file):
    return re.match(r'.*_(\d+)\.html', file)


def update_cache():
    shared.log_message('Begin KSL update cache')
    if shared.UPDATE_CACHE:
        start = time.time()
        sources = scrape()
        end = time.time()
        for file in os.listdir(shared.CACHE_CURRENT_KSL_DIR):
            os.remove(os.path.join(shared.CACHE_CURRENT_KSL_DIR, file))
        for i, source in enumerate(sources):
            with open(os.path.join(shared.CACHE_CURRENT_KSL_DIR, '{}_{}.html'.format(shared.g_timestamp, i)), 'w') as file:
                file.write(source)
        shared.log_message(f'KSL cache updated ({len(sources)} pages in {end - start:.2f} seconds) '
                           f'under name {shared.g_timestamp}')
    else:
        shared.log_message('UPDATE_CACHE set to false')


def extract_value(value):
    matches = re.match(r'^(\d*\.?\d+)\+.*$', value)
    return float(matches.group(1))


def extract_results_count(results_str):
    matches = re.match(r'^([\d,]+)\s.*$', results_str)
    return int(matches.group(1))


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
    results_count_el = soup.select_one(shared.PARAMS['selector']['results_count'])
    expected_count = extract_results_count(results_count_el.text)
    count = 0
    for listing_el in soup.select('.Listing'):
        if 'id' not in listing_el.attrs:
            continue
        count += 1
        unique_id = int(listing_el.get('id'))
        address = " ".join(listing_el.select_one('.Address').text.split())
        list_price = int(money_parser.price_str(listing_el.select_one('.Price').text))
        status = shared.ACTIVE
        bed_bath_str = listing_el.select_one('.BedBath').text
        bedrooms = int(re.match(r'(\d+) beds \|.*', bed_bath_str).group(1))
        bathrooms = int(round(float(re.match(r'.*\| (\d+\.?\d*) baths', bed_bath_str).group(1))))
        sqft = int(re.match(r'(\d+) sq\. ft\.', listing_el.select_one('.Listing-squareFeet').text).group(1))
        listing_agent = ''
        open_house = ''
        image_url = listing_el.select_one(shared.PARAMS['selector']['photo_image_ksl']).attrs['src']
        # ['mls', 'address', 'price', 'status', 'bedrooms', 'bathrooms', 'sqft', 'agent', 'open_house', 'source',
        # 'image_url']
        listing = shared.MLS(unique_id, address, list_price, status, bedrooms, bathrooms, sqft, listing_agent,
                             open_house, shared.SOURCE_KSL, image_url)
        validate_listing(listing)
        mls_listings.append(listing)
    if count == 0:
        raise ValueError('No listings found')
    if count < expected_count:
        raise ValueError(f'Results count ({count}) does not equal expected count ({expected_count})')
    return mls_listings


def parse_cache():
    shared.log_message('Begin KSL parse cache')
    parsed_files = list()
    for filename in sorted(os.listdir(shared.CACHE_CURRENT_KSL_DIR)):
        with open(os.path.join(shared.CACHE_CURRENT_KSL_DIR, filename), 'r') as file:
            parsed_files.append(parse_html(file.read()))
    listings = [item for sublist in parsed_files for item in sublist]
    shared.log_message(f'KSL parse cache returned {len(listings)} listings')
    return listings


def get_mls_listings():
    update_cache()
    return parse_cache()


def test():
    import time
    shared.log_message('Begin KSL_scraper')
    start = time.time()
    update_cache()
    end = time.time()
    shared.log_message(f'Update cache: {end-start:.2f} seconds')
    start = time.time()
    listings = parse_cache()
    end = time.time()
    shared.log_message(f'Parse cache: {end-start:.2f} seconds')
    for listing in listings:
        shared.log_message(shared.prettify_mls_str(listing))
    shared.log_message('End KSL_scraper')


if __name__ == '__main__':
    test()
