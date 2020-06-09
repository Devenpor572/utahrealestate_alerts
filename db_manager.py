from shared import *

import os
import sqlite3


def db_exists():
    return os.path.exists(DB)


def create_db():
    if db_exists():
        return
    conn = sqlite3.connect(DB)
    sql = 'CREATE TABLE mls (' \
          'mls_id INT, ' \
          'address VARCHAR(255), ' \
          'price INT, ' \
          'status VARCHAR(255), ' \
          'bedrooms INT, ' \
          'bathrooms INT, ' \
          'sqft INT, ' \
          'agent VARCHAR(255), ' \
          'open_house VARCHAR(255)' \
          ');'
    conn.execute(sql)
    conn.commit()
    conn.close()


def insert_row(row):
    conn = sqlite3.connect(DB)
    conn.execute('INSERT INTO mls VALUES (?,?,?,?,?,?,?,?,?)', row)
    conn.commit()
    conn.close()


def insert_rows(rows):
    conn = sqlite3.connect(DB)
    conn.executemany('INSERT INTO mls VALUES (?,?,?,?,?,?,?,?,?)', rows)
    conn.commit()
    conn.close()


def update_row(row):
    conn = sqlite3.connect(DB)
    sql = "UPDATE mls "\
          "SET " \
          "address='{1}', " \
          "price='{2}', " \
          "status='{3}', " \
          "bedrooms='{4}', " \
          "bathrooms='{5}', " \
          "sqft='{6}', " \
          "agent='{7}', " \
          "open_house='{8}' "\
          "WHERE mls_id='{0}'".format(*row)
    conn.execute(sql)
    conn.commit()
    conn.close()


def get_db_mls_listings_status(status=None):
    conn = sqlite3.connect(DB)
    sql = 'SELECT * FROM mls'
    if status is not None:
        sql += " WHERE status='{}'".format(status)
    rows = conn.execute(sql).fetchall()
    conn.close()
    listings = [MLS(*row) for row in rows]
    return {listing.mls_id for listing in listings}, {listing.mls_id: listing for listing in listings}


def get_db_mls_listings():
    return get_db_mls_listings_status(), \
           {ACTIVE: get_db_mls_listings_status(ACTIVE),
            BACKUP_OFFER: get_db_mls_listings_status(BACKUP_OFFER),
            UNDER_CONTRACT: get_db_mls_listings_status(UNDER_CONTRACT),
            OFF_MARKET: get_db_mls_listings_status(OFF_MARKET)}
