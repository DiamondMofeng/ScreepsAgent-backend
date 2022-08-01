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
router_template = Blueprint('template', __name__)


# 建立
@router_template.route("", methods=['POST'])
def creat():
    pass
