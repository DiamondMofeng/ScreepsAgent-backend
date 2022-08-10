import sqlite3
import os
import sys

import requests

from gamedata import config_gamedata as config
from common import utils

SHARDS = [f'shard{i}' for i in range(0, 3 + 1)]
SHARDS.reverse()


def init():
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE room_info
                            (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            shard TEXT NOT NULL,
                            
                            room_status TEXT NOT NULL DEFAULT '',  --normal, --out of borders, 
                            
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
        # 因为raw terrain 太大了，所以单独存
        c.execute('''CREATE TABLE room_terrain
                            (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            room TEXT NOT NULL,
                            shard TEXT NOT NULL,
                            terrain CHAR(2500) NOT NULL DEFAULT ''
                            )''')
        conn.commit()


def init_rooms():
    for shard in SHARDS:
        with sqlite3.connect(config.DB_PATH) as conn:
            c = conn.cursor()
            # if already exists, then skip
            c.execute(f"SELECT * FROM room_info WHERE shard = '{shard}'")
            if c.fetchone():
                continue

            res_world_size = requests.get(f'https://screeps.com/api/game/world-size', params={'shard': shard})
            world_size = res_world_size.json()
            rooms = utils.getRoomsByWorldSize(world_size['height'], world_size['width'])
            for room in rooms:
                c.execute(
                    f"INSERT INTO room_info (room, shard) VALUES ('{room}', '{shard}')"
                )
                c.execute(
                    f"INSERT INTO room_terrain (room, shard) VALUES ('{room}', '{shard}')"
                )
            conn.commit()


def try_init():
    if not os.path.exists(config.DB_PATH):
        init()
        init_rooms()
    else:
        # print('db already exists')
        pass


def select_room_info_by_rooms(rooms, shard):
    try_init()
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            f"SELECT * FROM room_info WHERE shard = '{shard}' AND room IN ({','.join([f''' '{room}' ''' for room in rooms])}) "
        )
        return c.fetchall()


def select_rooms_to_update_mineral_type_by_shard(shard):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            f"SELECT room FROM room_info WHERE shard={shard} AND mineral_type = '' AND instr(room,'0')=0 ")  # 后面是筛去过道房
        rooms = [room_tup[0] for room_tup in c.fetchall()]
        return rooms


def update_mineral_type_by_map_stats_and_shard(map_stats, shard):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        for roomName, roomStat in map_stats['stats'].items():
            mineral_type = roomStat['minerals0']['type']
            c.execute(
                f"UPDATE room_info SET mineral_type = '{mineral_type}' WHERE room = '{roomName}' AND shard = '{shard}'"
            )
        conn.commit()


if __name__ == '__main__':
    print(select_room_info_by_rooms(['W1N1', 'W1N2'], 'shard1'))
