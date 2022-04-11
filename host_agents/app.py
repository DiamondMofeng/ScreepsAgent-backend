import json
import hashlib

# import screepsapi
import requests

from agent_influxdb import influxdb
from agent_grafana import grafana
# from save_agent import saveAgent
from flask import Flask, request
from flask_cors import *
from tinydb import TinyDB, Query

from CONSTS import DB_USER, DB_AGENT, MD5_KEY_PASSWORD, MD5_KEY_LOGINTOKEN


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


def isValidStrDict(Dict, keys: list):
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


# from flask import request
# 用flask做一个简单的http服务器
# 输入：username,password,
app = Flask(__name__)
CORS(app, supports_credentials=True)


# 登录

@app.route("/api/login", methods=['POST'])
def login():
    if request.method == 'POST':
        # print(request.json)
        # print(type(request.json))
        login = request.json  # dict

        if not isinstance(login, dict) \
                or 'username' not in login.keys() \
                or 'password' not in login.keys() \
                or not isinstance(login['username'], str) \
                or not isinstance(login['password'], str):
            return ERR_WRONG_KEY_OR_VALUE

        else:
            username = login["username"]
            password = login["password"]

            with TinyDB(DB_USER) as db:

                query = db.search(Query().fragment(
                    {
                        'username': username,
                        "password": md5(password)
                    }
                ))

                # print(query)

                if len(query) == 1:
                    user = query[0]
                    return json.dumps({
                        "message": "登陆成功！",
                        "user": {
                            "name": user["username"],
                            "loginTOKEN": user["loginTOKEN"]
                        }
                    }), 200
                else:
                    return json.dumps({
                        "message": "Unknown user！"}
                    ), 403

    return ERR_UNKNOWN_ENDPOINT


@app.route("/api/user", methods=['POST'])
def register():
    if request.method == 'POST':
        signup = request.json  # dict
        print(signup)
        if not isinstance(signup, dict) \
                or 'username' not in signup.keys() \
                or 'password' not in signup.keys() \
                or not isinstance(signup['username'], str) \
                or not isinstance(signup['password'], str):
            return ERR_WRONG_KEY_OR_VALUE

        else:
            username = signup["username"]
            password = signup["password"]

            with TinyDB(DB_USER) as db:
                # user = Query()
                # db.search(user["username"] == username)
                query = db.search(Query().fragment({'username': username}))
                if len(query) != 0:
                    return json.dumps({"message": "This User Has Already Registered"}), 403
                else:

                    dbTOKEN = influxdb(username)

                    grafana(username, password, dbTOKEN)

                    db.insert({"username": username,
                               "password": md5(password),
                               "loginTOKEN": md5_token(password),
                               "dbTOKEN": dbTOKEN})
                    return json.dumps({"message": "注册成功！"}), 201

    return ERR_UNKNOWN_ENDPOINT


# 建立Agent
@app.route("/api/agents", methods=['POST'])
def creat_agent():
    if request.method == 'POST':
        print(request.json)
        print(type(request.json))
        agent = request.json

        if not isinstance(agent, dict) \
                or 'username' not in agent.keys() \
                or 'loginTOKEN' not in agent.keys() \
                or 'token' not in agent.keys() \
                or 'path' not in agent.keys() \
                or 'shard' not in agent.keys() \
                or not isinstance(agent['username'], str) \
                or not isinstance(agent['loginTOKEN'], str) \
                or not isinstance(agent['token'], str) \
                or not isinstance(agent['path'], str) \
                or not isinstance(agent['shard'], str):
            return ERR_WRONG_KEY_OR_VALUE

        # 验证当前登录是否有效
        with TinyDB(DB_USER) as db:
            query = db.search(Query().fragment(
                {
                    'username': agent["username"],
                    "loginTOKEN": agent["loginTOKEN"]
                }
            ))
            if len(query) == 0:
                return json.dumps({"message": "验证登录失败！"}), 403

        # 验证数据是否有效

        r = requests.get(
            url=f'''https://screeps.com/api/user/memory?_token={agent['token']}&shard={agent['shard']}&path={agent['path']}''')
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
            db.insert(newAgent)
            return json.dumps(newAgent), 201

    return ERR_UNKNOWN_ENDPOINT


# 以用户名查找agent
@app.route("/api/agents", methods=['GET'])
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
            print(query)
            return json.dumps(query), 200

    return ERR_UNKNOWN_ENDPOINT


# 以agentID删除agent
@app.route("/api/deleteAgent", methods=['POST'])
def delete_agent_by_agentID():
    if request.method == "POST":

        req_dict = request.json
        print(type(req_dict), req_dict)
        if not isValidStrDict(req_dict, ['username', 'loginTOKEN', 'token', 'shard', 'path']):
            return ERR_WRONG_KEY_OR_VALUE

        username = req_dict["username"]
        loginTOKEN = req_dict["loginTOKEN"]
        token = req_dict["token"]
        shard = req_dict["shard"]
        path = req_dict["path"]

        # 验证登录有效性
        if not isValidLoginTOKEN(DB_USER, username, loginTOKEN):
            return ERR_INVALID_LOGIN

        with TinyDB(DB_AGENT) as db:
            query = db.search(Query().fragment({'username': username, 'token': token, 'path': path, 'shard': shard}))
            if len(query) == 0:
                return json.dumps({"message": "agentID not found"}), 404
            elif len(query) >= 1:
                db.remove(Query().fragment({'username': username, 'token': token, 'path': path, 'shard': shard}))
                return json.dumps({"message": "delete success"}), 200
            else:
                print('unknown error')
                return ERR_UNKNOWN_ENDPOINT

    return ERR_UNKNOWN_ENDPOINT


if __name__ == '__main__':
    app.run()
