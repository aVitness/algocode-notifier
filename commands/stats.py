import time

import aiogram
from aiogram import F, Router, types
from aiogram.filters import Command
from tabulate import tabulate

from commands.fsolves import batched
from utils.standings import CONTESTS, USERS_BY_NAME, STANDINGS
from utils.times import take_page, page_authors, format_time

router = Router()


@router.message(Command("stats"))
async def stats(message: types.Message):
    msg = message.text.split(maxsplit=1)
    if len(msg) == 1:
        buttons = [
            [types.InlineKeyboardButton(text=CONTESTS[contest_id]["title"], callback_data=f"?{contest_id}") for contest_id in row]
            for row in
            batched(CONTESTS, 2)
        ]
        msg = await message.answer(
            "Выберите контест",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        page_authors[msg.message_id] = (message.from_user.id, int(time.time()))
    elif len(msg) == 2:
        user = USERS_BY_NAME.get(msg[1])
        if not user:
            return message.answer("Человек с таким именем не найден.")
        buttons = [
            [
                types.InlineKeyboardButton(text="Все" if contest_id == "Все" else CONTESTS[contest_id]["title"], callback_data=f"*{contest_id}:{user['id']}")
                for contest_id in row
            ]
            for row in batched(("Все", *CONTESTS), 2)
        ]
        msg = await message.answer(
            "Выберите контест",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        page_authors[msg.message_id] = (message.from_user.id, int(time.time()))


@router.callback_query(F.data.startswith("?"))
async def stats_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_id = callback.data[1:]
    contest = CONTESTS[contest_id]

    headers = ("~ Задача", "Попыток", "Решавших", "Успешных", "% успешных", "% решивших")
    align = ("left", "right", "right", "right", "right", "right")

    table_data = []
    for i in range(len(contest["problems"])):
        current = [f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", 0, 0, 0, None, None]
        for user_id in contest["users"]:
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
        [types.InlineKeyboardButton(text=CONTESTS[contest_id]["title"], callback_data=f"?{contest_id}") for contest_id in row]
        for row in
        batched(CONTESTS, 2)
    ]
    try:
        await callback.message.edit_text(result_string, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбран этот контест!")
    await callback.answer()


@router.callback_query(F.data.startswith("*"))
async def stats_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_id, user_id = callback.data[1:].split(":")
    buttons = [
        [
            types.InlineKeyboardButton(text="Все" if contest_id == "Все" else CONTESTS[contest_id]["title"], callback_data=f"*{contest_id}:{user_id}")
            for contest_id in row
        ]
        for row in batched(("Все", *CONTESTS), 2)
    ]
    if contest_id == "Все":
        solved = total = 0
        for table in STANDINGS:
            for contest in table["contests"]:
                total += len(contest["problems"])
                solved += sum(solve['verdict'] == 'OK' for solve in contest['users'][user_id])

        result_string = "```\n"
        result_string += f"Всего {solved}/{total}\n"
        for table in STANDINGS:
            for contest in table["contests"]:
                solves = contest["users"][user_id]
                result_string += f'{contest["title"]} ({sum(solve["verdict"] == "OK" for solve in solves)}/{len(contest["problems"])})\n'
                for p in batched(range(len(contest["problems"])), 12):
                    for i in p:
                        result_string += contest["problems"][i]["short"].center(5, " ")
                    result_string += "\n"
                    for i in p:
                        cur = str(solves[i]["penalty"] or "")
                        if solves[i]["verdict"] == "OK":
                            cur = "+" + cur
                        elif cur:
                            cur = "-" + cur
                        result_string += cur.center(5, " ")
                    result_string += "\n"
        result_string += "```\n"
        if len(result_string) >= 4090:  # эх
            result_string = result_string[:4080] + "...\n```\n"
        await callback.message.edit_text(result_string, parse_mode="markdown")
        await callback.answer()
    else:
        contest = CONTESTS[contest_id]
        solves = contest["users"][user_id]

        headers = ("~ Задача", "Штраф", "Вердикт", "Время")
        align = ("left", "right", "right", "right")

        table_data = []
        for i in range(len(contest["problems"])):
            t = int(solves[i]["time"])
            table_data.append(
                (f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", solves[i]["penalty"], solves[i]["verdict"], format_time(t)))
        result_string = "```\n" + tabulate(table_data, headers, colalign=align) + "\n```"
        try:
            await callback.message.edit_text(result_string, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="markdown")
        except aiogram.exceptions.TelegramBadRequest:
            return await callback.answer("Уже выбран этот контест!")
        await callback.answer()
