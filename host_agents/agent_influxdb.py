import json

import certifi
import requests
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from host_agents.CONSTS import INFLUXDB_PUBLIC_ORG, INFLUXDB_PUBLIC_ORG_ID, INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN, INFLUXDB_URL

'''
思路：
    不创建新用户了。
    而是为每个用户提供一个bucket，以用户名命名，
    对此bucket进行dbrp v1映射
    再返回对应bucket的    **只读**  token
    
    

'''

EXPIRE_SECONDS = 7776000


def influxdb(username: str):
    request_header = {"Authorization": "Token {}".format(INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN)}
    # print(request_header)
    # return
    url = INFLUXDB_URL
    dbTOKEN = INFLUXDB_PUBLIC_ORG_ADMIN_TOKEN
    org = INFLUXDB_PUBLIC_ORG

    with InfluxDBClient(url=url, token=dbTOKEN, org=org, certifi=certifi.where()) as client:
        auth_api = client.authorizations_api()
        bucket_api = client.buckets_api()

        # 创建bucket
        bkt = bucket_api.find_bucket_by_name(username)
        if bkt is None:
            bkt = bucket_api.create_bucket(bucket_name=username, org=INFLUXDB_PUBLIC_ORG, retention_rules={
                "type": "expire",
                "everySeconds": EXPIRE_SECONDS,
                "shardGroupDurationSeconds": 0
            })
        # print(bkt.id)
        # print(type(bkt))
        bktID = bkt.id
        ##########################################################
        # 进行v1映射
        dictToMap = {
            "bucketID": bktID,
            "database": username,
            "default": True,
            "org": INFLUXDB_PUBLIC_ORG,
            "orgID": INFLUXDB_PUBLIC_ORG_ID,
            "retention_policy": username
        }

        jsonToMap = json.dumps(dictToMap)
        # print(jsonToMap)
        # 查找
        url_find_dbrp = url + '/api/v2/dbrps?db={}&org=screeps'.format(username)
        dbrp_find_res = requests.get(url_find_dbrp, headers=request_header)
        # print(dbrp_find_res.text)
        dbrp_find_list = json.loads(dbrp_find_res.text)["content"]
        # print(dbrp_find_list)
        # print(dbrp_find_res.text)
        # print(dbrp_find_list)

        if len(dbrp_find_list) != 0:
            dbrp = dbrp_find_list[0]
        else:
            dbrp_post_res = requests.post(url + '/api/v2/dbrps', data=jsonToMap, headers=request_header)
            # print(dbrp_post_res.text)
            dbrp = json.loads(dbrp_post_res.text)
            # print(dbrp_post_dict)

        # '/api/v2/dbrps'
        ##########################################################
        # 返回token

        auth_find = auth_api.find_authorizations(org_id=INFLUXDB_PUBLIC_ORG_ID)

        def fil_by_description(auth_block):
            return auth_block.description == username

        filtered_auth = filter(fil_by_description, auth_find)
        list_auth = list(filtered_auth)
        print('================')
        # print(list_auth)
        if len(list_auth) != 0:
            auth = list_auth[0]
            # print(type(auth))
        else:
            auth_url = url + '/api/v2/authorizations'
            dictToAuth = {
                "description": username,
                "status": "active",
                "orgID": INFLUXDB_PUBLIC_ORG_ID,
                "permissions":
                    [
                        {
                            "action": "read",
                            "resource":
                                {
                                    "id": bktID,
                                    "org": INFLUXDB_PUBLIC_ORG,
                                    "orgID": INFLUXDB_PUBLIC_ORG_ID,
                                    "type": "buckets"
                                }
                        }
                    ],
            }
            jsonToAuth = json.dumps(dictToAuth)
            auth_res = requests.post(auth_url, data=jsonToAuth, headers=request_header)
            auth = json.loads(auth_res.text)

        # print(auth)

        return auth["token"] if isinstance(auth, dict) else auth.token


if __name__ == '__main__':
    print(influxdb('test5'))
