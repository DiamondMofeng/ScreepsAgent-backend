# DB

The count of rooms in per shard is 10k order of magnitude, so I have to use some kind of DB supporting indexing to make it
efficient.  
I use sqlite3 here.

# Game data

存放一些我觉得有用的处理后的数据。

# 数据

## room stats

- 不变的数据：
    - sources 数量/位置
    - controller 位置
    - mineral 类型/位置

## room terrains

- 不变的数据：
    - terrain 基础地形
        - exit directions 出口方向
            - 方向：出口数
        - 地形覆盖率
            - 平原
            - 沼泽
            - 山地
  