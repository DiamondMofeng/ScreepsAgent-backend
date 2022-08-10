import collections
import json


class Helper:
    class fromRoomObjDict:
        """
        from shard:room[]:room_obj[]
        """

        def __init__(self, roomObjDict):
            self.__roomObjDict: dict = roomObjDict

        def getResources(self):
            targetStructureTypes = ['terminal', 'storage', 'factory']
            result = {}
            for shard in self.__roomObjDict.values():
                for roomName, roomObjs in shard.items():
                    for obj in roomObjs:
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
                for roomName, roomObjsList in shardInfo.items():
                    walls = [
                        obj for obj in roomObjsList
                        if
                        obj['type'] in wallType
                        and
                        "hits" in obj  # novice walls do not have hits
                        and
                        obj['hits'] >= MIN_HITS_TO_COUNT
                    ]
                    result[shardName][roomName] = round(sum([wall['hits'] for wall in walls]) / len(walls)) if len(
                        walls) > 0 else 0
                    if unit == 'M':
                        result[shardName][roomName] = round(result[shardName][roomName] / 1e6, 2)

            # print(result)
            return result

    class fromRoomObjectsList:
        """
        from a list of a room's room-objects
        """

        def __init__(self, roomObjectsList):
            self.__roomObjectsList: list = roomObjectsList

        def get_static_room_info(self):
            """
            used for gamedata module

            source_position
            source_count
            controller_position
            mineral_position
            # mineral_type # do not need

            :return:
            """

            def getObjPosition(obj):
                return [obj['x'], obj['y']]

            result = {
                'source_position': [],
                'source_count': 0,
                'controller_position': [],
                'mineral_position': [],
            }
            for obj in self.__roomObjectsList:
                if obj['type'] == 'controller':
                    result['controller_position'].append(getObjPosition(obj))
                elif obj['type'] == 'source':
                    result['source_count'] += 1
                    result['source_position'].append(getObjPosition(obj))
                elif obj['type'] == 'mineral':
                    result['mineral_position'].append(getObjPosition(obj))
                    result['mineral_type'] = obj['mineralType']
            return result
