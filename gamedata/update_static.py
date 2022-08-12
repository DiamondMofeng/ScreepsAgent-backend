import asyncio
import json
from collections import Counter

from common import screeps_api_aiohttp, utils, screeps_ws, Terrain_Helper, Helper
from gamedata import config_gamedata as config
from gamedata import db_services

# from gamedata import db_services

"""
controller_position 
source_count 
source_position 
mineral_type 
mineral_position

terrain_exit_direction_count
terrain_exit_per_direction 
terrain_plain_count 
terrain_swamp_count 
terrain_wall_count 



从ws获取
controller_position,
source_count,
source_position,
mineral_position

从map-stats获取
mineral_type

从room-terrain获取terrain相关信息


"""

SHARDS = [f'shard{i}' for i in range(0, 3 + 1)]
SHARDS.reverse()

progress_get_terrain_sum = -1
progress_get_terrain_cur = -1

progress_get_room_objects_sum = -1
progress_get_room_objects_cur = -1


async def mark_is_center_or_highway_room():
    for shard in SHARDS:
        with db_services.get_database() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT room FROM room_info
                WHERE shard='{shard}'
                AND (is_center = -1 OR is_highway = -1)
                """
            )
            rooms = [room_tup[0] for room_tup in c.fetchall()]
            if len(rooms) == 0:
                return

            highway_rooms = [room for room in rooms if utils.isHighWay(room)]  # 确定过道房
            center_rooms = [room for room in rooms if utils.isCenter(room)]  # 确定中心房

            c.execute(
                f"""
                UPDATE room_info
                SET is_highway = 1
                WHERE room IN ("{'","'.join(highway_rooms)}")
                AND shard='{shard}'

                """
            )
            c.execute(
                f"""
                UPDATE room_info
                SET is_center = 1
                WHERE room IN ("{'","'.join(center_rooms)}")
                AND shard='{shard}'
                """
            )
            # 剩余的都置为0
            c.execute(
                f"""
                UPDATE room_info
                SET is_highway = 0
                WHERE room NOT IN ("{'","'.join(highway_rooms)}")
                AND shard='{shard}'
                """
            )
            c.execute(
                f"""
                UPDATE room_info
                SET is_center = 0
                WHERE room NOT IN ("{'","'.join(center_rooms)}")
                AND shard='{shard}'
                """
            )
            conn.commit()


async def update_mineralType_and_roomStatus_by_map_stats():
    """
    需要提供一个有可用token的api
    :return:
    """
    async with screeps_api_aiohttp.API(token=config.token) as api:

        # 从数据库中选出需要更新的房间
        for shard in SHARDS:
            # rooms = db_services.select_rooms_to_update_mineral_type_by_shard(shard)
            with db_services.get_database() as conn:
                c = conn.cursor()
                c.execute(
                    f"""
                    SELECT room FROM room_info 
                    WHERE shard='{shard}' 
                    AND (mineral_type is NULL OR room_status is NULL) 
                    """)
                rooms = [room_tup[0] for room_tup in c.fetchall()]
            i = 0
            short_split_rooms = utils.split_list_by_len(rooms,
                                                        config.MAP_STATS_ROOMS_PER_REQUEST)  # 不宜过大，会造成响应缓慢
            for short_rooms in short_split_rooms:
                map_stats = await api.map_stats(short_rooms, shard, 'minerals0')
                i += 1
                print(f'getting map-stats: {shard}: {i}/{len(short_split_rooms)}')

                # db_services.update_mineral_type_by_map_stats_and_shard(map_stats, shard)
                with db_services.get_database() as conn:
                    c = conn.cursor()
                    for roomName, roomStat in map_stats['stats'].items():
                        mineral_type = roomStat['minerals0']['type'] if 'minerals0' in roomStat else 'none'
                        c.execute(
                            f"""
                            UPDATE room_info 
                            SET 
                            mineral_type = '{mineral_type}', 
                            room_status = '{roomStat['status']}'
                            WHERE 
                            room = '{roomName}'     
                            AND shard = '{shard}'"""
                        )
                    conn.commit()


async def update_room_info_by_ws_roomMap():
    """
    存在以下问题：
        1. 无法获取未开放房间的信息
        2. 无法获取有主的controller位置
    优点：
        快，roomMap2一秒可以获取数十房间的信息

    :return:
    """
    # 选出所有需要更新的房间
    # !因为未开放的房间ws不会推送，所以需要额外更新
    for shard in SHARDS:
        with db_services.get_database() as conn:
            c = conn.cursor()
            c.execute(
                f"""
                SELECT room FROM room_info 
                WHERE 
                shard = '{shard}' 
                AND (controller_position IS NULL OR source_count = '' OR source_position IS NULL OR mineral_position IS NULL)
                AND room_status = 'normal'
                """)
            rooms_all = [room_tup[0] for room_tup in c.fetchall()]

            # 用websocket
            # 回调
            def onRoomMap(event, ws):
                if event['data'] == {}:  # TODO 这里还得手动考虑边界条件
                    return
                roomMapData = screeps_ws.Helper.roomMap.RoomMapData(event)
                shard, roomName = screeps_ws.Helper.parse_channel(event['channel'])[1:2 + 1]
                c.execute(
                    f"UPDATE room_info "
                    f"SET controller_position = '{roomMapData.controller_position}', "
                    f"source_count = '{roomMapData.source_count}', "
                    f"source_position = '{roomMapData.source_positions}', "
                    f"mineral_position = '{roomMapData.mineral_position}' "
                    f"WHERE room = '{roomName}' AND shard = '{shard}'"
                )
                conn.commit()

            i = 0
            split_rooms = utils.split_list_by_len(rooms_all, 750)  # 手动限制ws单次请求，后面想封装到ws模块里
            for rooms in split_rooms:  #

                # from viztracer import VizTracer
                # tracer = VizTracer()
                # tracer.start()

                i += 1
                print(f'{shard}: {i}/{len(split_rooms)}')
                ws = screeps_ws.Client(token=config.token, logging=True)
                for room in rooms:
                    ws.subscribe_roomMap(room, shard, lambda event: onRoomMap(event, ws))
                ws.start()

                # tracer.stop()
                # tracer.save()


async def update_room_info_by_room_objects():
    """
    弥补update_room_info_by_ws_roomMap的不足
        1. 获取未开放房间的基础信息
        2. 获取有主的controller位置

    这里不用ws了，因为未开放房间用不了
    :return:
    """

    async with screeps_api_aiohttp.API(token=config.token) as api:
        for shard in SHARDS:
            # 查出需要更新的房间
            with db_services.get_database() as conn:
                c = conn.cursor()
                c.execute(
                    f"""
                    SELECT room FROM room_info 
                    WHERE 
                    
                    shard = '{shard}'
                    AND 
                    (
                        (
                            room_status != 'normal'
                            AND (controller_position IS NULL OR source_count = '' OR source_position IS NULL OR mineral_position IS NULL)
                        )
                            OR 
                        (
                            is_center = 0               
                            AND is_highway = 0          
                            AND room_status = 'normal'
                            AND controller_position = '[]'
                        )
                    )
                    """)
                rooms = [room_tup[0] for room_tup in c.fetchall()]

            global progress_get_room_objects_sum, progress_get_room_objects_cur
            progress_get_room_objects_sum = len(rooms)
            progress_get_room_objects_cur = 0
            semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

            async def show_progress_get_room_objects(room):
                async with semaphore:
                    global progress_get_room_objects_sum, progress_get_room_objects_cur
                    progress_get_room_objects_cur += 1
                    print(
                        f"getting room-objects: {shard}/{room} : {progress_get_room_objects_sum - progress_get_room_objects_cur}/{progress_get_room_objects_sum}"
                    )
                    objects = (await api.room_objects(room, shard))["objects"]
                    room_objects_helper = Helper.Helper.fromRoomObjectsList(objects)
                    roomObjectsData = room_objects_helper.get_static_room_info()

                    # print(res)
                    with db_services.get_database() as conn:
                        c = conn.cursor()
                        c.execute(
                            f"""
                            UPDATE room_info 
                            SET controller_position = '{roomObjectsData['controller_position']}', 
                            source_count = '{roomObjectsData['source_count']}', 
                            source_position = '{roomObjectsData['source_position']}', 
                            mineral_position = '{roomObjectsData['mineral_position']}' 
                            WHERE room = '{room}' AND shard = '{shard}'
                             """)
                        conn.commit()

            await asyncio.gather(*[show_progress_get_room_objects(room) for room in rooms])


async def update_room_terrain():
    async with screeps_api_aiohttp.API(token=config.token) as api:
        for shard in SHARDS:
            with db_services.get_database() as conn:
                c = conn.cursor()
                c.execute(
                    f"""
                    SELECT room FROM room_terrain
                    WHERE shard='{shard}' 
                    AND terrain IS NULL
                    """)
                rooms = [room_tup[0] for room_tup in c.fetchall()]

            global progress_get_terrain_sum, progress_get_terrain_cur
            progress_get_terrain_sum = len(rooms)
            progress_get_terrain_cur = 0
            semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

            async def show_progress_get_room_terrain(room):
                async with semaphore:
                    global progress_get_terrain_sum, progress_get_terrain_cur
                    progress_get_terrain_cur += 1
                    print(
                        f"getting room-terrain: {shard}/{room}: {progress_get_terrain_sum - progress_get_terrain_cur}/{progress_get_terrain_sum}"
                    )
                    res = (await api.room_terrain(room, shard))["terrain"][0]['terrain']
                    with db_services.get_database() as conn:
                        c = conn.cursor()
                        c.execute(
                            f"""
                            UPDATE room_terrain
                            SET terrain = '{res}'
                            WHERE room = '{room}' AND shard = '{shard}'
                            """)
                        conn.commit()

            await asyncio.gather(*[show_progress_get_room_terrain(room) for room in rooms])


async def update_room_terrain_info():
    with db_services.get_database() as conn:
        c = conn.cursor()
        c.execute(
            f"""
            SELECT room,shard,terrain FROM room_terrain
            WHERE terrain IS NOT NULL
            AND room in (SELECT room FROM room_info WHERE terrain_plain_count = -1)
            AND shard in (SELECT shard FROM room_info WHERE terrain_plain_count = -1)
            """)

        def analyze_then_update_terrain_info(room, shard, terrain):
            # 0:plain
            # 1:wall
            # 2:swamp
            # 3:swamp_wall
            terrain_count = Counter(terrain)

            # 基础地形统计
            plain_count = terrain_count['0']
            swamp_count = terrain_count['2']
            wall_count = terrain_count['1'] + terrain_count['3']

            # 出口数据统计
            terrain_helper = Terrain_Helper.Helper_terrain(terrain)
            terrain_exit_direction_count = terrain_helper.get_exit_dirs_count()
            terrain_exit_per_direction = terrain_helper.get_dict_exit_count_per_dir()

            # 更新至数据库中
            c = conn.cursor()
            c.execute(
                f"""
                UPDATE room_info
                SET
                terrain_plain_count = '{plain_count}',
                terrain_swamp_count = '{swamp_count}',
                terrain_wall_count = '{wall_count}',
                terrain_exit_direction_count = '{terrain_exit_direction_count}',
                terrain_exit_per_direction = '{json.dumps(terrain_exit_per_direction)}'
                WHERE room = '{room}' AND shard = '{shard}'
                """)
            conn.commit()

        for room_tup in c.fetchall():
            room, shard, terrain = room_tup
            print(f"analyzing room-terrain: {shard}/{room}")
            analyze_then_update_terrain_info(room, shard, terrain)

        print('analyze of room-terrain done!')


async def sub_main_update_room_info():
    await mark_is_center_or_highway_room()
    await update_mineralType_and_roomStatus_by_map_stats()
    await update_room_info_by_ws_roomMap()
    await update_room_info_by_room_objects()


async def sub_main_update_room_terrain():
    await update_room_terrain()
    await update_room_terrain_info()


async def main():
    await asyncio.gather(
        sub_main_update_room_info(),
        sub_main_update_room_terrain(),
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
