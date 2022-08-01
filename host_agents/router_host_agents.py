import hashlib
import json
import ssl

# my server has some issue so i have to pass this ssl_context
import certifi
# import screepsapi
import requests
from flask import Blueprint
from flask import request
from tinydb import TinyDB, Query

from host_agents.CONSTS import DB_USER, DB_AGENT, MD5_KEY_PASSWORD, MD5_KEY_LOGINTOKEN

ssl_context = ssl.create_default_context(cafile=certifi.where())

# blue print is defined here
router_hosted_agent = Blueprint('hosted_agent', __name__)


def md5(string):
    _md5 = hashlib.md5(bytes(MD5_KEY_PASSWORD, encoding='utf-8'))
    _md5.update(string.encode(encoding='utf-8'))
    return _md5.hexdigest()


def md5_token(string):
    _md5 = hashlib.md5(bytes(MD5_KEY_LOGINTOKEN, encoding='utf-8'))
    _md5.update(string.encode(encoding='utf-8'))
    return _md5.hexdigest()


ERR_INVALID = json.dumps({"message": "Unknown user！"}), 403
ERR_UNKNOWN_ENDPOINT = json.dumps({"message": "unknown endpoint"}), 400
ERR_WRONG_KEY_OR_VALUE = json.dumps({"message": "Wrong JSON Keys or values"}), 403
ERR_INVALID_LOGIN = json.dumps({"message": "Invalid login state！"}), 403


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


def isValidLoginTOKEN(DB_USER, username, loginTOKEN):
    # 验证当前登录是否有效
    with TinyDB(DB_USER) as db:
        query = db.search(Query().fragment(
            {
                'username': username,
                "loginTOKEN": loginTOKEN
            }
        ))
        if len(query) == 1:
            return True
        else:
            return False


# 建立Agent
@router_hosted_agent.route("", methods=['POST'])
def creat_agent():
    if request.method == 'POST':
        # print(request.json)
        # print(type(request.json))
        agent: dict = request.json

        if not isValidStrDict(agent, ['username', 'loginTOKEN', 'token', 'path', 'shard']):
            return ERR_WRONG_KEY_OR_VALUE

        # 验证当前登录是否有效
        if not isValidLoginTOKEN(DB_USER, agent["username"], agent["loginTOKEN"]):
            return ERR_INVALID_LOGIN

        # 考虑私服的情况
        isPrivate = False
        if "private_enable" in agent.keys() and agent["private_enable"] is True:
            if not isValidStrDict(agent, ["private_url",
                                          "private_username",
                                          "private_password"
                                          ]):  # 键名 暂定为private_enable、private_url、private_username、private_password # url最后不要加斜杠/
                return ERR_WRONG_KEY_OR_VALUE
            isPrivate = True

        # 获取数据
        r = None
        if isPrivate:
            # print(agent)
            tempTokenReq = requests.post(f'''{agent["private_url"]}/api/auth/signin''',
                                         json={
                                             "email": agent["private_username"],
                                             "password": agent["private_password"]
                                         }, timeout=10)
            # print(tempTokenReq.url)
            # print(tempTokenReq.text)
            if tempTokenReq.status_code != 200:
                return json.dumps({"message": "私服登录信息有误"}), 403
            tempToken = tempTokenReq.json()["token"]
            r = requests.get(f'''{agent["private_url"]}/api/user/memory''',
                             {
                                 "shard": agent['shard'],
                                 "path": agent['path']
                             },
                             headers={
                                 "x-token": tempToken,
                                 "x-username": "foobar"
                             }, timeout=10)
            pass
        else:
            r = requests.get(
                url=f'''https://screeps.com/api/user/memory?_token={agent['token']}&shard={agent['shard']}&path={agent['path']}''',
                timeout=10)
        # 验证数据是否有效
        if r.status_code != 200:
            return json.dumps({"message": "invalid args"}), 403

        res_dict = r.json()
        if 'error' in res_dict.keys():
            return json.dumps({"message": "参数输入有误"}), 403

        if 'data' not in res_dict.keys():
            return json.dumps({"message": "token正确但path下无数据"}), 403

        # 加入agents数据库
        with TinyDB(DB_AGENT) as db:
            newAgent = {
                "username": agent["username"],
                "token": agent["token"],
                "path": agent["path"],
                "shard": agent["shard"],
            }
            newAgent.update({
                'id': db.all()[- 1]['id'] + 1
            })
            if isPrivate:
                newAgent.update({
                    "private_enable": agent["private_enable"],
                    "private_url": agent["private_url"],
                    "private_username": agent["private_username"],
                    "private_password": agent["private_password"],
                })
            db.insert(newAgent)
            return json.dumps(newAgent), 201

    return ERR_UNKNOWN_ENDPOINT


# 以用户名查找agent
@router_hosted_agent.route("", methods=['GET'])
def get_agents_by_username():
    if request.method == "GET":

        req_dict = request.values.to_dict()
        # print(type(req_dict), req_dict)
        if not isValidStrDict(req_dict, ['username', 'loginTOKEN']):
            return ERR_WRONG_KEY_OR_VALUE

        username = req_dict["username"]
        loginTOKEN = req_dict["loginTOKEN"]

        # 验证登录有效性
        if not isValidLoginTOKEN(DB_USER, username, loginTOKEN):
            return ERR_INVALID_LOGIN

        # 查询对应agent
        with TinyDB(DB_AGENT) as db:
            query = db.search(Query().fragment({'username': username}))
            # print(query)
            return json.dumps(query), 200

    return ERR_UNKNOWN_ENDPOINT


@router_hosted_agent.route("/<int:_id>", methods=['DELETE'])
def delete_agent_by_agentID(_id):
    if request.method != 'DELETE':
        return
    # 从header获得验证信息，并验证登录
    header_dict = dict(request.headers)
    if not isValidStrDict(header_dict, ['X-Token', 'X-Username']):
        return ERR_INVALID_LOGIN
    if not isValidLoginTOKEN(DB_USER, header_dict['X-Username'], header_dict['X-Token']):
        print(header_dict['X-Username'], header_dict['X-Token'])
        return ERR_INVALID_LOGIN

    # 验证要删除数据的所有权
    with TinyDB(DB_AGENT) as db:
        to_delete = db.search(Query().fragment({'id': _id}))

        if len(to_delete) > 1:
            return ERR_UNKNOWN_ENDPOINT
        elif len(to_delete) == 0:
            return json.dumps({'message': 'failed to find, maybe have been deleted'}), 200

        to_delete = to_delete[0]
        if to_delete['username'] != header_dict['X-Username']:
            return ERR_INVALID_LOGIN

        # 验证完毕，进行删除
        db.remove(Query().fragment({"id": _id}))
        return json.dumps({"message": "successfully deleted"}), 200

    # return ERR_UNKNOWN_ENDPOINT
