import json
import time
import sys

import screepsapi

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

                    api = screepsapi.API(token=screepsTOKEN)
                    stats = api.memory(memoryPath, shard)['data']
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
                except:
                    print(PLAYERNAME, shard, memoryPath, ' failed')
                    continue
