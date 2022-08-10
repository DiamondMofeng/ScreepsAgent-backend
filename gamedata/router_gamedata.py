import hashlib
import json

# my server has some issue so i have to pass this ssl_context
import certifi
import ssl
from flask import Blueprint, request

from common import utils
from common.ENDPOINT_ERRORS import *

ssl_context = ssl.create_default_context(cafile=certifi.where())

# blue print is defined here
router_gamedata = Blueprint('gamedata', __name__)


# 建立
@router_gamedata.route("/api/gamedata/room-info", methods=['POST'])
def query_room_info_by_rooms_shard():
    r: dict = request.json
    if not utils.is_valid_str_dict(r, ['shard']):
        return ERR_WRONG_KEY_OR_VALUE
