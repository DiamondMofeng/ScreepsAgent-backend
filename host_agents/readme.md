# Mofeng的Screeps图表信息收集代理--后端

使用python的Flask框架作为基础。使用现成的screeps-api、grafana-api、influxdb-api模块帮助调用接口。   
后端的入口为app.py，定时使用getDataByAgent.py从tinyDB中获取代理数据，以访问官方接口并将memory/path中数据存入influxdb。

## 如何使用

先在服务器上部署grafana与influxdb

将CONSTS_SAMPLE.py中的信息替换成自己的信息，更名为CONSTS.py然后运行app.py即可。     
在服务器中新建一个定时任务调用getDataByAgent.py以为grafana提供数据。
 