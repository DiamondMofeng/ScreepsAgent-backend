import asyncio
import json
import math
import os
import re
import ssl
import sys
import time

import certifi

from common import screeps_api_aiohttp
from toys import findRooms

from portals import config_update

"""
I am rather to use websocket instead of http. Anyway my server is very slow and this makes it fatal.
So I have to use http.
"""

"""
for each shard
world-size
如果条件允许，可以先用ws过一遍房间，避免不必要的room-objects请求
如果不是shard0只爬十字路口
如果是shard0，爬十字路口周围2格    

当前没有用到需要token的方法，所以暂时不用token
        
        
        
"""

ssl_context = ssl.create_default_context(cafile=certifi.where())  # my server has some issues, you may do not need this

rooms_len_sum = -1
rooms_len_cur = -1

shards = ['shard0', 'shard1', 'shard2', 'shard3']
shards.reverse()

folder_path = sys.path[0] + '/' + config_update.folder_path
min_update_interval = config_update.min_update_interval
timeout_sec = config_update.timeout_sec

token = config_update.token
url = config_update.url
myheaders = config_update.myheaders


async def main():
    # portals = {}
    async with screeps_api_aiohttp.API(token=token,
                                       url=url,
                                       ssl=ssl_context,
                                       headers=myheaders,
                                       timeout=timeout_sec
                                       ) as api:
        for shard in shards:

            # 检查上次修改时间
            if os.path.exists(f"{folder_path}/{shard}.json"):
                last_modified = os.path.getmtime(f"{folder_path}/{shard}.json")
                if last_modified > int(time.time() - min_update_interval):
                    print(f"skipped {shard}")
                    continue

            print(f"getting data of {shard}")

            world_size = await api.world_size(shard=shard)
            farthest_size = int(math.floor(world_size['width'] // 10) / 2 * 10)
            # print(farthest_size)

            LT = f"W{farthest_size}N{farthest_size}"
            RB = f"E{farthest_size}S{farthest_size}"

            rooms = findRooms.getRoomsBetween(LT, RB)

            # print(rooms)

            def s123filter(roomName):
                # 只包含路口
                return re.match(r'.*0[NnSs]\d*0$', roomName) is not None

            def s0filter(roomName):
                # 包含路口及各十字方向拓展的2格
                return re.match(r'^[WwEe]\d*0[NnSs]\d*[89012]$|^[WwEe]\d*[89012][NnSs]\d*0$', roomName) is not None

            rooms = list(filter(s0filter if shard == 'shard0' else s123filter, rooms))

            # print(rooms)
            # print(len(rooms))

            global rooms_len_sum, rooms_len_cur
            rooms_len_sum = len(rooms)
            rooms_len_cur = len(rooms)

            semaphore = asyncio.Semaphore(3)  # 5非常容易过快，2比较保险

            async def show_progress_room_objects(room):
                async with semaphore:
                    global rooms_len_sum, rooms_len_cur
                    rooms_len_cur -= 1
                    print(f"{shard}: {rooms_len_sum - rooms_len_cur}/{rooms_len_sum}")
                    res = (await api.room_objects(room, shard))["objects"]
                    # print(res)
                    return res

            # room_objects = [(await api.room_objects(room, shard))["objects"] for room in rooms]
            # room_objects = [await show_progress_room_objects(room) for room in rooms]
            room_objects = await asyncio.gather(*[show_progress_room_objects(room) for room in rooms])

            def extract_portals(lst):
                return [item for sublist in lst for item in sublist if item["type"] == "portal"]

            def save_to_json_file(fileName, data):
                with open(fileName, 'w', encoding='utf8') as fp:
                    return json.dump(data, fp)

            save_to_json_file(f"{folder_path}/{shard}.json", extract_portals(room_objects))
            print(f"{shard} done")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
