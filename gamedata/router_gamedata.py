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

ssl_context = ssl.create_default_context(cafile=certifi.where())

# blue print is defined here
router_gamedata = Blueprint('gamedata', __name__)


# 查询room-info
@router_gamedata.route("/api/gamedata/room-info", methods=['POST'])
def query_room_info_by_rooms_shard_and_rules():
    r: dict = request.json
    if not utils.is_valid_str_dict(r, ['shard']):
        return ERR_WRONG_KEY_OR_VALUE


# 获取临时token
@router_gamedata.route("/api/gamedata/temp-token", methods=['GET'])
def get_temp_token():
    token = requests.post('https://screeps.com/api/auth/signin', json={
        'email': config.TEMP_TOKEN_USERNAME,
        'password': config.TEMP_TOKEN_PASSWORD
    }).json()['token']
    return json.dumps({'token': token}), 200
