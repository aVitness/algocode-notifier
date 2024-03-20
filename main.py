import asyncio
import importlib
import logging
import os.path
import random
from copy import deepcopy
from datetime import timedelta
from pytrovich.enums import NamePart, Gender
import aiohttp
from aiogram import Bot, Dispatcher

from config import *
from utils import *

logging.basicConfig(level=logging.INFO)
morph = pymorphy3.MorphAnalyzer()
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(disable_fsm=True)
should_run = time_now().replace(hour=23, minute=0, second=0)
if time_now() >= should_run:
    should_run += timedelta(days=1)
should_run_week = time_now().replace(hour=15, minute=55, second=0) + timedelta(days=(5 - time_now().weekday()) % 7)
if time_now() >= should_run_week:
    should_run_week += timedelta(days=7)


def fix_number(match):
    number, word, case = match[1].split()
    return f"{number} {morph.parse(word)[0].inflect({case}).make_agree_with_number(int(number)).word}"


def fix_case(match):
    surname, name, case = match[1].split()
    case = case_translations[case]

    gender = detector.detect(firstname=name, lastname=surname)
    name = maker.make(NamePart.FIRSTNAME, gender, case, name)
    surname = maker.make(NamePart.LASTNAME, gender, case, surname)
    return f"{surname} {name}"


async def send_messages(changes):
    for user, old, new, task, is_first_solve in changes:
        name, surname = user["name"].split()
        for patterns, messages_list in messages:
            if all(re.fullmatch(patterns[key], str(new[key])) for key in patterns):
                is_female = detector.detect(firstname=name, lastname=surname) == Gender.FEMALE
                message = random.choice(messages_list).format(name=user["name"], task=task, penalty=new["penalty"], verdict=new["verdict"])
                message = gender_regex.sub(lambda match: match[1].split("/")[is_female], message)
                message = number_regex.sub(fix_number, message)
                message = case_regex.sub(fix_case, message)

                try:
                    await bot.send_message(CHAT_ID, message, parse_mode="markdown")
                    if is_first_solve:
                        await bot.send_message(
                            CHAT_ID,
                            gender_regex.sub(lambda match: match[1].split("/")[is_female], first_solve_message.format(name=name, task=task)),
                            parse_mode="markdown"
                        )
                except Exception as e:
                    # TODO: make a queue for sending again instead
                    logging.error(f"Got an error while sending main message: {e}")
                break


async def load_standings():
    async with aiohttp.ClientSession() as session:
        async with session.get(STANDINGS_PAGES[0]) as response:
            CONFIG.data = await response.json(encoding="utf-8")
        for page in STANDINGS_PAGES[1:]:
            async with session.get(page) as response:
                data = await response.json(encoding="utf-8")
                CONFIG.data["users"].extend(data["users"])
                CONFIG.data["contests"].extend(data["contests"])

    if CONFIG.users:
        del CONFIG.data["users"]
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
    _all_changes = []
    for old_contest, new_contest in zip(old_contests, contests):
        changes = []
        for user_id in CONFIG.users:
            for i, (old, new) in enumerate(zip(old_contest["users"].get(user_id, {}), new_contest["users"].get(user_id, {}))):
                if old != new:
                    changes.append((CONFIG.users[user_id], old, new, tasks[index + i], new.get("verdict") == "OK" and total_solves[index + i] == 0))
        index += len(new_contest["problems"])
        await send_messages(changes)
        if changes:
            _all_changes.append(changes)
    logging.debug(f"Found {sum(map(len, _all_changes))} changes: {_all_changes}")

    CONFIG.old_data = deepcopy(CONFIG.data)


async def leaderboard(date):
    logging.info("Generating leaderboard")
    score_table, penalty_table = generate_leaderboard(date)
    await bot.send_message(CHAT_ID, score_table, parse_mode="markdown")
    await bot.send_message(CHAT_ID, penalty_table, parse_mode="markdown")


def clear_old_pages():
    current_time = time.time()
    CONFIG.page_authors = {key: value for key, value in CONFIG.page_authors.items() if current_time - value[1] < 60}


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
            clear_old_pages()
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
    load_routers()
    asyncio.run(main())
