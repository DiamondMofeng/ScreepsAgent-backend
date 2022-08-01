import json

from grafana_api.grafana_face import GrafanaFace

from host_agents.CONSTS import GRAFANA_URL, GRAFANA_ADMIN_PASSWORD, GRAFANA_ADMIN_USERNAME, INFLUXDB_URL


def grafana(username: str, password: str, dbTOKEN: str):
    api = GrafanaFace(auth=(GRAFANA_ADMIN_USERNAME, GRAFANA_ADMIN_PASSWORD), host=GRAFANA_URL)

    # 查找org,不存在则创建
    try:
        res_org = api.organization.find_organization(username)
        print("res_org1", res_org)
        orgid = res_org["id"]
    except:
        res_org = api.organization.create_organization(
            {
                "name": username
            }
        )
        print("res_org2:", res_org)
        orgid = res_org["orgId"]
    # print(res_org)
    print('orgid:', orgid)

    # 查找用户，不存在则创建并加入相应组织
    try:
        res_user = api.users.find_user(username)
    except:
        res_user = api.admin.create_user({
            "name": username,
            "login": username,
            "password": password,
            "OrgId": orgid
        }
        )
    # print(res_user)
    userid = res_user["id"]
    # 更改用户在组内权限
    api.organizations.organization_user_update(str(orgid), str(userid), "Admin")

    # 登录新建账号，以在其组织内建立数据源
    api = GrafanaFace(auth=(username, password), host=GRAFANA_URL)

    DATABASE_NAME = 'InfluxDB-' + username
    # 添加数据源
    try:
        datasource = api.datasource.get_datasource_by_name(DATABASE_NAME)
    except:

        datasource = api.datasource.create_datasource({
            "orgId": orgid,
            "name": DATABASE_NAME,
            "type": "influxdb",
            "typeLogoUrl": "",
            "access": "proxy",
            "url": INFLUXDB_URL,
            "database": username,
            "withCredentials": False,
            "isDefault": True,
            "jsonData": {
                "httpHeaderName1": "Authorization"
            },
            "secureJsonFields": {
                "httpHeaderValue1": True
            },
            "secureJsonData": {
                "httpHeaderValue1": "Token {}".format(dbTOKEN)
            }
        })


# print(user, org)

if __name__ == '__main__':
    # test
    grafana('Mofengg', '123456')
