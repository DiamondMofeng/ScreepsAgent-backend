import screepsapi
from toys import websocketsClient, SECRETS

token = SECRETS.token

SHARDS = ["shard0", "shard1", "shard2", "shard3"]

api = screepsapi.API(token=token)
socket = websocketsClient.Client()


class Detector:

    # def __init__(self, token):
    #     self.token = token

    class fromRoomObjDict:

        def __init__(self, roomObjDict):
            self.__roomObjDict: dict = roomObjDict

        def getResources(self):
            targetStructureTypes = ['terminal', 'storage', 'factory']
            result = {}
            for shard in self.__roomObjDict.values():
                for roomName, roomObjs in shard.items():
                    for objID, obj in roomObjs.items():
                        if obj['type'] in targetStructureTypes:
                            for resourceType in obj['store']:
                                if resourceType not in result:
                                    result[resourceType] = 0
                                result[resourceType] += obj['store'][resourceType]

            # result = dict([(k, result[k]) for k in sorted(result.keys())])  # 根据键名排序
            # print(result)
            return result

        def getWallThickness(self, MIN_HITS_TO_COUNT=1e6, unit='M'):
            """

            :param MIN_HITS_TO_COUNT:   耐久小于此数字的墙 不计入
            :param unit:
            :return:
            """
            wallType = ['rampart', 'constructedWall']
            result = {}
            for shardName, shardInfo in self.__roomObjDict.items():
                result[shardName] = {}
                for roomName, roomObjsDict in shardInfo.items():
                    walls = [
                        roomObjsDict[objID] for objID in roomObjsDict
                        if
                        roomObjsDict[objID]['type'] in wallType
                        and
                        "hits" in roomObjsDict[objID]  # novice walls do not have hits
                        and
                        roomObjsDict[objID]['hits'] >= MIN_HITS_TO_COUNT
                    ]
                    result[shardName][roomName] = round(sum([wall['hits'] for wall in walls]) / len(walls)) if len(
                        walls) > 0 else 0
                    if unit == 'M':
                        result[shardName][roomName] = round(result[shardName][roomName] / 1e6, 2)

            # print(result)
            return result

    @staticmethod
    def getPlayerRoomDict(playerName):
        # 获取玩家id
        playerId = api.user_find(username=playerName)['user']['_id']
        # 获取玩家所有房间
        roomsRep = api.user_rooms(user_id=playerId)

        roomsDict = roomsRep['shards']  # 格式:{shardName:[roomNameList]}
        return roomsDict

    @staticmethod
    def getPlayerRoomObjectsDict(playerName):
        """

        :param playerName: 玩家名
        :return:{
                shard:  {
                        roomName:   {
                                    objID:  {
                                                #objInfo here
                                            "_id":"..."
                                            "type":"..."
                                            }
                                    }
                        }
                }
        """
        roomsDict = Detector.getPlayerRoomDict(playerName)
        ws = websocketsClient.Client(token=token, subscribeOnce=True, running_until_subscribe_is_empty=True,
                                     logging=False)
        data = {}

        for shard in roomsDict:
            data[shard] = {}
            for room in roomsDict[shard]:
                channel = websocketsClient.Helper.get_channel.room(room=room, shard=shard)
                ws.subscribe(channel)

                # ?IDK why closure is not work, I have to write this way
                ws.onChannel(channel, lambda event, _shard=shard, _room=room: data[_shard].update(
                    {_room: event['data']['objects']}))
        ws.start()
        return data

    @staticmethod
    def getPlayerResources(playerName):

        targetStructureTypes = ['terminal', 'storage', 'factory']

        roomsDict = Detector.getPlayerRoomDict(playerName)

        ws = websocketsClient.Client(token=token, subscribeOnce=True, running_until_subscribe_is_empty=True,
                                     logging=False)
        data = []
        for shard in roomsDict:
            for room in roomsDict[shard]:
                channel = websocketsClient.Helper.get_channel.room(room=room, shard=shard)
                ws.subscribe(channel)
                ws.onChannel(channel, lambda event: data.append(event))
        ws.start()

        result = {}
        for event in data:
            for objID in event['data']['objects']:
                obj = event['data']['objects'][objID]
                # print(event['data']['objects'])
                if obj['type'] in targetStructureTypes:
                    for resourceType in obj['store']:
                        if resourceType not in result:
                            result[resourceType] = 0
                        result[resourceType] += obj['store'][resourceType]

        # result = dict([(k, result[k]) for k in sorted(result.keys())])  # 根据键名排序
        # print(result)
        return result

    @staticmethod
    def getPlayerWallThickness(playerName, unit=None):
        """
        获取玩家各房间墙的平均厚度
        :param playerName:
        :param unit: 默认为None，可设置为'M'，结果将 / 1e6
        :return:
        """
        wallType = ['rampart', 'constructedWall']
        MIN_HITS_TO_COUNT = 1e6  # 小于1M的墙不计入
        result = {}
        roomsDict = Detector.getPlayerRoomDict(playerName)
        ws = websocketsClient.Client(token=token, subscribeOnce=True, running_until_subscribe_is_empty=True,
                                     logging=True)
        data = []
        for shard in roomsDict:
            for room in roomsDict[shard]:
                result[shard] = {} if shard not in result else result[shard]
                result[shard][room] = 0
                channel = websocketsClient.Helper.get_channel.room(room=room, shard=shard)
                ws.subscribe(channel)
                ws.onChannel(channel, lambda event: data.append(event))
        ws.start()
        for event in data:
            parsedChannel = websocketsClient.Helper.parse_channel(event['channel'])
            shard = parsedChannel[1]
            roomName = parsedChannel[2]
            walls = [
                event['data']['objects'][objID] for objID in event['data']['objects']
                if
                event['data']['objects'][objID]['type'] in wallType
                and
                event['data']['objects'][objID]['hits'] >= MIN_HITS_TO_COUNT
            ]
            result[shard] = {} if shard not in result else result[shard]
            result[shard][roomName] = sum([wall['hits'] for wall in walls]) / len(walls) if len(walls) > 0 else 0
            if unit == 'M':
                result[shard][roomName] = round(result[shard][roomName] / 1e6, 2)

        # print(result)
        return result


if __name__ == '__main__':

    api = screepsapi.API(token=token)
    # 要获取战斗力的玩家名(大小写均可)
    playerNameList = ['Mofeng']

    for playerName in playerNameList:
        roomObjDict = Detector.getPlayerRoomObjectsDict(playerName)
        # print(roomObjDict)
        print(Detector.fromRoomObjDict(roomObjDict).getWallThickness(unit=''))
        print(Detector.fromRoomObjDict(roomObjDict).getResources())
        # print(f"=====info of {playerName}=====")
        # print(f"{playerName}的物资储量")
        # print(Detector.getPlayerResources(playerName))
        # print(f"{playerName}的平均墙厚度")
        # print(Detector.getPlayerWallThickness(playerName, 'M'))
