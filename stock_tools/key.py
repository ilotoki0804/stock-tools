import json
import logging
import os

if os.path.exists("keys.json"):
    path = "keys.json"
elif os.path.exists("_keys.json"):
    path = "_keys.json"
else:
    path = None


if path is None:
    logging.error(
        "'keys.json' or '_keys.json' is not found. In order to use KEY, root directory should contain 'keys.json'."
    )
    KEY = {}
    OTHER_ENV = {}
else:
    with open(path) as f:
        _key_and_env = json.load(f)
        KEY = {}
        OTHER_ENV = {}
        for key, value in _key_and_env.items():
            if key in {"api_key", "api_secret", "acc_no"}:
                KEY[key] = value
            else:
                OTHER_ENV[key] = value
