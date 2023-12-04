import asyncio
import json
import logging
import os.path
import random
import re
from copy import deepcopy
from datetime import timedelta

import aiogram
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from tabulate import tabulate

from config import *
from utils import batched, load_from_file, save_to_file

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher()
should_run = time_now().replace(hour=23, minute=0, second=0)
if time_now() >= should_run:
    should_run += timedelta(days=1)
filename = f'archive/{time_now().strftime("%m-%d")}'
data = {}
old_data = {}
users = {}
user_id_by_name = {}
with open("chats.json", "r", encoding="utf-8") as file:
    chats = json.load(file)
    for key in chats:
        chats[key] = set(chats[key])


def replace_decl(s):
    for x, repl in ((" 1 неверных посылок", " 1 неверной посылки"), (" 1 попытками", " 1 попыткой"), (" 1 попыток", " 1 попытки"), (" 1 ошибки", " 1 ошибку")):
        s = s.replace(x, repl)
    return s


async def send_messages(changes):
    for user, old, new, task, is_first_solve in changes:
        name = user["name"].split()[1]
        for patterns, messages_list in messages[name in female_names]:
            if all(re.fullmatch(patterns[key], str(new[key])) for key in patterns):
                message = replace_decl(random.choice(messages_list).format(name=user["name"], task=task, penalty=new["penalty"], verdict=new["verdict"]))
                await bot.send_message(CHAT_ID, message, parse_mode="markdown")
                if is_first_solve:
                    await bot.send_message(CHAT_ID, first_solve_message.format(name=name, task=task), parse_mode="markdown")

                for chat_id, users_to_send in chats.items():
                    if user["id"] in users_to_send:
                        await bot.send_message(chat_id, message, parse_mode="markdown")
                        if is_first_solve:
                            await bot.send_message(chat_id, first_solve_message.format(name=name, task=task), parse_mode="markdown")
                        await asyncio.sleep(0.1)

                break


async def load_standings():
    global data, users
    async with aiohttp.ClientSession() as session:
        async with session.get(STANDING_PAGE) as response:
            data = await response.json(encoding="utf-8")

    if users:
        return
    for user_dict in data["users"]:
        user_dict["id"] = str(user_dict["id"])
        users[user_dict["id"]] = user_dict
        user_id_by_name[user_dict["name"]] = user_dict["id"]


async def job():
    global old_data
    logging.info("Starting regular job")
    await load_standings()
    contests = data["contests"]

    old_contests = old_data["contests"]
    if not os.path.exists(filename) or len(contests) != len(old_contests):
        save_to_file(filename, data)
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
        for user_id in users:
            for i, (old, new) in enumerate(zip(old_contest["users"][user_id], new_contest["users"][user_id])):
                if old != new:
                    changes.append((users[user_id], old, new, tasks[index + i], new["verdict"] == "OK" and total_solves[index + i] == 0))
        index += len(new_contest["problems"])
        await send_messages(changes)

    old_data = deepcopy(data)


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


async def leaderboard():
    logging.info("Generating leaderboard")
    old_data = load_from_file(filename)
    UPDATES = {
        "+": [],
        "-": []
    }
    old_stats = total_score_and_penalty(old_data["contests"])
    new_stats = total_score_and_penalty(data["contests"])

    for user_id in users:
        old_ok, old_penalty = old_stats[user_id]
        ok, penalty = new_stats[user_id]
        full_name = users[user_id]["name"]
        UPDATES["+"].append((ok - old_ok, ok, old_ok, full_name))
        UPDATES["-"].append((penalty - old_penalty, penalty, old_penalty, full_name))
    UPDATES["+"].sort(reverse=True)
    UPDATES["-"].sort(reverse=True)
    headers = ("*", "Имя", "Δ", "Было", "Стало")

    date = datetime.now().strftime("%d.%m")
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["+"][:10], 1))
    result = f"Топ 10 по успешным посылкам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await bot.send_message(CHAT_ID, result, parse_mode="markdown")
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["-"][:10], 1))
    result = f"Топ 10 по штрафам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await bot.send_message(CHAT_ID, result, parse_mode="markdown")


@dispatcher.message(Command("fsolves"))
async def first_solves(message: types.Message):
    buttons = [
        [types.KeyboardButton(text=text, callback_data=list(title_replacements).index(text)) for text in row]
        for row in
        batched(title_replacements.keys(), 2)
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите контест"
    )
    await message.answer("Контест?", reply_markup=keyboard)


@dispatcher.message(F.text.in_(title_replacements))
async def show_first_solves(message: types.Message):
    builder = InlineKeyboardBuilder()
    contest, = (contest for contest in data["contests"] if contest["title"] == message.text)

    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=chr(ord("A") + i),
            callback_data="!" + title_replacements[message.text] + ":" + chr(ord("A") + i))
        )
    await message.answer(
        "Выберите задачу",
        reply_markup=builder.as_markup()
    )


@dispatcher.callback_query(F.data.startswith("!"))
async def show_first_callback(callback: types.CallbackQuery):
    contest_title, task_l = callback.data[1:].split(":")
    contest_title = reversed_title_replacements[contest_title]
    contest, = (contest for contest in data["contests"] if contest["title"] == contest_title)
    task = contest["problems"][ord(task_l) - ord("A")]
    solves = []
    for user_id in users:
        result = contest["users"][user_id][ord(task_l) - ord("A")]
        if result["verdict"] == "OK":
            solves.append((result["time"], users[user_id]["name"]))
    solves = sorted(solves)[:3]
    while len(solves) < 3:
        solves.append((-1, "-"))
    result_string = first_solves_message.format(first=solves[0][1], second=solves[1][1], third=solves[2][1],
                                                task=f"{contest_title} - {task_l} ({task['long']})")

    builder = InlineKeyboardBuilder()
    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=chr(ord("A") + i),
            callback_data="!" + title_replacements[contest_title] + ":" + chr(ord("A") + i))
        )
    try:
        await callback.message.edit_text(result_string, reply_markup=builder.as_markup(), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбрана эта задача!")
    await callback.answer()


@dispatcher.message(Command("stats"))
async def stats(message: types.Message):
    msg = message.text.split(maxsplit=1)
    if len(msg) == 1:
        buttons = [
            [types.InlineKeyboardButton(text=text, callback_data="?" + text) for text in row]
            for row in
            batched(reversed_title_replacements, 2)
        ]
        await message.answer(
            "Выберите контест",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    elif len(msg) == 2:
        user_ids = [user_id for user_id in users if users[user_id]["name"] == msg[1]]
        if not user_ids:
            return message.answer("Человек с таким именем не найден.")

        buttons = [
            [types.InlineKeyboardButton(text=text, callback_data="*" + text + ":" + user_ids[0]) for text in row]
            for row in
            batched(reversed_title_replacements, 2)
        ]
        await message.answer(
            "Выберите контест",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
        )


@dispatcher.callback_query(F.data.startswith("?"))
async def stats_callback(callback: types.CallbackQuery):
    contest_title = callback.data[1:]
    contest, = (contest for contest in data["contests"] if contest["title"] == reversed_title_replacements[contest_title])

    headers = ("~ Задача", "Попыток", "Решавших", "Успешных", "% успешных", "% решивших")
    align = ("left", "right", "right", "right", "right", "right")

    table_data = []
    for i in range(len(contest["problems"])):
        current = [f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", 0, 0, 0, None, None]
        for user_id in users:
            solve = contest["users"][user_id][i]
            if solve["verdict"] is not None:
                current[2] += 1
            if solve["verdict"] == "OK":
                current[3] += 1
                current[1] += 1
            current[1] += solve["penalty"]
        if current[2] == 0:
            current[4] = current[5] = "0.0%"
        else:
            current[4] = f"{current[3] / current[1] * 100:.2f}%"
            current[5] = f"{current[3] / current[2] * 100:.2f}%"
        table_data.append(current)
    result_string = "```\n" + tabulate(table_data, headers, colalign=align) + "\n```"

    buttons = [
        [types.InlineKeyboardButton(text=text, callback_data="?" + text) for text in row]
        for row in
        batched(reversed_title_replacements, 2)
    ]
    try:
        await callback.message.edit_text(result_string, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбран этот контест!")
    await callback.answer()


@dispatcher.callback_query(F.data.startswith("*"))
async def stats_callback(callback: types.CallbackQuery):
    contest_title, user_id = callback.data[1:].split(":")
    contest, = (contest for contest in data["contests"] if contest["title"] == reversed_title_replacements[contest_title])
    solves = contest["users"][user_id]

    headers = ("~ Задача", "Штраф", "Вердикт", "Время")
    align = ("left", "right", "right", "right")

    table_data = []
    for i in range(len(contest["problems"])):
        t = int(solves[i]["time"])
        if t == 0:
            t = None
        else:
            h, m = divmod(t, 3600)
            m, s = divmod(m, 60)
            t = f"{h}:{m:02}:{s:02}"
        table_data.append((f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", solves[i]["penalty"], solves[i]["verdict"], t))
    result_string = "```\n" + tabulate(table_data, headers, colalign=align) + "\n```"
    buttons = [
        [types.InlineKeyboardButton(text=text, callback_data="*" + text + ":" + user_id) for text in row]
        for row in
        batched(reversed_title_replacements, 2)
    ]
    try:
        await callback.message.edit_text(result_string, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбран этот контест!")
    await callback.answer()


@dispatcher.message(F.text.startswith("/add_users"))
@dispatcher.channel_post(F.text.startswith("/add_users"))
async def add_users(message: types.Message):
    chat = chats.setdefault(message.chat.id, set())
    good = []
    for name in map(str.strip, message.text[message.text.find(" "):].split(",")):
        if name in user_id_by_name and len(chat) <= 20:
            chat.add(user_id_by_name[name])
            good.append(name)
    with open("chats.json", "w", encoding="utf-8") as file:
        json.dump({key: list(value) for key, value in chats.items()}, file)
    await message.answer(f"Успешно добавлены: {', '.join(good)}")


@dispatcher.message(Command("remove_users"))
@dispatcher.channel_post(F.text.startswith("/remove_users"))
async def remove_users(message: types.Message):
    chat = chats.setdefault(message.chat.id, set())
    good = []
    for name in map(str.strip, message.text[message.text.find(" "):].split(",")):
        if user_id_by_name.get(name) in chat:
            chat.remove(user_id_by_name[name])
            good.append(name)
    with open("chats.json", "w", encoding="utf-8") as file:
        json.dump({key: list(value) for key, value in chats.items()}, file)
    await message.answer(f"Успешно убраны: {', '.join(good)}")


@dispatcher.message(Command("users_list"))
@dispatcher.channel_post(F.text.startswith("/users_list"))
async def users_list(message: types.Message):
    await message.answer(f"Текущие добавленные: {', '.join((users[user_id]['name'] for user_id in chats.get(message.chat.id, tuple())))}")


async def task(sleep_for):
    global should_run, filename
    while True:
        await asyncio.sleep(sleep_for)
        filename = f'archive/{time_now().strftime("%m-%d")}'
        await job()
        if time_now() >= should_run:
            await leaderboard()
            should_run += timedelta(days=1)


async def main():
    global old_data
    await load_standings()
    old_data = deepcopy(data)
    asyncio.create_task(task(40))
    await dispatcher.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(module)s:%(message)s at %(asctime)s", datefmt='%H:%M:%S')
    asyncio.run(main())
