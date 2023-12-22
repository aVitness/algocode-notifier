import aiogram
from aiogram import F, Router, types
from aiogram.filters import Command
from tabulate import tabulate

from config import CONFIG, reversed_title_replacements
from utils import batched, format_time, take_page

router = Router()


@router.message(Command("stats"))
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
        user_ids = [user_id for user_id in CONFIG.users if CONFIG.users[user_id]["name"] == msg[1]]
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


@router.callback_query(F.data.startswith("?"))
async def stats_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_title = callback.data[1:]
    contest, = (contest for contest in CONFIG.data["contests"] if contest["title"] == reversed_title_replacements[contest_title])

    headers = ("~ Задача", "Попыток", "Решавших", "Успешных", "% успешных", "% решивших")
    align = ("left", "right", "right", "right", "right", "right")

    table_data = []
    for i in range(len(contest["problems"])):
        current = [f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", 0, 0, 0, None, None]
        for user_id in CONFIG.users:
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


@router.callback_query(F.data.startswith("*"))
async def stats_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_title, user_id = callback.data[1:].split(":")
    contest, = (contest for contest in CONFIG.data["contests"] if contest["title"] == reversed_title_replacements[contest_title])
    solves = contest["users"][user_id]

    headers = ("~ Задача", "Штраф", "Вердикт", "Время")
    align = ("left", "right", "right", "right")

    table_data = []
    for i in range(len(contest["problems"])):
        t = int(solves[i]["time"])
        table_data.append((f"{contest['problems'][i]['short']}. {contest['problems'][i]['long']}", solves[i]["penalty"], solves[i]["verdict"], format_time(t)))
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
