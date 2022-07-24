import json
import time
import sys
import traceback
from base64 import b64decode
from gzip import GzipFile
from io import BytesIO

import requests

import certifi

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from tinydb import TinyDB

from CONSTS import DB_AGENT, INFLUXDB_URL, INFLUXDB_PUBLIC_ORG, INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN

import asyncio

DB_AGENT_ABSOLUTE_PATH = sys.path[0] + '/' + DB_AGENT

global PLAYERNAME, shard, memoryPath


def deepDictToJSON(Dict: dict):
    for k, v in Dict.items():
        if isinstance(v, dict):
            Dict[k] = json.dumps(v)
    return Dict


def intInDictToFloat(Dict: dict):
    for k, v in Dict.items():
        if isinstance(v, int):
            Dict[k] = float(v)
    return Dict


async def getDataByAgent(agent, influxdbClient):
    global PLAYERNAME, shard, memoryPath
    try:
        screepsTOKEN = agent["token"]
        memoryPath = agent["path"]
        shard = agent["shard"]
        PLAYERNAME = agent["username"]

        # res_stats = None
        private_enable = False
        if 'private_enable' in agent and agent['private_enable'] is True:
            private_enable = True
            # 私服
            privateUrl = agent['private_url']
            # 获取临时token
            res_signin = requests.post(f'{privateUrl}/api/auth/signin',
                                       json={
                                           'email': agent['private_username'],
                                           'password': agent['private_password']
                                       },
                                       timeout=10)
            if res_signin.status_code == 401:
                raise Exception('401 not authorized')

            res_stats = requests.get(f'''{agent['private_url']}/api/user/memory''',
                                     {
                                         "shard": agent['shard'],
                                         "path": agent['path']
                                     },
                                     headers={
                                         "X-Token": json.loads(res_signin.text)['token'],
                                         "X-Username": "foobar"
                                     },
                                     timeout=10)
        else:
            # 官服
            res_stats = requests.get(
                f'https://screeps.com/api/user/memory?_token={screepsTOKEN}&shard={shard}&path={memoryPath}',
                timeout=10)
        if res_stats.status_code == 401:
            raise Exception('401 not authorized')

        stats = json.loads(res_stats.text)

        # 解读gz
        if 'data' not in stats:
            raise Exception('There is no data in stats')

        gzip_input = BytesIO(b64decode(stats['data'][3:]))
        gzip_string = GzipFile(fileobj=gzip_input).read().decode("utf-8")
        stats['data'] = json.loads(gzip_string)

        stats = stats['data']
        # 拼接数据

        stats = deepDictToJSON(stats)
        stats = intInDictToFloat(stats)

        measurement = PLAYERNAME

        data = {
            "measurement": measurement,
            "tags": {
                "shard": shard,
                "path": memoryPath,
                "server": "screeps.com" if not private_enable else agent['private_url'][
                                                                   agent['private_url'].find('//') + 2:]
            },
            "fields": stats,

        }

        bucket = PLAYERNAME

        write_api = influxdbClient.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket, org, data)

        print('success', f"{privateUrl if private_enable else 'screeps.com'} : {PLAYERNAME} {shard} {memoryPath} ")
    except Exception as e:
        print('failed', f"{privateUrl if private_enable else 'screeps.com'} : {PLAYERNAME} {shard} {memoryPath} ")
        print('Error:', e)
        traceback.print_exc()


if __name__ == '__main__':
    tm = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print('==========' + tm + "==========")
    url = INFLUXDB_URL
    dbTOKEN = INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN
    org = INFLUXDB_PUBLIC_ORG

    with InfluxDBClient(url=url, token=dbTOKEN, org=org, certifi=certifi.where()) as client:
        print('InfluxDB Client connected')

        with TinyDB(DB_AGENT_ABSOLUTE_PATH) as db:
            print('TinyDB connected')
            tasks = [getDataByAgent(agent, client) for agent in db]
            if len(tasks) > 0:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.wait(tasks))
