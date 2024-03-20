import json
import re
import time
from itertools import islice

import pymorphy3
from aiogram import types
from pytrovich.detector import PetrovichGenderDetector
from pytrovich.enums import Case
from pytrovich.maker import PetrovichDeclinationMaker
from tabulate import tabulate

from config import CONFIG, time_now

detector = PetrovichGenderDetector()
morph = pymorphy3.MorphAnalyzer()
gender_regex = re.compile(r"\[([^\[\]]+)\]")
number_regex = re.compile(r"%([^%]+)%")
case_regex = re.compile(r"@([^@]+)@")
maker = PetrovichDeclinationMaker()
case_translations = {"gent": Case.GENITIVE, "datv": Case.DATIVE, "accs": Case.ACCUSATIVE, "ablt": Case.INSTRUMENTAL, "loct": Case.PREPOSITIONAL}


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


def generate_leaderboard(date):
    old_data = load_from_file(f'archive/{"-".join(date.split(".")[::-1])}')
    UPDATES = {
        "+": [],
        "-": []
    }
    old_stats = total_score_and_penalty(old_data["contests"])
    new_stats = total_score_and_penalty(CONFIG.data["contests"])

    for user_id in CONFIG.users:
        old_ok, old_penalty = old_stats.get(user_id, (0, 0))
        ok, penalty = new_stats[user_id]
        full_name = CONFIG.users[user_id]["name"]
        UPDATES["+"].append((ok - old_ok, ok, old_ok, full_name))
        UPDATES["-"].append((penalty - old_penalty, penalty, old_penalty, full_name))
    UPDATES["+"].sort(reverse=True)
    UPDATES["-"].sort(reverse=True)
    headers = ("*", "Имя", "Δ", "Было", "Стало")

    if date != time_now().strftime("%d.%m"):
        date += f' - {time_now().strftime("%d.%m")}'
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["+"][:10], 1))
    score_result = f"Топ 10 по успешным посылкам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["-"][:10], 1))
    penalty_result = f"Топ 10 по штрафам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    return score_result, penalty_result


async def is_admin(message: types.Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return chat_member.status in ('creator', 'administrator')


def take_page(callback: types.CallbackQuery):
    current_time = int(time.time())
    user, last_used = CONFIG.page_authors.get(callback.message.message_id, (None, 0))
    if user == callback.from_user.id or current_time - last_used >= 60:
        CONFIG.page_authors[callback.message.message_id] = (callback.from_user.id, current_time)
        return True
    return False
