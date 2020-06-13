import shared

import os
import sqlite3


def db_exists():
    return os.path.exists(shared.DB)


def create_db():
    if db_exists():
        return
    if not os.path.exists(shared.DB_DIR):
        os.makedirs(shared.DB_DIR)
    conn = sqlite3.connect(shared.DB)
    sql = 'CREATE TABLE mls (' \
          'mls_id INT, ' \
          'address VARCHAR(255), ' \
          'price INT, ' \
          'status VARCHAR(255), ' \
          'bedrooms INT, ' \
          'bathrooms INT, ' \
          'sqft INT, ' \
          'agent VARCHAR(255), ' \
          'open_house VARCHAR(255),' \
          'source VARCHAR(255)' \
          ');'
    conn.execute(sql)
    conn.commit()
    conn.close()


def insert_row(row):
    conn = sqlite3.connect(shared.DB)
    conn.execute('INSERT INTO mls VALUES (?,?,?,?,?,?,?,?,?,?)', row)
    conn.commit()
    conn.close()


def insert_rows(rows):
    conn = sqlite3.connect(shared.DB)
    conn.executemany('INSERT INTO mls VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
    conn.commit()
    conn.close()


def update_row(row):
    conn = sqlite3.connect(shared.DB)
    sql = "UPDATE mls "\
          "SET " \
          "address='{1}', " \
          "price='{2}', " \
          "status='{3}', " \
          "bedrooms='{4}', " \
          "bathrooms='{5}', " \
          "sqft='{6}', " \
          "agent='{7}', " \
          "open_house='{8}', "\
          "source='{9}' "\
          "WHERE mls_id='{0}'".format(*row)
    conn.execute(sql)
    conn.commit()
    conn.close()


def get_db_listings_source_status(status=None):
    conn = sqlite3.connect(shared.DB)
    sql = "SELECT * FROM mls"
    if status is not None:
        sql += " WHERE status='{}'".format(status)
    rows = conn.execute(sql).fetchall()
    conn.close()
    listings = [shared.MLS(*row) for row in rows]
    return {listing.mls_id for listing in listings}, {listing.mls_id: listing for listing in listings}


def get_db_listings():
    return get_db_listings_source_status(), \
           {shared.ACTIVE: get_db_listings_source_status(shared.ACTIVE),
            shared.BACKUP_OFFER: get_db_listings_source_status(shared.BACKUP_OFFER),
            shared.UNDER_CONTRACT: get_db_listings_source_status(shared.UNDER_CONTRACT),
            shared.OFF_MARKET: get_db_listings_source_status(shared.OFF_MARKET)}
