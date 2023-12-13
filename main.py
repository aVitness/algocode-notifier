import asyncio
import importlib
import logging
import os.path
import random
import re
from copy import deepcopy
from datetime import timedelta

import aiohttp
from aiogram import Bot, Dispatcher
from tabulate import tabulate

from config import *
from utils import *

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(disable_fsm=True)
should_run = time_now().replace(hour=23, minute=0, second=0)
if time_now() >= should_run:
    should_run += timedelta(days=1)
should_run_week = time_now().replace(hour=15, minute=55, second=0) + timedelta(days=(5 - time_now().weekday()) % 7)


async def send_messages(changes):
    for user, old, new, task, is_first_solve in changes:
        name = user["name"].split()[1]
        for patterns, messages_list in messages[name in female_names]:
            if all(re.fullmatch(patterns[key], str(new[key])) for key in patterns):
                message = replace_decl(random.choice(messages_list).format(name=user["name"], task=task, penalty=new["penalty"], verdict=new["verdict"]))
                await bot.send_message(CHAT_ID, message, parse_mode="markdown")
                if is_first_solve:
                    await bot.send_message(CHAT_ID, first_solve_message[name in female_names].format(name=name, task=task), parse_mode="markdown")

                for chat_id, users_to_send in CONFIG.chats.items():
                    if user["id"] in users_to_send:
                        await bot.send_message(chat_id, message, parse_mode="markdown")
                        if is_first_solve:
                            await bot.send_message(chat_id, first_solve_message[name in female_names].format(name=name, task=task), parse_mode="markdown")
                        await asyncio.sleep(0.1)

                break


async def load_standings():
    async with aiohttp.ClientSession() as session:
        async with session.get(STANDING_PAGE) as response:
            CONFIG.data = await response.json(encoding="utf-8")

    if CONFIG.users:
        return
    for user_dict in CONFIG.data["users"]:
        user_dict["id"] = str(user_dict["id"])
        CONFIG.users[user_dict["id"]] = user_dict
        CONFIG.user_id_by_name[user_dict["name"]] = user_dict["id"]


async def job():
    logging.info("Starting regular job")
    await load_standings()
    contests = CONFIG.data["contests"]

    old_contests = CONFIG.old_data["contests"]
    if not os.path.exists(CONFIG.filename) or len(contests) != len(old_contests):
        save_to_file(CONFIG.filename, CONFIG.data)
        return

    tasks = []
    for contest in old_contests:
        for problem in contest["problems"]:
            tasks.append(f"{title_replacements.get(contest['title'], contest['title'])} - {problem['short']} ({problem['long']})")

    total_solves = [0] * len(tasks)
    index = 0
    for contest in old_contests:
        for solves in contest["users"].values():
            for i, result in enumerate(solves):
                if result["verdict"] == "OK":
                    total_solves[index + i] += 1
        index += len(contest["problems"])

    index = 0
    for old_contest, new_contest in zip(old_contests, contests):
        changes = []
        for user_id in CONFIG.users:
            for i, (old, new) in enumerate(zip(old_contest["users"][user_id], new_contest["users"][user_id])):
                if old != new:
                    changes.append((CONFIG.users[user_id], old, new, tasks[index + i], new["verdict"] == "OK" and total_solves[index + i] == 0))
        index += len(new_contest["problems"])
        await send_messages(changes)

    CONFIG.old_data = deepcopy(CONFIG.data)




async def leaderboard(date):
    logging.info("Generating leaderboard")
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
    result = f"Топ 10 по успешным посылкам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await bot.send_message(CHAT_ID, result, parse_mode="markdown")
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["-"][:10], 1))
    result = f"Топ 10 по штрафам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await bot.send_message(CHAT_ID, result, parse_mode="markdown")


async def task(sleep_for):
    global should_run, should_run_week
    while True:
        try:
            await asyncio.sleep(sleep_for)
            CONFIG.filename = f'archive/{time_now().strftime("%m-%d")}'
            await job()
            if time_now() >= should_run:
                await leaderboard(time_now().strftime("%d.%m"))
                should_run += timedelta(days=1)
            if time_now() >= should_run_week:
                await leaderboard((time_now() - timedelta(days=6)).strftime("%d.%m"))
                should_run_week += timedelta(days=7)
        except Exception as e:
            logging.error(f"Got an error: {e}")


async def main():
    await load_standings()
    CONFIG.old_data = deepcopy(CONFIG.data)
    asyncio.create_task(task(40))
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


def load_routers():
    for filename in os.listdir("commands"):
        if filename.startswith("_"):
            continue
        router = getattr(importlib.import_module(f"commands.{filename[:-3]}"), "router")
        dispatcher.include_router(router)
        logging.info(f"Router `{filename}` has been loaded")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(module)s:%(message)s at %(asctime)s", datefmt='%H:%M:%S')
    load_routers()
    asyncio.run(main())
