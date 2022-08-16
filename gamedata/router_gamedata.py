import hashlib
import json

# my server has some issue so i have to pass this ssl_context
import certifi
import ssl
from flask import Blueprint, request
import requests
from common import utils
from common.ENDPOINT_ERRORS import *
from gamedata import config_gamedata as config
from gamedata import db_services

ssl_context = ssl.create_default_context(cafile=certifi.where())

# blue print is defined here
router_gamedata = Blueprint('gamedata', __name__)


# 查询room-info
@router_gamedata.route("/api/gamedata/rooms-info", methods=['POST'])
def query_room_info_by_rooms_shard_and_rules():
    r: dict = request.json
    if 'rooms' not in r or 'shard' not in r:
        return ERR_INVALID_PARAMS

    if not utils.is_valid_rooms_list(r['rooms']) or not utils.is_valid_shard(r['shard']):
        return ERR_INVALID_PARAMS

    # 查询room-info

    # 按条件查询
    # if 'rules' in r:
    #     rules = r['rules']

    # 直接查询
    return json.dumps(db_services.rooms_info(r['rooms'], r['shard'])), 200


# 获取临时token
@router_gamedata.route("/api/gamedata/temp-token", methods=['GET'])
def get_temp_token():
    try:
        res = requests.post('https://screeps.com/api/auth/signin', json={
            'email': config.TEMP_TOKEN_USERNAME,
            'password': config.TEMP_TOKEN_PASSWORD
        })
        token = res.json()['token']
        return json.dumps({'token': token}), 200
    except Exception as e:
        print(res,res.text)
