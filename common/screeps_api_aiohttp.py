import asyncio
import math

import aiohttp

DEFAULT_SHARDS = ['shard0', 'shard1', 'shard2', 'shard3']
DEFAULT_SHARD = 'shard3'

OFFICIAL_URL = 'https://screeps.com/api'


class API:
    def __init__(self,
                 token: str = None,
                 url: str = None,
                 timeout: int or float = None,
                 ssl=None,
                 headers: dict = None,
                 **kwargs
                 ):
        """

        :param token:
        :param url:
        :param timeout:
        :param ssl:
        :param headers:
        :param kwargs:  args will be passed to aiohttp.ClientSession
        """
        self.token = token

        headers = headers or {}
        if token is not None:
            headers.update({'X-Token': token, 'X-Username': token})

        timeout = timeout or 60 * 30  # 30 minutes
        _timeout = aiohttp.ClientTimeout(timeout)

        self.url = OFFICIAL_URL if url is None else url

        self.ssl = ssl

        self.session = aiohttp.ClientSession(headers=headers, timeout=_timeout, **kwargs)

    def __enter__(self, **kwargs):
        raise TypeError('please use "async with" instead')

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.session.close()

    async def __aenter__(self, **kwargs):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # return self.session.__aexit__(exc_type, exc_val, exc_tb)
        return await self.session.close()

    # ===================basic methods

    async def get(self, url, **kwargs):
        async with self.session.get(self.url + url, params=kwargs, ssl=self.ssl) as res:
            # print(await res.text())
            try:
                return await res.json()
            except aiohttp.ContentTypeError:
                # print(await res.text())
                print('too fast, have a short sleep')
                await asyncio.sleep(2)

                return await self.get(url, **kwargs)  # TODO 尝试自动延迟

    async def post(self, url, **kwargs):
        async with self.session.post(self.url + url, json=kwargs, ssl=self.ssl) as res:
            # will raise Error if text type is not json
            try:
                return await res.json()
            except aiohttp.ContentTypeError:
                print(await res.text())

    # ====================/game/

    async def room_terrain(self, room, shard, encoded=1):
        return await self.get('/game/room-terrain', room=room, shard=shard, encoded=encoded)

    # ====================/game/map
    async def world_size(self, shard):
        return await self.get('/game/world-size', shard=shard)

    async def map_stats(self, rooms, shard, stat_name='claim0'):
        """ ** REQUIRE TOKEN

        :param rooms: a list of room names
        :param shard: shard name
        :param stat_name: stat name
        :return:
        """
        #
        return await self.post('/game/map-stats',
                               rooms=rooms,
                               shard=shard,
                               statName=stat_name)

    # ====================/game/room

    async def room_objects(self, room, shard):
        return await self.get('/game/room-objects',
                              room=room,
                              shard=shard)

    # ====================/user/

    async def user_find(self, username=None, user_id=None) -> any:
        """ *DO NOT REQUIRE TOKEN

        :param username:
        :param user_id:
        :return:
        """
        if username is not None:
            return await self.get('/user/find', username=username)
        if user_id is not None:
            return await self.get('/user/find', id=user_id)
        return False

    async def user_room(self, user_id, shard=DEFAULT_SHARD):
        """*DO NOT REQUIRE TOKEN

        :param user_id:
        :param shard:
        :return:
        """
        return await self.get('/user/rooms', id=user_id, shard=shard)

    # =====================Combos

    async def get_rooms_of_shard(self, shard):
        """*DO NOT REQUIRE TOKEN
        get room list of a shard

        :param shard:
        :return:
        """
        world_size = await self.world_size(shard)
        width = world_size['width']
        height = world_size['height']  # normally it is equal to width
        return [
            f'{WE}{x}{NS}{y}'
            for x in range(math.floor(width / 2))
            for y in range(math.floor(height / 2))
            for WE in ['W', 'E']
            for NS in ['N', 'S']
        ]

    async def get_player_room_dict(self, username: str, shards: list = None) -> dict:
        """*DO NOT REQUIRE TOKEN
         get all room of a player

        :param username:
        :param shards:
        :return: {shard_name:[room_names]}
        """
        # 获取玩家id
        user_id = (await self.user_find(username=username))['user']['_id']
        # 获取玩家所有房间
        user_rooms = (await self.user_room(user_id=user_id))['shards']
        return user_rooms

    async def get_player_room_objects_dict(self, username: str) -> dict:
        """*DO NOT REQUIRE TOKEN
        get room objects of a player's all rooms

        :param username:
        :return: {shard_name:{room_name:room_objects}}
        """

        # 获取玩家id
        user_id = (await self.user_find(username=username))
        user_id = user_id['user']['_id']
        # 获取玩家所有房间
        user_rooms = (await self.user_room(user_id=user_id))['shards']
        """
        {
            shard1:  {
                        room1:[room1_objs],
                        room2:[{obj1},{obj2}]
                    },
            shard2: {...}
        }
        """
        # below can be used in python 3.11, neither previous

        # res = {shard: {room: await self.room_objects(room=room, shard=shard) for room in shard_rooms} for
        #        shard, shard_rooms
        #        in
        #        user_rooms.items()}

        res = {
            shard: dict(zip(shard_rooms, [res['objects'] for res in (await asyncio.gather(
                *[self.room_objects(room=room, shard=shard)
                  for
                  room
                  in
                  shard_rooms]
            ))]))
            for
            shard, shard_rooms
            in
            user_rooms.items()
        }

        return res


if __name__ == '__main__':
    # for test
    async def main():
        async with API() as api:
            # mydict = await helper.get_player_room_objects_dict('Mofeng')
            t1 = await api.get_rooms_of_shard('shard0')
            print(t1)
            print(len(t1))


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

pass
