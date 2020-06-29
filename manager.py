#!/usr/bin/python3
import shared
import db_manager as db
import ksl_scraper
import ure_scraper
import email_manager

import sys
import traceback

LISTING_STATE_DICT = {shared.ACTIVE: 0, shared.BACKUP_OFFER: 1, shared.UNDER_CONTRACT: 2, shared.OFF_MARKET: 3}


def get_all_set(listing_dict, statuses):
    return set().union(*[listing_dict[status][0] for status in statuses])


def update_db_new_listings(current, current_dict, previous, previous_dict):
    # New listings includes all current listings that are not previous listings
    all_current = get_all_set(current_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT])
    all_previous = get_all_set(previous_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT,
                                               shared.OFF_MARKET])
    new_listing_ids = all_current - all_previous
    if new_listing_ids:
        db.insert_rows([current[1][new_mls_num] for new_mls_num in new_listing_ids])


def update_db_off_market(current, current_dict, previous, previous_dict):
    # Off Market includes all previous listings that are not current listings
    all_current = get_all_set(current_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT])
    all_previous = get_all_set(previous_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT])
    off_market_ids = all_previous - all_current
    if off_market_ids:
        for off_market_id in off_market_ids:
            mls = previous[1][off_market_id]
            mls.status = shared.OFF_MARKET
            db.update_row(mls)


def update_db(current, current_dict, previous, previous_dict):
    # All listings in both current and previous
    all_current = get_all_set(current_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT])
    all_previous = get_all_set(previous_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT,
                                               shared.OFF_MARKET])
    existing_ids = all_current.intersection(all_previous)
    if existing_ids:
        for existing_id in existing_ids:
            db.update_row(current[1][existing_id])


def send_email(current, current_dict, previous, previous_dict):
    # New listings includes all current listings that are not previous listings
    all_current = get_all_set(current_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT])
    all_previous = get_all_set(previous_dict, [shared.ACTIVE, shared.BACKUP_OFFER, shared.UNDER_CONTRACT,
                                               shared.OFF_MARKET])
    new_listing_ids = [mls for mls in all_current - all_previous if current[1][mls].status in [shared.ACTIVE]]
    if new_listing_ids:
        shared.log_message('New listings: {}'.format(', '.join(map(str, new_listing_ids))))
    existing_ids = all_current.intersection(all_previous)
    more_available_ids = dict()
    price_drop_ids = dict()
    open_house_ids = dict()
    for existing_id in existing_ids:
        prepend = 'MLS #{}: '.format(existing_id)
        # If the listing has become more available than previously
        if current[1][existing_id].status not in [shared.UNDER_CONTRACT, shared.OFF_MARKET] \
                and LISTING_STATE_DICT[current[1][existing_id].status] < LISTING_STATE_DICT[previous[1][existing_id].status]:
            message = 'Availability Change: {} -> {}'.format(previous[1][existing_id].status,
                                                             current[1][existing_id].status)
            shared.log_message(prepend + message)
            more_available_ids[existing_id] = message
        # If the listing has had a price drop
        elif current[1][existing_id].price < previous[1][existing_id].price \
                and current[1][existing_id].status not in [shared.UNDER_CONTRACT, shared.OFF_MARKET]:
            message = 'Price Drop: ${:,} -> ${:,}'.format(previous[1][existing_id].price,
                                                          current[1][existing_id].price)
            shared.log_message(prepend + message)
            price_drop_ids[existing_id] = message
        # If the listing has a new open house
        elif current[1][existing_id].open_house \
                and not previous[1][existing_id].open_house \
                and current[1][existing_id].status not in [shared.UNDER_CONTRACT, shared.OFF_MARKET]:
            message = 'New open house: {}'.format(current[1][existing_id].open_house)
            shared.log_message(prepend + message)
            open_house_ids[existing_id] = message
    if new_listing_ids or more_available_ids or price_drop_ids or open_house_ids:
        email_manager.generate_and_send_email(current[1], new_listing_ids, more_available_ids, price_drop_ids, open_house_ids)
    else:
        shared.log_message('No email sent')


def update_and_alert():
    ksl_results = ksl_scraper.get_mls_listings()
    ure_results = ure_scraper.get_mls_listings()
    results = ure_results + ksl_results
    results_dict = {status: [result for result in results if result.status == status] for status in shared.STATUSES}
    current = shared.format_listings(results)
    current_dict = {key: shared.format_listings(value) for key, value in results_dict.items()}
    if db.db_exists():
        previous, previous_dict = db.get_db_listings()
        update_db_new_listings(current, current_dict, previous, previous_dict)
        update_db_off_market(current, current_dict, previous, previous_dict)
        update_db(current, current_dict, previous, previous_dict)
        shared.log_message('Updated DB')
        send_email(current, current_dict, previous, previous_dict)
    else:
        db.create_db()
        db.insert_rows([value for key, value in current[1].items()])
        shared.log_message('Created DB')


def short_loop_sleep():
    shared.sleep_norm_dist(60, 10, 15)


def update():
    passed = False
    for i in range(5):
        try:
            shared.update_timestamp()
            shared.log_message('Begin {}'.format(shared.g_timestamp))
            update_and_alert()
            shared.log_message('End {}'.format(shared.g_timestamp))
            shared.make_checkpoint(shared.CACHE_CURRENT_DIR, shared.CACHE_CHECKPOINT_DIR)
            shared.make_checkpoint(shared.DB, shared.DB_CHECKPOINT_DIR)
            passed = True
            break
        except:
            shared.log_message(traceback.format_exc())
            short_loop_sleep()
    return passed


if __name__ == '__main__':
    if not update():
        sys.exit(1)
    else:
        sys.exit(0)
