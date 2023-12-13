import time

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from tabulate import tabulate

from config import CONFIG
from utils import total_score_and_penalty

router = Router()

last_update = 0
scores = {}
stats = [None, None]


def generate(page, target):
    global last_update, stats, scores
    if time.time() - last_update > 60:
        scores = total_score_and_penalty(CONFIG.data["contests"])
        stats = [sorted(scores, key=lambda key: scores[key], reverse=True), sorted(scores, key=lambda key: scores[key][::-1], reverse=True)]
        last_update = time.time()
    if page < 0 or 15 * page >= len(scores):
        return
    return [(place, CONFIG.users[user_id]["name"], scores[user_id][target]) for place, user_id in enumerate(stats[target][page * 15:(page + 1) * 15], start=page * 15 + 1)]


def keyboard(prefix, page):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="<<<",
        callback_data=f"{prefix}{page - 5}")
    )
    builder.add(types.InlineKeyboardButton(
        text="<",
        callback_data=f"{prefix}{page - 1}")
    )
    builder.add(types.InlineKeyboardButton(
        text=">",
        callback_data=f"{prefix}{page + 1}")
    )
    builder.add(types.InlineKeyboardButton(
        text=">>>",
        callback_data=f"{prefix}{page + 5}")
    )
    return builder.as_markup()


@router.message(Command("penalty_top"))
async def penalty_top(message: types.Message):
    table_data = generate(0, 1)
    headers = ("*", "Имя", "Штраф")
    result = f"Топ по штрафам, страница 1\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await message.answer(result, parse_mode="markdown", reply_markup=keyboard("pt", 0))


@router.callback_query(F.data.startswith("pt"))
async def penalty_top_callback(callback: types.CallbackQuery):
    page = int(callback.data[2:])
    table_data = generate(page, 1)
    if table_data is None:
        return await callback.answer("Это крайняя страница")
    headers = ("*", "Имя", "Штраф")
    result = f"Топ по штрафам, страница {page + 1}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await callback.message.edit_text(result, parse_mode="markdown", reply_markup=keyboard("pt", page))
    await callback.answer()


@router.message(Command("score_top"))
async def penalty_top(message: types.Message):
    table_data = generate(0, 0)
    headers = ("*", "Имя", "Решено")
    result = f"Топ по успешным посылкам, страница 1\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await message.answer(result, parse_mode="markdown", reply_markup=keyboard("st", 0))


@router.callback_query(F.data.startswith("st"))
async def penalty_top_callback(callback: types.CallbackQuery):
    page = int(callback.data[2:])
    table_data = generate(page, 0)
    if table_data is None:
        return await callback.answer("Это крайняя страница")
    headers = ("*", "Имя", "Решено")
    result = f"Топ по успешным посылкам, страница {page + 1}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    await callback.message.edit_text(result, parse_mode="markdown", reply_markup=keyboard("st", page))
    await callback.answer()
