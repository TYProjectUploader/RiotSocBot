import json
import os

DATA_FILE = "data.json"

def get_persist():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def update_persist(key, value):
    data = get_persist()
    data[key] = value
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)