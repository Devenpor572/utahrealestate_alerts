from shared import *
from db_manager import *
from get_mls_listings import get_mls_listings
from email_manager import generate_and_send_email

import sys

LISTING_STATE_DICT = {ACTIVE: 0, BACKUP_OFFER: 1, UNDER_CONTRACT: 2, OFF_MARKET: 3}


def get_all_set(listing_dict):
    return set().union(listing_dict[ACTIVE][0], listing_dict[BACKUP_OFFER][0], listing_dict[UNDER_CONTRACT][0])


def update_db_new_listings(current, current_dict, previous, previous_dict):
    # New listings includes all current listings that are not previous listings
    all_current = get_all_set(current_dict)
    all_previous = get_all_set(previous_dict)
    new_listing_ids = all_current - all_previous
    if new_listing_ids:
        insert_rows([current[1][new_mls_num] for new_mls_num in new_listing_ids])


def update_db_off_market(current, current_dict, previous, previous_dict):
    # Off Market includes all previous listings that are not current listings
    all_current = get_all_set(current_dict)
    all_previous = get_all_set(previous_dict)
    off_market_ids = all_previous - all_current
    if off_market_ids:
        for off_market_id in off_market_ids:
            mls = previous[1][off_market_id]
            mls.status = OFF_MARKET
            update_row(mls)


def update_db(current, current_dict, previous, previous_dict):
    # All listings in both current and previous
    all_current = get_all_set(current_dict)
    all_previous = get_all_set(previous_dict)
    existing_ids = all_current.intersection(all_previous)
    if existing_ids:
        for existing_id in existing_ids:
            update_row(current[1][existing_id])


def send_email(current, current_dict, previous, previous_dict):
    # New listings includes all current listings that are not previous listings
    all_current = get_all_set(current_dict)
    all_previous = get_all_set(previous_dict)
    new_listing_ids = all_current - all_previous
    existing_ids = all_current.intersection(all_previous)
    more_available_ids = dict()
    price_drop_ids = dict()
    open_house_ids = dict()
    for existing_id in existing_ids:
        # If the listing has become more available than previously
        if LISTING_STATE_DICT[current[1][existing_id].status] < LISTING_STATE_DICT[previous[1][existing_id].status]:
            more_available_ids[existing_id] = 'Availability Change: {} -> {}'.format(previous[1][existing_id].status,
                                                                                     current[1][existing_id].status)
        # If the listing has had a price drop
        elif current[1][existing_id].price < previous[1][existing_id].price:
            price_drop_ids[existing_id] = 'Price Drop: ${:,} -> ${:,}'.format(previous[1][existing_id].price,
                                                                              current[1][existing_id].price)
            # If the listing has a new open house
        elif current[1][existing_id].open_house and not previous[1][existing_id].open_house:
            open_house_ids[existing_id] = 'New open house: {}'.format(current[1][existing_id].open_house)
    if new_listing_ids or more_available_ids or price_drop_ids or open_house_ids:
        generate_and_send_email(current[1], new_listing_ids, more_available_ids, price_drop_ids, open_house_ids)
    else:
        log_message('No email sent')


def update_and_alert():
    current, current_dict = get_mls_listings()
    if db_exists():
        previous, previous_dict = get_db_mls_listings()
        update_db_new_listings(current, current_dict, previous, previous_dict)
        update_db_off_market(current, current_dict, previous, previous_dict)
        update_db(current, current_dict, previous, previous_dict)
        log_message('Updated DB')
        send_email(current, current_dict, previous, previous_dict)
    else:
        create_db()
        insert_rows([value for key, value in current[1].items()])
        log_message('Created DB')


def short_loop_sleep():
    sleep_norm_dist(60, 10, 15)


def loop_sleep():
    sleep_norm_dist(900, 120, 300)


def main_loop():
    loop_num = 0
    while True:
        for i in range(5):
            try:
                loop_num += 1
                log_message('Begin update/alert {}'.format(loop_num))
                update_and_alert()
                log_message('End update/alert {}'.format(loop_num))
                break
            except:
                log_message(sys.exc_info())
                short_loop_sleep()
        loop_sleep()


main_loop()
