import json

ERR_INVALID_PARAMS = json.dumps({"message": "Invalid parameters！"}), 403
ERR_INVALID = json.dumps({"message": "Unknown user！"}), 403
ERR_UNKNOWN_ENDPOINT = json.dumps({"message": "unknown endpoint"}), 400
ERR_WRONG_KEY_OR_VALUE = json.dumps({"message": "Wrong JSON Keys or values"}), 403
ERR_INVALID_LOGIN = json.dumps({"message": "Invalid login state！"}), 403
