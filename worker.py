import asyncio
import logging
import os
import random
import re

from config import CHAT_ID, SAVE_FULL_ARCHIVE
from messages import MESSAGES, FIRST_SOLVE
from utils.files import save_to_file
from utils.leaderboard import generate_leaderboard
from utils.msg import detect, gender_regex, fix_main_message, Gender
from utils.standings import STANDINGS, USERS, get_total_scores
from utils.times import *


async def send_messages(bot, changes):
    for user, old, new, task, is_first_solve in changes:
        surname, name = user["name"].split()
        for patterns, messages_list in MESSAGES:
            if all(re.fullmatch(patterns[key], str(new[key])) for key in patterns):
                is_female = detect(name) == Gender.FEMALE
                message = random.choice(messages_list).format(name=user["name"], task=task, penalty=new["penalty"], verdict=new["verdict"])
                message = fix_main_message(message, is_female)

                try:
                    await bot.send_message(CHAT_ID, message, parse_mode="markdown")
                    await asyncio.sleep(0.2)
                    if is_first_solve:
                        await bot.send_message(
                            CHAT_ID,
                            gender_regex.sub(lambda match: match[1].split("/")[is_female], FIRST_SOLVE.format(name=name, task=task)),
                            parse_mode="markdown"
                        )

                except Exception as e:
                    logging.error(f"Got an error while sending main message: {e}")
                break


async def job(bot):
    logging.info("Starting regular job")
    for table in STANDINGS:
        ok = await table.load()
        if not ok or not table.old_data:
            logging.error(f"Table {table.url} was not loaded")
            continue

    archive_name = get_archive_name(get_current_time())
    if not os.path.exists(archive_name):
        save_to_file(archive_name, get_total_scores())
        if SAVE_FULL_ARCHIVE:
            save_to_file(archive_name + "_full", [table.data for table in STANDINGS])
        return

    for table in STANDINGS:
        if not table.old_data:
            continue
        old_contests = {contest["id"]: contest for contest in table.old_data["contests"]}
        for contest in table["contests"]:
            if contest["id"] not in old_contests:
                message = f"*Добавлен новый контест*\n[{contest['title']}](https://ejudge.algocode.ru/cgi-bin/new-client?contest_id={contest['id']})\n\n"
                for problem in contest["problems"]:
                    message += f"{problem['short']} - {problem['long']}\n"
                await bot.send_message(CHAT_ID, message, parse_mode="markdown")
                old_contests[contest["id"]] = {}

            tasks = []
            for problem in contest["problems"]:
                tasks.append(f"{contest['title']} - {problem['short']} ({problem['long']})")

            total_solves = [0] * len(tasks)
            for solves in old_contests[contest["id"]].get("users", {}).values():
                for i, result in enumerate(solves):
                    if result["verdict"] == "OK":
                        total_solves[i] += 1

            changes = []
            for user_id in contest["users"]:
                for i, (old, new) in enumerate(zip(old_contests[contest["id"]].get("users", {}).get(user_id, contest["empty_row"]), contest["users"][user_id])):
                    if old != new:
                        changes.append((USERS[user_id], old, new, tasks[i], new["verdict"] == "OK" and total_solves[i] == 0))
            await send_messages(bot, changes)


async def leaderboard(bot, date):
    logging.info("Generating leaderboard")
    score_table, penalty_table = generate_leaderboard(date)
    await bot.send_message(CHAT_ID, score_table, parse_mode="markdown")
    await bot.send_message(CHAT_ID, penalty_table, parse_mode="markdown")


async def task(bot, sleep_for):
    NEXT_DAILY = get_next_daily_leaderboard()
    NEXT_WEEKLY = get_next_weekly_leaderboard()

    while True:
        await asyncio.sleep(sleep_for)

        try:
            await job(bot)

            if get_current_time() >= NEXT_DAILY:
                await leaderboard(bot, get_current_time())
                NEXT_DAILY = get_next_daily_leaderboard()

            if get_current_time() >= NEXT_WEEKLY:
                await leaderboard(bot, get_current_time() - timedelta(days=6))
                NEXT_WEEKLY = get_next_weekly_leaderboard()

        except Exception as e:
            logging.error(f"Error: {e}")
