import json

from aiogram import F, Router, types
from aiogram.filters import Command

from config import CONFIG

router = Router()


@router.message(F.text.startswith("/add_users"))
@router.channel_post(F.text.startswith("/add_users"))
async def add_users(message: types.Message):
    chat = CONFIG.chats.setdefault(message.chat.id, set())
    good = []
    for name in map(str.strip, message.text[message.text.find(" "):].split(",")):
        if name in CONFIG.user_id_by_name and len(chat) <= 20:
            chat.add(CONFIG.user_id_by_name[name])
            good.append(name)
    with open("chats.json", "w", encoding="utf-8") as file:
        json.dump({key: list(value) for key, value in CONFIG.chats.items()}, file)
    await message.answer(f"Успешно добавлены: {', '.join(good)}")


@router.message(Command("remove_users"))
@router.channel_post(F.text.startswith("/remove_users"))
async def remove_users(message: types.Message):
    chat = CONFIG.chats.setdefault(message.chat.id, set())
    good = []
    for name in map(str.strip, message.text[message.text.find(" "):].split(",")):
        if CONFIG.user_id_by_name.get(name) in chat:
            chat.remove(CONFIG.user_id_by_name[name])
            good.append(name)
    with open("chats.json", "w", encoding="utf-8") as file:
        json.dump({key: list(value) for key, value in CONFIG.chats.items()}, file)
    await message.answer(f"Успешно убраны: {', '.join(good)}")


@router.message(Command("users_list"))
@router.channel_post(F.text.startswith("/users_list"))
async def users_list(message: types.Message):
    await message.answer(f"Текущие добавленные: {', '.join((CONFIG.users[user_id]['name'] for user_id in CONFIG.chats.get(message.chat.id, tuple())))}")
