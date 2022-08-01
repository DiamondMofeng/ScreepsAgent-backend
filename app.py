from flask import Flask
from flask_cors import CORS
from host_agents.router_host_agents import router_hosted_agent

# 用flask做一个简单的http服务器
app = Flask(__name__)
CORS(app, supports_credentials=True)

# routers
app.register_blueprint(router_hosted_agent, url_prefix='/api/agents')

if __name__ == '__main__':
    print(app.url_map)
    app.run()
