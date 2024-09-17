import time
from itertools import islice

import aiogram
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from messages import TOP_3_FIRST_SOLVES
from utils.standings import CONTESTS, USERS
from utils.times import format_time, page_authors, take_page

router = Router()


def batched(iterable, n):
    it = iter(iterable)
    while True:
        batch = list(islice(it, n))
        if not batch:
            return
        yield batch


@router.message(Command("fsolves"))
async def first_solves(message: types.Message):
    buttons = [
        [types.InlineKeyboardButton(text=CONTESTS[contest_id]["title"], callback_data=f"#{contest_id}") for contest_id in row]
        for row in
        batched(CONTESTS, 2)
    ]
    msg = await message.answer(
        "Выберите контест",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    page_authors[msg.message_id] = (message.from_user.id, int(time.time()))


@router.callback_query(F.data.startswith("#"))
async def show_first_solves(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    builder = InlineKeyboardBuilder()
    contest_id = callback.data[1:]
    contest = CONTESTS[contest_id]

    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=contest["problems"][i]["short"],
            callback_data=f"!{contest_id}:{i}")
        )
    await callback.message.edit_text(
        "Выберите задачу",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("!"))
async def show_first_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_id, task = callback.data[1:].split(":")
    task = int(task)
    contest = CONTESTS[contest_id]
    solves = []
    for user_id in contest["users"]:
        result = contest["users"][user_id][task]
        if result["verdict"] == "OK":
            solves.append((result["time"], USERS[user_id]["name"]))
    solves = sorted(solves)[:3]
    while len(solves) < 3:
        solves.append((-1, "-"))
    solves = [
        name + (f" ({format_time(int(time))})" if time > 0 else "")
        for time, name in solves
    ]
    result_string = TOP_3_FIRST_SOLVES.format(
        first=solves[0], second=solves[1], third=solves[2],
        task=f"{contest['title']} - {contest['problems'][task]['short']} ({contest['problems'][task]['long']})"
    )

    builder = InlineKeyboardBuilder()
    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=contest["problems"][i]["short"],
            callback_data=f"!{contest_id}:{i}")
        )
    try:
        await callback.message.edit_text(result_string, reply_markup=builder.as_markup(), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбрана эта задача!")
    await callback.answer()
