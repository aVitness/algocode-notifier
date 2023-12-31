import time

import aiohttp
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from tabulate import tabulate

from config import CONFIG
from utils import take_page

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
            region_users = {str(user["id"]): user for user in region_table["users"]}
            region_table = region_table["contests"]
            total_dists = len(region_table)

        async with session.get("https://algocode.ru/standings_data/b_2023_midterm_test/") as response:
            test_table = await response.json(encoding="utf-8")
            test_table = test_table["contests"]
            total_test_tasks = sum(len(contest["problems"]) for contest in test_table)

        async with session.get("https://algocode.ru/standings_data/b_2023_midterm_blitz/") as response:
            blitz_table = await response.json(encoding="utf-8")
            blitz_table = blitz_table["contests"]
            total_blitz_tasks = sum(len(contest["problems"]) for contest in blitz_table)

    result = {user_id: {"solved_thematic": 0, "solved_dists": [0] * total_dists, "solved_blitz": 0, "solved_test": 0} for user_id in CONFIG.users}

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
                if region_users[user_id]["name"] not in CONFIG.user_id_by_name:
                    continue
                user_id = CONFIG.user_id_by_name[region_users[user_id]["name"]]
            result[user_id]["solved_dists"][i] = max(result[user_id]["solved_dists"][i], sum(task_result["score"] for task_result in contest_result))
    for contest in test_table:
        for user_id, contest_result in contest["users"].items():
            if user_id not in CONFIG.users:
                continue
            for task_result in contest_result:
                result[user_id]["solved_test"] += task_result["score"]
    for contest in blitz_table:
        for user_id, contest_result in contest["users"].items():
            if user_id not in CONFIG.users:
                continue
            for task_result in contest_result:
                result[user_id]["solved_blitz"] += task_result["score"]

    for user_result in result.values():
        user_result["score_dists"] = sum(
            min(12, 10 * x / 300) for x in user_result["solved_dists"]
        ) / total_dists
        user_result["score_thematic"] = 12 * user_result["solved_thematic"] / total_tasks
        user_result["score_test"] = max(user_result["solved_test"] / 15 * 10, user_result["solved_test"] - 2) / 3
        user_result["score_blitz"] = 20 * user_result["solved_blitz"] / 9 / 3
        user_result["score_s"] = user_result["score_test"] + user_result["score_blitz"]
        user_result["score"] = min(10, 0.5 * user_result["score_thematic"] + 0.2 * user_result["score_dists"] + 0.3 * user_result["score_s"])

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
    return [(place, CONFIG.users[user_id]["name"], f'{result[user_id]["score"]:.2f}', f'{result[user_id]["score_thematic"]:.2f}',
             f'{result[user_id]["score_dists"]:.2f}', f'{result[user_id]["score_s"]:.2f}') for
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
    headers = ("*", "Имя", "Оценка", "Темтуры", "Дистуры", "Зачёт")
    align = ("right", "left", "right", "right", "right", "right")
    result_message = f"Топ по оценкам, страница 1\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql", colalign=align) + "\n```"
    msg = await message.answer(result_message, parse_mode="markdown", reply_markup=keyboard("gt", 0))
    CONFIG.page_authors[msg.message_id] = (message.from_user.id, int(time.time()))


@router.callback_query(F.data.startswith("gt"))
async def grade_callback(callback: types.CallbackQuery):
    if not take_page(callback):
        return await callback.answer("Эта таблица занята другим пользователем")
    page = int(callback.data[2:])
    table_data = generate_table(page)
    if table_data is None:
        return await callback.answer("Это крайняя страница")
    headers = ("*", "Имя", "Оценка", "Темтуры", "Дистуры", "Зачёт")
    align = ("right", "left", "right", "right", "right", "right")
    result_message = f"Топ по оценкам, страница {page + 1}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql", colalign=align) + "\n```"
    await callback.message.edit_text(result_message, parse_mode="markdown", reply_markup=keyboard("gt", page))
    await callback.answer()
