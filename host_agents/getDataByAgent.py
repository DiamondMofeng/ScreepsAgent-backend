import json
import time
import sys
import traceback
from base64 import b64decode
from gzip import GzipFile
from io import BytesIO

import requests

import certifi

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from tinydb import Query, TinyDB

from CONSTS import DB_AGENT, \
    INFLUXDB_URL, INFLUXDB_PUBLIC_ORG, INFLUXDB_PUBLIC_ORG_ID, INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN

DB_AGENT_ABSOLUTE_PATH = sys.path[0] + '/' + DB_AGENT


def deepDictToJSON(Dict: dict):
    for k, v in Dict.items():
        if isinstance(v, dict):
            Dict[k] = json.dumps(v)
    return Dict


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
            for agent in db:
                try:
                    screepsTOKEN = agent["token"]
                    memoryPath = agent["path"]
                    shard = agent["shard"]
                    PLAYERNAME = agent["username"]

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
                    
                    measurement = PLAYERNAME

                    data = {
                        "measurement": measurement,
                        "tags": {
                            "shard": shard,
                            "path": memoryPath,
                        },
                        "fields": stats,

                    }

                    bucket = PLAYERNAME

                    write_api = client.write_api(write_options=SYNCHRONOUS)
                    write_api.write(bucket, org, data)
                    print(PLAYERNAME, shard, memoryPath, ' success')
                except Exception as e:
                    print(PLAYERNAME, shard, memoryPath, ' failed')
                    print('Error:', e)
                    traceback.print_exc()
