import os.path

from aiogram import Router, types
from aiogram.filters import Command

from config import time_now
from utils import generate_leaderboard

router = Router()


@router.message(Command("leaderboard"))
async def leaderboard(message: types.Message):
    date = message.text.split()[1:]
    if not date:
        date.append(time_now().strftime("%d.%m"))
    date = date[0]
    if not os.path.exists(f'archive/{"-".join(date.split(".")[::-1])}'):
        return await message.answer("Архив за данную дату не найден. Дата введена некорректно либо бот в этот день не работал.")
    score_table, penalty_table = generate_leaderboard(date)
    await message.answer(score_table, parse_mode="markdown")
    await message.answer(penalty_table, parse_mode="markdown")
