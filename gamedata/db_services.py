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
            PRIMARY KEY (room, shard),
            room TEXT NOT NULL,
            shard TEXT NOT NULL, 
            room_objects TEXT NOT NULL DEFAULT '',       -- 

            last_update_timestamp INTEGER NOT NULL DEFAULT -1,  -- last timestamp when update room_objects from http endpoint
--             last_scan_timestamp INTEGER NOT NULL DEFAULT -1,    -- last timestamp when this room is scanned by webSocket roomMap2
            --本来想先用ws扫一遍再详细获取信息，但是由于ws扫不到Ruin故取消。

            storage_used_capacity INTEGER NOT NULL DEFAULT -1,
            storage_store TEXT NOT NULL DEFAULT '',

            terminal_used_capacity INTEGER NOT NULL DEFAULT -1,
            terminal_store TEXT NOT NULL DEFAULT '',

            factory_used_capacity INTEGER NOT NULL DEFAULT -1,
            factory_store TEXT NOT NULL DEFAULT ''

            )"""
        )
        conn.commit()


def init_table_map_stats():
    with get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"""CREATE TABLE IF NOT EXISTS map_stats 
            (
            PRIMARY KEY (room, shard),
            room TEXT NOT NULL,
            shard TEXT NOT NULL, 
--             map_stats TEXT NOT NULL DEFAULT '',

            last_update_timestamp INTEGER NOT NULL DEFAULT -1,  -- last timestamp when update map_stats from http endpoint

            owner TEXT NOT NULL DEFAULT '',
            owner_id TEXT NOT NULL DEFAULT '',
            controller_level INTEGER NOT NULL DEFAULT -1,

            novice_area_timestamp INTEGER NOT NULL DEFAULT -1,
            respawn_area_timestamp INTEGER NOT NULL DEFAULT -1,

            is_power_enabled INTEGER NOT NULL DEFAULT -1

            )"""
        )
        conn.commit()


def init_table_room_info():
    with get_database() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS room_info
                            (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            shard TEXT NOT NULL,

                            room_status TEXT NOT NULL DEFAULT '',  --normal, --out of borders, 

                            is_highway INTEGER NOT NULL DEFAULT -1,
                            is_center INTEGER NOT NULL DEFAULT -1,

                            controller_position TEXT NOT NULL DEFAULT '',
                            source_count INTEGER NOT NULL DEFAULT -1,
                            source_position TEXT NOT NULL DEFAULT '',
                            mineral_type TEXT NOT NULL DEFAULT '',
                            mineral_position TEXT NOT NULL DEFAULT '',

                            terrain_exit_direction_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_exit_per_direction TEXT NOT NULL DEFAULT '',          --json

                            terrain_plain_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_swamp_count INTEGER NOT NULL  DEFAULT -1,
                            terrain_wall_count INTEGER NOT NULL  DEFAULT -1

                            )
                            ''')
        conn.commit()


def init_table_room_terrain():
    with get_database() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS room_terrain
                                    (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    room TEXT NOT NULL,
                                    shard TEXT NOT NULL,
                                    terrain TEXT NOT NULL DEFAULT ''
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
    for shard in SHARDS:
        with get_database() as conn:
            c = conn.cursor()
            # if already exists, then skip
            c.execute(f"SELECT 1 FROM room_info WHERE shard = '{shard}'")
            if c.fetchone():
                continue

            res_world_size = requests.get(f'https://screeps.com/api/game/world-size', params={'shard': shard})
            world_size = res_world_size.json()
            rooms = utils.getRoomsByWorldSize(world_size['height'], world_size['width'])
            for room in rooms:
                for table_name in ['room_info', 'room_terrain', 'room_objects', 'map_stats']:
                    c.execute(f"""
                        INSERT INTO {table_name} (room, shard) VALUES ('{room}', '{shard}') 
                        WHERE NOT EXISTS    (  
                                            SELECT 1 FROM {table_name} 
                                            WHERE room = '{room}' AND shard = '{shard}'
                                            )
                        
                        """
                              )
            conn.commit()


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
            f"SELECT room FROM room_info WHERE shard={shard} AND mineral_type = '' AND instr(room,'0')=0 ")  # 后面是筛去过道房
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
    print(select_room_info_by_rooms(['W1N1', 'W1N2'], 'shard1'))
