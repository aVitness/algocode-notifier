import json
from itertools import islice


def batched(iterable, n):
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch


def load_from_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.loads(file.read())


def save_to_file(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)
