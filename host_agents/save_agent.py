from tinydb import TinyDB, Query

from CONSTS import DB_AGENT


# 把数据存到数据库里即可

def saveAgent(username, screepsTOKEN, shard, path):
    db = TinyDB(DB_AGENT)
    db.insert(
        {
            'username': username,
            'token': screepsTOKEN,
            'shard': shard,
            'path': path,
        })

    # el = db.insert({"type": "peach", "count": 3})


if __name__ == '__main__':
    saveAgent('test', 'test', 'test', 'test')
