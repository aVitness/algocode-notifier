import time

import aiohttp
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from tabulate import tabulate

from config import CONFIG

router = Router()

last_update = 0
result = {}


async def generate():
    global last_update, result
    if time.time() - last_update < 60:
        return
    last_update = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://algocode.ru/standings_data/b_fall_2023/") as response:
            thematic_table = await response.json(encoding="utf-8")
            thematic_table = thematic_table["contests"]
            total_tasks = sum(len(contest["problems"]) for contest in thematic_table)

        async with session.get("https://algocode.ru/standings_data/region2023/") as response:
            region_table = await response.json(encoding="utf-8")
            region_table = region_table["contests"]
            total_dists = len(region_table)
    result = {user_id: {"solved_thematic": 0, "solved_dists": [0] * total_dists} for user_id in CONFIG.users}

    for contest in thematic_table:
        for user_id, contest_result in contest["users"].items():
            if user_id not in CONFIG.users:
                continue
            for task_result in contest_result:
                result[user_id]["solved_thematic"] += task_result["score"]
                if not task_result["score"] and task_result["verdict"] == "PR":
                    result[user_id]["solved_thematic"] += 1
    for i, contest in enumerate(region_table):
        for user_id, contest_result in contest["users"].items():
            if user_id not in CONFIG.users:
                continue
            for task_result in contest_result:
                result[user_id]["solved_dists"][i] += task_result["score"]

    for user_result in result.values():
        user_result["score_dists"] = sum(
            min(12, 10 * x / 300) for x in user_result["solved_dists"]
        ) / total_dists
        user_result["score_thematic"] = 12 * user_result["solved_thematic"] / total_tasks
        user_result["score"] = min(10, 0.5 * user_result["score_thematic"] + 0.2 * user_result["score_dists"])

    result = dict(sorted(result.items(), key=lambda x: x[1]["score"], reverse=True))


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


def generate_table(page):
    if page < 0 or 15 * page >= len(result):
        return
    return [(place, CONFIG.users[user_id]["name"], f'{result[user_id]["score"]:.2f}', f'{result[user_id]["score_thematic"]:.2f}', f'{result[user_id]["score_dists"]:.2f}') for
            place, user_id in
            enumerate(tuple(result)[page * 15:(page + 1) * 15], start=page * 15 + 1)]


@router.message(Command("grade"))
async def grade(message: types.Message):
    await generate()
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1] not in CONFIG.user_id_by_name:
        return await message.answer("Пользователь с таким именем не найден")
    elif len(args) > 1:
        return await message.answer(f"{args[1]}\nОценка: {result[CONFIG.user_id_by_name[args[1]]]['score']:.2f}")

    table_data = generate_table(0)
    headers = ("*", "Имя", "Оценка", "Темтуры", "Дистуры")
    align = ("right", "left", "right", "right", "right")
    result_message = f"Топ по оценкам, страница 1\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql", colalign=align) + "\n```"
    await message.answer(result_message, parse_mode="markdown", reply_markup=keyboard("gt", 0))


@router.callback_query(F.data.startswith("gt"))
async def penalty_top_callback(callback: types.CallbackQuery):
    page = int(callback.data[2:])
    table_data = generate_table(page)
    if table_data is None:
        return await callback.answer("Это крайняя страница")
    headers = ("*", "Имя", "Оценка", "Темтуры", "Дистуры")
    align = ("right", "left", "right", "right", "right")
    result_message = f"Топ по оценкам, страница {page + 1}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql", colalign=align) + "\n```"
    await callback.message.edit_text(result_message, parse_mode="markdown", reply_markup=keyboard("gt", page))
    await callback.answer()
