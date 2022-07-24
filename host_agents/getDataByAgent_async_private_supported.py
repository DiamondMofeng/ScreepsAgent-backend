import json
import time
import sys
import traceback
from base64 import b64decode
from gzip import GzipFile
from io import BytesIO

# import requests
import aiohttp

import certifi  # have to import certifi and ssl to solve server side problem
import ssl

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from tinydb import TinyDB

from CONSTS import DB_AGENT, INFLUXDB_URL, INFLUXDB_PUBLIC_ORG, INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN

import asyncio

DB_AGENT_ABSOLUTE_PATH = sys.path[0] + '/' + DB_AGENT

ssl_context = ssl.create_default_context(cafile=certifi.where())


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


async def fetchFromPrivate(agent, session: aiohttp.ClientSession):
    # 先获取临时token，再获取memory
    async with session.post(f'''{agent['private_url']}/api/auth/signin''',
                            data={'email': agent['private_username'],
                                  'password': agent['private_password']
                                  },
                            ssl=ssl_context) as res:
        if res.status == 401:
            raise Exception('401 not authorized')
        token = json.loads(await res.text())['token']
    async with session.post(f'''{agent['private_url']}/api/auth/signin''',
                            data={
                                "shard": agent['shard'],
                                "path": agent['path']
                            },
                            header={
                                "X-Token": token,
                                "X-Username": "foobar"
                            },
                            ssl=ssl_context) as res:
        return {
            "status_code": res.status,
            "text": await res.text()
        }


async def fetchFromOfficial(agent, session):
    async with session.get(
            f'https://screeps.com/api/user/memory?_token={agent["token"]}&shard={agent["shard"]}&path={agent["path"]}',
            ssl=ssl_context) as response:
        return {
            "status_code": response.status,
            "text": await response.text()
        }


async def getDataByAgent(agent, influxdbClient, aiohttpSession):
    try:
        # screepsTOKEN = agent["token"]
        memoryPath = agent["path"]
        shard = agent["shard"]
        PLAYERNAME = agent["username"]

        # res_stats = None
        private_enable = True if ('private_enable' in agent and agent['private_enable']) else False

        if private_enable is True:
            res_stats = await fetchFromPrivate(agent, aiohttpSession)

        else:
            res_stats = await fetchFromOfficial(agent, aiohttpSession)

        if res_stats["status_code"] == 401:
            raise Exception('401 not authorized')

        stats = json.loads(res_stats["text"])

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

        print('success',
              f"""{'screeps.com' if not private_enable else agent['private_url']} : {agent["username"]} {agent["shard"]} {agent["path"]} """)
    except Exception as e:
        print('failed',
              f"""{'screeps.com' if ('private_enable' not in agent or not agent['private_enable']) else agent['private_url']} : {agent["username"]} {agent["shard"]} {agent["path"]} """)
        print('Error:', e)
        traceback.print_exc()
    finally:
        pass


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


            async def asyncFetch():
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
                    for agent in db:
                        await getDataByAgent(agent, client, session)
                    # tasks = [getDataByAgent(agent, client, session) for agent in db]
                    # if len(tasks) > 0:
                    #     loop = asyncio.get_event_loop()
                    #     loop.run_until_complete(asyncio.wait(tasks))


            loop2 = asyncio.get_event_loop()
            loop2.run_until_complete(asyncFetch())
