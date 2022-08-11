import asyncio
import json

from common import screeps_api_aiohttp, utils
from gamedata import config_gamedata as config
from gamedata import db_services

"""
dynamic data is mainly room-objects.
Besides, map-stats should also be updated.
"""
SHARDS = ['shard0', 'shard1', 'shard2', 'shard3']


async def init_table():
    db_services.init_table_room_objects()
    db_services.init_table_map_stats()
    db_services.init_rooms()


async def update_room_objects():
    async with screeps_api_aiohttp.API(token=config.token) as api:
        for shard in SHARDS:
            with db_services.get_database() as conn:
                c = conn.cursor()
                c.execute(f"""
                    SELECT room FROM room_objects 
                    WHERE shard = '{shard}'
                    AND last_update_timestamp < {utils.get_js_timestamp() - config.UPDATE_INTERVAL}
                    """)
                rooms = [row[0] for row in c.fetchall()]

                semaphore = asyncio.Semaphore(config.MAX_CONCURRENT)

                async def update_a_room(room):
                    async with semaphore:
                        # print(f'updating dynamic room_objects of {shard}/{room}')
                        room_objects: list = (await api.room_objects(room, shard))['objects']
                        room_objects_json = json.dumps(room_objects)

                        def translation_single_quotes(s: str):
                            return s.replace("'", r"\'")

                        room_objects_json = translation_single_quotes(room_objects_json)

                        def try_find(_room_objects, _structure_type):

                            live_strut = [obj for obj in _room_objects if obj['type'] == _structure_type]
                            if len(live_strut) > 0:
                                return live_strut[0]
                            ruin_strut = [
                                obj for obj in _room_objects
                                if
                                obj['type'] == 'ruin'
                                and
                                obj['structure']['type'] == _structure_type
                            ]
                            if len(ruin_strut) > 0:
                                return ruin_strut[0]
                            return {}

                        def get_used_capacity(room_object):
                            if 'store' not in room_object:
                                return 0
                            # print(room_object['store'].values())
                            return sum([amount for amount in room_object['store'].values() if type(amount) is int])

                        def get_store(room_object):
                            if 'store' not in room_object:
                                return '{}'
                            return json.dumps(room_object['store'])

                        update_dict = {
                            'last_update_timestamp': utils.get_js_timestamp(),
                            'room_objects': room_objects_json
                        }

                        for structure_type in ['storage', 'terminal', 'factory']:
                            structure = try_find(room_objects, structure_type)

                            update_dict[f'{structure_type}_used_capacity'] = get_used_capacity(structure)
                            update_dict[f'{structure_type}_store'] = get_store(structure)
                            # c.execute(f"""
                            #     UPDATE room_objects
                            #     SET {structure_type}_used_capacity = {get_used_capacity(structure)},
                            #         {structure_type}_store = '{get_store(structure)}'
                            #     WHERE room = '{room}' AND shard = '{shard}'
                            #     """)

                        c.execute(f"""
                            UPDATE room_objects
                            SET {','.join([f"{k} = '{v}'" for k, v in update_dict.items()])}
                            WHERE room = '{room}' AND shard = '{shard}'
                        """)

                        conn.commit()
                        print(f'updated dynamic room_objects of {shard}/{room}')

                await asyncio.gather(*[update_a_room(room) for room in rooms])
    pass


async def update_map_stats():
    """"
    需要提供一个有可用token的api
    :return:
    """
    async with screeps_api_aiohttp.API(token=config.token) as api:

        # 从数据库中选出需要更新的房间
        for shard in SHARDS:
            with db_services.get_database() as conn:
                c = conn.cursor()
                c.execute(
                    f"""
                    SELECT room FROM map_stats
                    WHERE shard='{shard}' 
                    AND last_update_timestamp < {utils.get_js_timestamp() - config.UPDATE_INTERVAL}
                    """)
                rooms = [room_tup[0] for room_tup in c.fetchall()]
            i = 0
            short_split_rooms = utils.split_list_by_len(rooms, 900)  # 单次请求900会被rate limit限制，然而超过900会payload too large
            for short_rooms in short_split_rooms:
                map_stats = await api.map_stats(short_rooms, shard, 'claim0')
                i += 1
                print(f'updating dynamic map-stats: {shard}: {i}/{len(short_split_rooms)}')

                # db_services.update_mineral_type_by_map_stats_and_shard(map_stats, shard)
                with db_services.get_database() as conn:
                    c = conn.cursor()
                    current_timestamp = utils.get_js_timestamp()

                    def get_room_stats_dict_from_map_stats(roomName, roomStat):
                        res = {}
                        res['room'] = roomName
                        res['status'] = roomStat['status'] if 'status' in roomStat else 'unknown'

                        res['novice_area_stamp'] = roomStat['novice'] if (
                                'novice' in roomStat and roomStat['novice'] is not None
                        ) else -1
                        res['respawn_area_stamp'] = roomStat['respawnArea'] if (
                                'respawnArea' in roomStat and roomStat['respawnArea'] is not None
                        ) else -1
                        res['owner_id'] = roomStat['own']['user'] if 'own' in roomStat else 'none'
                        res['owner'] = map_stats['users'][res['owner_id']]['username'] if res[
                                                                                              'owner_id'] != 'none' else 'none'
                        res['controller_level'] = roomStat['own']['level'] if 'own' in roomStat else 0
                        res['is_power_enabled'] = int(
                            roomStat['isPowerEnabled'] if 'isPowerEnabled' in roomStat else 0
                        )
                        return res

                    room_stats_s = [get_room_stats_dict_from_map_stats(roomName, roomStats)
                                    for
                                    roomName, roomStats
                                    in
                                    map_stats['stats'].items()
                                    ]

                    sql_replace = f"""
                            REPLACE INTO map_stats (room, shard, room_status, owner, owner_id, controller_level, is_power_enabled,
                                                    novice_area_timestamp, respawn_area_timestamp, last_update_timestamp)
                            VALUES {','.join(f"('{room_stat['room']}', '{shard}', '{room_stat['status']}', '{room_stat['owner']}', '{room_stat['owner_id']}', {room_stat['controller_level']}, {room_stat['is_power_enabled']}, {room_stat['novice_area_stamp']}, {room_stat['respawn_area_stamp']}, {current_timestamp})" for room_stat in room_stats_s)}

                            """

                    c.execute(
                        sql_replace
                    )
                    conn.commit()


async def main():
    await asyncio.gather(
        update_map_stats(),
        update_room_objects()
    )

    pass


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
