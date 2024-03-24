import aiogram
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CONFIG, first_solves_message, reversed_title_replacements, title_replacements, ALPHABET
from utils import batched, format_time, take_page

router = Router()


@router.message(Command("fsolves"))
async def first_solves(message: types.Message):
    buttons = [
        [types.InlineKeyboardButton(text=text, callback_data="#" + text) for text in row]
        for row in
        batched(reversed_title_replacements, 2)
    ]
    await message.answer(
        "Выберите контест",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("#"))
async def show_first_solves(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    contest_title = callback.data[1:]
    contest, = (contest for contest in CONFIG.data["contests"] if contest["title"] == reversed_title_replacements[contest_title])

    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=ALPHABET[i],
            callback_data="!" + contest_title + ":" + ALPHABET[i])
        )
    await callback.message.edit_text(
        "Выберите задачу",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("!"))
async def show_first_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    contest_title, task_l = callback.data[1:].split(":")
    contest_title = reversed_title_replacements[contest_title]
    contest, = (contest for contest in CONFIG.data["contests"] if contest["title"] == contest_title)
    task = contest["problems"][ord(task_l) - ord("A")]
    solves = []
    for user_id in CONFIG.users:
        if user_id not in contest["users"]:
            continue
        result = contest["users"][user_id][ord(task_l) - ord("A")]
        if result["verdict"] == "OK":
            solves.append((result["time"], CONFIG.users[user_id]["name"]))
    solves = sorted(solves)[:3]
    while len(solves) < 3:
        solves.append((-1, "-"))
    solves = [
        name + (f" ({format_time(int(time))})" if time > 0 else "")
        for time, name in solves
    ]
    result_string = first_solves_message.format(first=solves[0], second=solves[1], third=solves[2], task=f"{contest_title} - {task_l} ({task['long']})")

    builder = InlineKeyboardBuilder()
    for i in range(len(contest["problems"])):
        builder.add(types.InlineKeyboardButton(
            text=ALPHABET[i],
            callback_data="!" + title_replacements[contest_title] + ":" + ALPHABET[i])
        )
    try:
        await callback.message.edit_text(result_string, reply_markup=builder.as_markup(), parse_mode="markdown")
    except aiogram.exceptions.TelegramBadRequest:
        return await callback.answer("Уже выбрана эта задача!")
    await callback.answer()
