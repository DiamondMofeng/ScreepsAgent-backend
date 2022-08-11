import sqlite3
import os
import sys

import pymysql
import requests

from gamedata import config_gamedata as config
from common import utils

SHARDS = [f'shard{i}' for i in range(0, 3 + 1)]
SHARDS.reverse()


def get_database(database_type=config.DB_TYPE):
    if database_type == 'mysql':
        return pymysql.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            passwd=config.MYSQL_PASSWORD,
            db=config.MYSQL_DB)
    if database_type == 'sqlite' or database_type == 'sqlite3':
        return sqlite3.connect(config.SQLITE_PATH)


def init_table_room_objects():
    with get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"""CREATE TABLE IF NOT EXISTS room_objects 
            (
            room    VARCHAR(255) NOT NULL,
            shard   VARCHAR(255) NOT NULL,
            
            room_objects MEDIUMTEXT,       

            last_update_timestamp BIGINT NOT NULL DEFAULT -1,  /*  -- last timestamp when update room_objects from http endpoint
--             last_scan_timestamp INTEGER NOT NULL DEFAULT -1,    -- last timestamp when this room is scanned by webSocket roomMap2
            --本来想先用ws扫一遍再详细获取信息，但是由于ws扫不到Ruin故取消。

*/
            storage_used_capacity INTEGER NOT NULL DEFAULT -1,
            storage_store TEXT,

            terminal_used_capacity INTEGER NOT NULL DEFAULT -1,
            terminal_store TEXT,

            factory_used_capacity INTEGER NOT NULL DEFAULT -1,
            factory_store TEXT,

            PRIMARY KEY (room, shard)
            )"""
        )
        conn.commit()


def init_table_map_stats():
    with get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"""CREATE TABLE IF NOT EXISTS map_stats 
            (
            room    VARCHAR(255) NOT NULL,
            shard   VARCHAR(255) NOT NULL,

            last_update_timestamp BIGINT NOT NULL DEFAULT -1,  /* -- last timestamp when update map_stats from http endpoint */
            
            room_status TEXT ,  /* --normal, --out of borders, */
            
            owner TEXT,
            owner_id TEXT,
            controller_level INTEGER NOT NULL DEFAULT -1,

            novice_area_timestamp BIGINT NOT NULL DEFAULT -1,
            respawn_area_timestamp BIGINT NOT NULL DEFAULT -1,

            is_power_enabled INTEGER NOT NULL DEFAULT -1,

            PRIMARY KEY (room, shard)
            )"""
        )
        conn.commit()


def init_table_room_info():
    with get_database() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS room_info
                            (
                            room    VARCHAR(255) NOT NULL,
                            shard   VARCHAR(255) NOT NULL,
                            
                            room_status TEXT ,  /* --normal, --out of borders, */ 

                            is_highway INTEGER NOT NULL DEFAULT -1,
                            is_center INTEGER NOT NULL DEFAULT -1,

                            controller_position TEXT,
                            source_count INTEGER NOT NULL DEFAULT -1,
                            source_position TEXT,
                            mineral_type TEXT ,
                            mineral_position TEXT,

                            terrain_exit_direction_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_exit_per_direction TEXT ,        /*  --json */ 

                            terrain_plain_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_swamp_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_wall_count INTEGER NOT NULL  DEFAULT -1,
                            
                            PRIMARY KEY (room, shard)
                            )
                            ''')
        conn.commit()


def init_table_room_terrain():
    with get_database() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS room_terrain
                                    (
                                    room    VARCHAR(255) NOT NULL,
                                    shard   VARCHAR(255) NOT NULL,
                                          
                                    terrain TEXT ,
                                    
                                    PRIMARY KEY (room, shard)
                                    )''')
        conn.commit()


def init():
    init_table_room_info()
    # 因为raw terrain 太大了，所以单独存
    init_table_room_terrain()
    # room-objects表，是动态的所以单独存
    init_table_room_objects()
    init_table_map_stats()


def init_rooms():
    print('checking should init rooms')
    tables = ['room_info', 'room_terrain', 'room_objects', 'map_stats']
    for shard in SHARDS:

        res_world_size = requests.get(f'https://screeps.com/api/game/world-size', params={'shard': shard})
        world_size = res_world_size.json()
        rooms = utils.getRoomsByWorldSize(world_size['height'], world_size['width'])

        for table_name in tables:
            with get_database() as conn:
                c = conn.cursor()
                # if already exists, then skip
                c.execute(f"SELECT room FROM {table_name} WHERE shard = '{shard}'")

                exist_rooms = [row[0] for row in c.fetchall()]
                missing_rooms = [room for room in rooms if room not in exist_rooms]

                if len(missing_rooms) == 0:
                    continue

                print(f'initializing rooms of table {shard} / {table_name}')

                c.execute(
                    f"""
                    INSERT INTO {table_name} (room, shard)
                    VALUES  {','.join([f"('{room}', '{shard}')" for room in missing_rooms])}
                    """)

                print(f'initialized rooms of table {shard} / {table_name}')

                conn.commit()

    print('check over, rooms are inited')


def try_init():
    if not os.path.exists(config.SQLITE_PATH):
        init()
        init_rooms()
    else:
        # print('db already exists')
        pass


def select_room_info_by_rooms(rooms, shard):
    try_init()
    with get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"SELECT * FROM room_info WHERE shard = '{shard}' AND room IN ({','.join([f''' '{room}' ''' for room in rooms])}) "
        )
        return c.fetchall()


def select_rooms_to_update_mineral_type_by_shard(shard):
    with get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"SELECT room FROM room_info WHERE shard={shard} AND mineral_type IS NULL AND instr(room,'0')=0 ")  # 后面是筛去过道房
        rooms = [room_tup[0] for room_tup in c.fetchall()]
        return rooms


def update_mineral_type_by_map_stats_and_shard(map_stats, shard):
    with get_database() as conn:
        c = conn.cursor()
        for roomName, roomStat in map_stats['stats'].items():
            mineral_type = roomStat['minerals0']['type']
            c.execute(
                f"UPDATE room_info SET mineral_type = '{mineral_type}' WHERE room = '{roomName}' AND shard = '{shard}'"
            )
        conn.commit()


if __name__ == '__main__':
    init()
    init_rooms()
    # try_init()
    print(select_room_info_by_rooms(['W1N1', 'W1N2'], 'shard1'))
