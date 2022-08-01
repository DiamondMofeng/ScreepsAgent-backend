import asyncio

import aiohttp

DEFAULT_SHARDS = ['shard0', 'shard1', 'shard2', 'shard3']
DEFAULT_SHARD = 'shard3'

OFFICIAL_URL = 'https://screeps.com/api'



class API:
    def __init__(self,
                 token=None,
                 url=None,
                 timeout: int or float = None,
                 ssl=None,
                 ):

        self.token = token

        headers = {} if token is None else {'X-Token': token, 'X-Username': token}

        timeout = timeout or 10.0
        _timeout = aiohttp.ClientTimeout(timeout)

        self.url = OFFICIAL_URL if url is None else url

        self.ssl = ssl

        self.session = aiohttp.ClientSession(headers=headers, timeout=_timeout)

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
            return await res.json()

    # ====================/game/

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
        async with API() as helper:
            mydict = await helper.get_player_room_objects_dict('Mofeng')
            print(mydict)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

pass
