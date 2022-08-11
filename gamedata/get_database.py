import sqlite3
import pymysql
from gamedata import config_gamedata as config


# TODO merge this to somewhere else. Currently at db_services.py

def get_database(database_type=config.DB_TYPE):
    if database_type == 'mysql':
        return pymysql.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            passwd=config.MYSQL_PASSWORD,
            db=config.MYSQL_DB)
    if database_type == 'sqlite' or database_type == 'sqlite3':
        return sqlite3.connect(config.SQLITE_PATH)


if __name__ == '__main__':
    with get_database('mysql') as db:
        print('connected')
        c = db.cursor()
        c.execute(f"""
        SELECT * FROM room_info WHERE shard = 'shard1' AND room ='W1N1'
        """)
        print(c.fetchone())
