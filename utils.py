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


def replace_decl(s):
    for x, repl in ((" 1 неверных посылок", " 1 неверной посылки"), (" 1 попытками", " 1 попыткой"), (" 1 попыток", " 1 попытки"), (" 1 ошибки", " 1 ошибку")):
        s = s.replace(x, repl)
    return s


def format_time(seconds):
    if seconds <= 0:
        return None
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}"


def total_score_and_penalty(contests):
    stats = {}
    for contest in contests:
        for user_id, solves in contest["users"].items():
            if user_id not in stats:
                stats[user_id] = [0, 0]
            for result in solves:
                stats[user_id][0] += int(result["score"])
                stats[user_id][1] += result["penalty"]
    return stats
