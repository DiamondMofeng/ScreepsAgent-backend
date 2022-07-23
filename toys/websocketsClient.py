# from base64 import b64decode
# from gzip import GzipFile
# from io import BytesIO, StringIO

import websockets
import asyncio
import json
import re

from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

GIVEN_URL = "wss://screeps.com/socket/631/6925pp1w/websocket"
DEFAULT_SHARD = "shard3"
OFFICIAL_HOST = 'screeps.com'
PTR_PREFIX = '/ptr'

'''
建立一个subscribe池。

创建subscribe时，扔进连接池。
使用on方法来监听这个subscribe的消息。
使用unsubscribe方法来取消这个subscribe。

subscribeOnce:
    创建一个subscribe，在成功监听一次后，取消这个subscribe。

'''


class Client:
    def __init__(self, token: str = None, email: str = None, password: str = None,

                 url: str = None,
                 host: str = None, prefix: str = None, secure: bool = True,
                 ptr: bool = False,

                 running_duration: float = -1,
                 running_forever: bool = False,
                 running_until_subscribe_is_empty: bool = False,

                 subscribeOnce: bool = False,
                 gzip: bool = False,
                 logging: bool = False,

                 concurrencyLimit: int = -1,
                 ):
        """

        :param token:
        :param email:
        :param password:

        :param url:                                 full websocket url to connect.

        :param host:                                hostname of the websocket server.
        :param prefix:                              if provided, host += prefix.
        :param ptr:                                 if True, when prefix is None, use PTR_PREFIX
        :param secure:                              if True, use 'wss' protocol, else use 'ws'

        :param subscribeOnce:                       if True, every subscription will auto unsubscribe after getting data

        :param running_forever:                     *Use running_duration = -1 instead*  if True, WS client will not exit because of running_duration.
        :param running_duration:                    default by -1, Ws client will never exit according to time.
                                                        if not set as -1, Ws client will exit after given Seconds.
        :param running_until_subscribe_is_empty:    if True, WS client will exit when every subscribe has run once.

        :param gzip:                                if True, data would be transferred in gz string. This may increase speed.
        """

        # init url
        self.url = url
        if url is None or not url.startswith('ws'):
            if host is None:
                self.url = GIVEN_URL
            else:
                prefix = PTR_PREFIX if ptr else prefix

                self.host = host
                self.prefix = prefix
                self.secure = secure

                self.url = 'wss://' if secure else 'ws://'  # wss:// or ws://
                self.url += host if host else OFFICIAL_HOST  # wss://screeps.com
                self.url += prefix if prefix else ''  # wss://screeps.com/ ?prefix
                self.url += '/socket/631/6925pp1w/websocket'  # wss://screeps.com/socket/631/6925pp1w/websocket # can be replaced with random number

        # auth info
        self.email = email
        self.password = password
        self.token = token
        self.userID = None

        # subscribe info
        self.pool = set()
        self.pool_once = set()
        self.pool_onSubscribe = set()
        self.pool_waiting = set()
        self.ws = None

        self.callbackPool = {}  # save subscribed channels' callback functions

        # configs
        self.concurrencyLimit = concurrencyLimit
        self.subscribeOnce = subscribeOnce
        self.gzip = gzip
        self.logging = logging

        # close condition
        self.running_forever = running_forever
        self.running_duration = running_duration
        self.running_until_subscribe_is_empty = running_until_subscribe_is_empty

    def get_token_from_login(self):
        # TODO not implemented
        if self.email is None or self.password is None:
            raise Exception('email or password is None')

    def parse_message(self, rawdata) -> list:
        """
        解析收到的消息。
        :param rawdata: a["message1", "message2", ...]
        :return:返回格式：[ message1, message2, ...]
                        subscribe模式下为
                        [ subscribeName , body : dict ]
        """

        # def __processGz(gzdata: str) -> str:
        #     """
        #     解压gzip数据。
        #     copy from python-screeps (https://github.com/screepers/python-screeps/)
        #     :param gzdata: "gz:foobar"
        #     """
        #
        #     return gzdata
        #     # TODO something wrong here, BadGzipFile Exception
        #     if not gzdata.startswith("gz:"):
        #         return gzdata
        #     gzip_input = BytesIO(b64decode(gzdata[3:]))
        #     print(gzdata[3:])
        #     print("gzinput:", gzip_input)
        #     gzip_string = GzipFile(fileobj=gzip_input).read().decode("utf-8")
        #     print(gzip_string)
        #     return json.loads(gzip_string)

        try:
            messageList: list = json.loads(rawdata[1:])  # 此时为["header,body"]
            if self.gzip:
                # print(messageList)
                # print(__processGz(messageList[0]))
                pass

            if '"' in messageList[0]:
                messageList = json.loads(messageList[0])
            # print(messageList)
            return messageList
            # subscribe模式下：
            # print(messageList[0])  # [0]为 subscribeName / header
            # print(messageList[1])  # [1]为 body,即subscribe的内容
            # 其他模式下：
            # 例: auth:
            # print(messageList[0])  # [0] : str : auth ok YourToken
        except json.JSONDecodeError:
            raise Exception(f"{rawdata} is not a valid message")
            # TODO something here?
            # return rawdata

    def process_message(self, message):
        """
        处理要发出的消息。
        :param message:
        :return: 可发送给ws服务器的消息格式:“[操作名 data]”
        """
        return json.dumps([message])

    # ============subscribe methods================

    def subscribe_user(self, watchpoint, userID=None, callBack=None):
        if userID is None and self.userID is None:
            if self.token is None or (self.email is None and self.password is None):
                raise Exception("user is required to subscribe user's watchpoint")
            else:
                # 获取token所有者的userID
                pass

        userID = userID if userID is not None else self.userID
        return self.subscribe(f"user:{userID}/{watchpoint}", callBack)

    def subscribe_roomMap(self, room, shard=DEFAULT_SHARD, callBack=None):
        return self.subscribe(f"roomMap2:{shard}/{room}", callBack)

    def subscribe_room(self, room, shard=DEFAULT_SHARD, callBack=None):
        return self.subscribe(f"room:{shard}/{room}", callBack)

    def subscribe(self, channel, callBack=None):
        if self.subscribeOnce:
            self.pool_once.add(channel)
        else:
            self.pool.add(channel)
        if callBack is not None:
            self.callbackPool[channel] = callBack

    # def subscribeOnce(self, channel):
    #     self.oncePool.add(f"subscribe {channel}")

    def unsubscribe(self, channel):
        self.pool.remove(channel)

    def onChannel(self, channel, callback):
        self.callbackPool[channel] = callback

    def isShouldEnd(self):
        if self.running_until_subscribe_is_empty and len(self.pool_once) == 0:
            self.log("======subscription pool is empty, should end======")
            return True
        if self.running_forever:
            return False
        if self.concurrencyLimit != -1 and len(self.pool_waiting) or len(self.pool_waiting) > 0:
            return False
        # if self.running_duration > 0:
        #     self.running_duration -= 1
        #     return False

    def __isOncePoolEmpty(self):
        return len(self.pool_once) == 0

    def parseRawdata(self, rawdata):
        """
        rawdata:
        :param rawdata:
        :return: response
        """
        if type(rawdata) != str:
            raise Exception("unknown message type")

        if rawdata[0] != "a":
            # 不考虑a以外的消息
            return

        messageList: list = self.parse_message(rawdata)
        # 通过msgList的长度来判断类型: 2则为subscribe类型,1则为普通消息.
        if len(messageList) == 1:
            # 普通消息
            """
            返回格式:
            {
                "type": "message",
                "data": message:str
            }
            """

            message = messageList[0]

            response = {
                "type": "message",
                "data": message
            }
            return response

        elif len(messageList) == 2:
            # subscribe类型
            """
            返回格式:
            {
                "type": "subscribe",
                "channel": "channel",
                "data": { data:dict }
            }
            """

            [channel, data] = messageList

            response = {
                "type": "subscribe",
                "channel": channel,
                "data": data
            }

            return response

        else:
            # print(messageList)
            raise Exception("unknown message type")

    def log(self, message):
        if self.logging:
            print(message)

    # ======methods on running =========

    async def __skip_connection_details(self, ws, CONNECTION_DETAILS_LENGTH=4):
        for _ in range(CONNECTION_DETAILS_LENGTH):
            rawdata = await ws.recv()
            self.log(f"↓ {rawdata}")

    async def __runtime_send(self, ws, message):
        await ws.send(self.process_message(message))

    async def __runtime_subscribe(self, ws, channel):
        self.log(f"↑ subscribe {channel}")
        await self.__runtime_send(ws, f"subscribe {channel}")

    async def __runtime_unsubscribe(self, ws, channel):
        self.log(f"↑ unsubscribe {channel}")
        await self.__runtime_send(ws, f"unsubscribe {channel}")

    async def __runtime_subscribe_all(self, ws):
        for channel in self.pool | self.pool_once:
            await self.__runtime_subscribe(ws, channel)

    async def __runtime_subscribe_until_reach_limit(self, ws):
        # TODO 未完成
        while len(self.pool_onSubscribe) < self.concurrencyLimit:
            channel = self.pool_waiting.pop()
            self.pool_onSubscribe.add(channel)
            await self.__runtime_subscribe(ws, channel)

    async def __runtime_do_all_subscribe_once(self, ws):
        pass

    async def __runtime_auth(self, ws):
        # Get token if None
        if self.token is None:
            if self.email is None or self.password is None:
                return "skip auth"
            else:
                pass

        await ws.send(self.process_message(f"auth {self.token}"))
        auth_response: str = await ws.recv()
        self.log(f"↓ {auth_response}")
        if auth_response.find("auth ok") != -1:
            return "auth ok"
        else:
            raise Exception("auth failed")

    async def __runtime_onReceiveRawData(self, ws, rawdata):
        response = self.parseRawdata(rawdata)
        channel = response["channel"]
        if channel in self.callbackPool:
            self.callbackPool[channel](response)
        if channel in self.pool_once:
            self.pool_once.remove(channel)
            await self.__runtime_unsubscribe(ws, channel)
        if channel in self.pool_onSubscribe:
            self.pool_onSubscribe.remove(channel)
            await self.__runtime_unsubscribe(ws, channel)
        pass

    async def __runtime_gzipOn(self, ws):
        # TODO currently broken
        # if self.gzip is True:
        #     await ws.send(self.process_message("gzip on"))
        pass

    def start(self):
        async def run():
            async with websockets.connect(self.url) as ws:

                await self.__skip_connection_details(ws,
                                                     CONNECTION_DETAILS_LENGTH=4)  # "o" "time" "protocol" "packages"

                await self.__runtime_auth(ws)

                await self.__runtime_gzipOn(ws)  # must be after auth

                # 订阅pool内的所有channel
                if self.concurrencyLimit == -1:
                    await self.__runtime_subscribe_all(ws)
                    self.log("======all channels are subscribed======")

                while True:

                    if self.concurrencyLimit != -1:
                        await self.__runtime_subscribe_until_reach_limit(ws)

                    if self.isShouldEnd():
                        return "should exit"

                    # TODO 待优化
                    try:
                        async def receiveData():
                            rawdata = await ws.recv()
                            self.log(f"↓ {rawdata}")
                            await self.__runtime_onReceiveRawData(ws, rawdata)

                        try:
                            await asyncio.wait_for(receiveData(), 100)
                        except asyncio.TimeoutError:
                            self.log("======长时间未收到新消息，退出======")
                            return "timeout"

                    except ConnectionClosedOK:
                        # pass
                        return "ConnectionClosedOK"

                    except ConnectionClosedError:
                        pass
                        # return "ConnectionClosedError"
            pass

        if self.running_duration != -1:
            async def runDuration():
                await asyncio.wait_for(run(), self.running_duration)

            try:
                asyncio.run(runDuration())
            except asyncio.TimeoutError:
                self.log("======stopped by running_duration======")
        else:
            asyncio.run(run())  # run forever


class Helper:
    @staticmethod
    def parse_channel(channel):
        """
        parse channel str to list
        :param channel: foo:bar/baz
        :return: [foo, bar, baz]
        """
        groups = re.match(r"^(.+):(.+?)(?:/(.+))?$", channel).groups()
        return [g for g in groups if g is not None]

    class get_channel:
        @staticmethod
        def room(room, shard):
            return f"room:{shard}/{room}"

        @staticmethod
        def roomMap2(room, shard):
            return f"roomMap2:{shard}/{room}"

        @staticmethod
        def user(userID, channel):
            return f"user:{userID}/{channel}"

    class roomMap_filter:
        @staticmethod
        def isTwoSourcesRoom(data: dict):
            if "s" not in data or type(data["s"]) != list:
                return False
            return len(data["s"]) == 2

    class room:
        @staticmethod
        def getGameObjsFromEvent(event):
            return event["data"]["objects"]

        @staticmethod
        def getRoomNameFromEvent(event):
            pass
            return

        class filter:
            @staticmethod
            def isLegacyRoom(event: dict):
                """
                是否是遗产房间
                现在不好界定。单纯认为留有storage、terminal、factory
                或
                :param event:
                :return:
                """
                legacyStructureTypes = ['storage', 'terminal', 'factory']
                objs: dict = Helper.room.getGameObjsFromEvent(event)
                # 若有指定类型的建筑且store不为空，则认为是遗产房间
                for obj in objs.values():
                    if obj["type"] in legacyStructureTypes and obj["store"] != {}:
                        return True
                # 若ruin的原型为指定类型且store不为空，则认为是遗产房间
                ruins = [obj for obj in objs.values() if obj["type"] == "ruin"]
                for ruin in ruins:
                    if ruin['structure']['type'] in legacyStructureTypes and 'store' in ruin["structure"] and \
                            ruin["structure"]['store'] != {}:
                        return True
                return False
