import json
import os


def save_to_file(path, data):
    os.makedirs("/".join(path.split("/")[:-1]), exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as file:
        json.dump(data, file)


def load_from_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, mode="r", encoding="utf-8") as file:
        return json.load(file)
