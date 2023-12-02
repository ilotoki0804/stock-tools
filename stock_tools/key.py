import json
import logging
import os

if os.path.exists("keys.json"):
    path = 'keys.json'
elif os.path.exists("_keys.json"):
    path = '_keys.json'
else:
    path = None


if path is None:
    logging.error(
        "'keys.json' or '_keys.json' is not found. In order to use KEY, root directory should contain 'keys.json'."
    )
    KEY = {}
else:
    with open(path) as f:
        KEY = json.load(f)
