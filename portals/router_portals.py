import hashlib
import json
import re
import ssl

import os
# my server has some issue so i have to pass this ssl_context
import certifi
# import screepsapi
import requests
from flask import Blueprint
from flask import request
from tinydb import TinyDB, Query

from host_agents.CONSTS import DB_USER, DB_AGENT, MD5_KEY_PASSWORD, MD5_KEY_LOGINTOKEN
from common.ENDPOINT_ERRORS import *

from portals.find_route import find_route

ssl_context = ssl.create_default_context(cafile=certifi.where())

# blue print is defined here
router_portals = Blueprint('template', __name__)


# 查询某个shard的portal信息
@router_portals.route("/api/portals", methods=['GET'])
def get():
    if request.method != 'GET':
        return ERR_UNKNOWN_ENDPOINT
    if "shard" not in request.args or re.match(r"^(shard)[0-3]$", request.args["shard"]) is None:
        return ERR_INVALID_PARAMS

    pass


@router_portals.route("/api/portals/fr", methods=['GET', 'POST'])
@router_portals.route("/api/portals/find_route", methods=['GET', 'POST'])
def find_portal_route():
    try:
        if request.method == "GET":
            _from, _to = request.args["from"], request.args["to"]
        elif request.method == "POST":
            req_body = request.json
            _from, _to = req_body["from"], req_body["to"]
        else:
            return ERR_UNKNOWN_ENDPOINT  # 加这个else只是为了编译器不报warning

        # 检查输入的from和to是否合法
        re_check_from_to = r"^(shard)[0-3]_[WE]\d+[NS]\d+$"
        if re.match(re_check_from_to, _from) is None or re.match(re_check_from_to, _to) is None:
            print(re.match(re_check_from_to, _from))
            print(re.match(re_check_from_to, _to))
            return ERR_INVALID_PARAMS
    except Exception as e:
        '''either KeyError or BadRequestKeyError'''
        return ERR_INVALID_PARAMS
    return find_route(_from, _to)

    pass
