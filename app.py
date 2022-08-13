from flask import Flask
from flask_cors import CORS

from host_agents.router_host_agents import router_hosted_agent
from portals.router_portals import router_portals
from gamedata.router_gamedata import router_gamedata

# 用flask做一个简单的http服务器
app = Flask(__name__)
CORS(app, supports_credentials=True)

# routers

# app.register_blueprint(router_hosted_agent, url_prefix='/api/agents')
app.register_blueprint(router_hosted_agent)  # api/agents    user    login
app.register_blueprint(router_portals)  # api/portals
app.register_blueprint(router_gamedata)  # api/gamedata

if __name__ == '__main__':
    print(app.url_map)
    app.run()
