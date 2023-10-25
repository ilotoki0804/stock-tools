import json
import logging

try:
    with open('keys.json') as f:
        KEY = json.load(f)
except FileNotFoundError:
    logging.error("'keys.json' not found. In order to use KEY, root directory should contain 'keys.json'.")
    KEY = {}
