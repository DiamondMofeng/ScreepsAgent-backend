import math
import re


def isValidStrDict(Dict: dict, keys: list):
    """
    检查Dict中是否存在所有的keys键且其值类型为str

    :param Dict: 要检查的字典
    :param keys: 要检查的键名列表
    :return:
    """
    if not isinstance(Dict, dict):
        return False
    for k in keys:
        if k not in Dict.keys() or not isinstance(Dict[k], str):
            return False
    return True


def is_valid_str_dict(*args):
    return isValidStrDict(*args)


def split_list_by_len(lst, n):
    """
    将列表按照每n个分成一组
    """
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def parseRoomName(roomName):
    """
    解析房间名
    :param roomName: 房间名
    :return: [ E/W , 坐标:int , N/S , 坐标:int ]
    """
    res = re.findall('([WwEeSsNn]|\\d+)', roomName)
    res[1] = int(res[1])
    res[3] = int(res[3])
    return res


def getRoomsBetween(fromRoom, toRoom):
    rooms = []
    # 处理房间参数为方便使用的格式
    fromRoom = parseRoomName(fromRoom)
    toRoom = parseRoomName(toRoom)

    # 简单判断房间参数是否合法
    if len(fromRoom) != 4 or len(toRoom) != 4:
        raise Exception('房间参数不合法')

    # 生成房间列表
    # 半截半截生成

    # 前半截
    pres = []
    if fromRoom[0] == toRoom[0]:
        for we in range(min(fromRoom[1], toRoom[1]), max(fromRoom[1], toRoom[1]) + 1):
            pres.append(fromRoom[0] + str(we))
    else:
        for we1 in range(fromRoom[1], -1, -1):
            pres.append(fromRoom[0] + str(we1))
        for we2 in range(0, toRoom[1] + 1):
            pres.append(toRoom[0] + str(we2))
    # 后半截
    for pre in pres:
        if fromRoom[2] == toRoom[2]:
            for ns in range(min(fromRoom[3], toRoom[3]), max(fromRoom[3], toRoom[3]) + 1):
                rooms.append(pre + (fromRoom[2] + str(ns)))
        else:
            for ns1 in range(0, fromRoom[3] + 1):
                rooms.append(pre + (fromRoom[2] + str(ns1)))
            for ns2 in range(0, toRoom[3] + 1):
                rooms.append(pre + (toRoom[2] + str(ns2)))

    return rooms


def getRoomsInRange(room, _range: int):
    """
    获取以room为中心的_range范围内的房间
    """
    # rooms = []
    parsedRoom: list = parseRoomName(room)

    toWS = parsedRoom[0]
    toWEInt = parsedRoom[1] - _range
    toNS = parsedRoom[2]
    toNSInt = parsedRoom[3] - _range
    if toWEInt < 0:
        toWEInt = -1 * toWEInt - 1
        toWS = 'E' if toWS == 'W' else 'W'
    if toNSInt < 0:
        toNSInt = -1 * toNSInt - 1
        toNS = 'S' if toNS == 'N' else 'N'

    fromRoom = parsedRoom[0] + str(parsedRoom[1] + _range) + parsedRoom[2] + str(parsedRoom[3] + _range)
    toRoom = toWS + str(toWEInt) + toNS + str(toNSInt)
    # print(fromRoom)
    # print(toRoom)
    return getRoomsBetween(fromRoom, toRoom)


def getRoomsByWorldSize(width, height):
    return [f'{WE}{x}{NS}{y}'
            for x in range(math.floor(width / 2))
            for y in range(math.floor(height / 2))
            for WE in 'WE'
            for NS in 'NS']


def isHighWay(roomName):
    # 坐标含有0即为高速路房
    return roomName.find('0') != -1


def isCenter(roomName):
    # 坐标末位 *同时* 为4、5、6即为中央房
    return re.match('^[WwEe]\\d*[4-6]+[NnSs]\\d*[4-6]+$', roomName) is not None


def isHighWayNeighbour(roomName):
    # 坐标末位 包含1或9即为 highway的邻居房
    # print(roomName, re.match('^[WwEe]\\d*[19]+[NnSs]|.*[19]$', roomName))
    return re.match('^[WwEe]\\d*[19]+[NnSs]|.*[19]$', roomName) is not None
