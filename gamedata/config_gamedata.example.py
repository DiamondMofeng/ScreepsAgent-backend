token = '1234567--4e26789e-b6789-54a67896789a6'

TEMP_TOKEN_USERNAME = '123'
TEMP_TOKEN_PASSWORD = '456'

UPDATE_INTERVAL = 1000 * 60 * 60 * 24 * 3  # 3 day js timestamp(ms)

MAX_CONCURRENT_REQUESTS = 5
MAP_STATS_ROOMS_PER_REQUEST = 2500  # should not below 1300, which leads to reaching token's rate limits

# database
DB_TYPE = 'sqlite3'  # sqlite3   /   mysql

# sqlite
SQLITE_PATH = './gamedata.db'

# mysql
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'screeps'
