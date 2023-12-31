import json
import os
from datetime import datetime

from dotenv import load_dotenv
from pytz import timezone

load_dotenv()

CHAT_ID = "@yandex_b_notifications"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
STANDING_PAGE = "https://algocode.ru/standings_data/b_fall_2023/"
time_now = lambda: datetime.now(tz=timezone("Europe/Moscow"))


class CONFIG:
    filename = f'archive/{time_now().strftime("%m-%d")}'
    data = {}
    old_data = {}
    users = {}
    user_id_by_name = {}
    chats = {}
    page_authors = {}


with open("chats.json", "r", encoding="utf-8") as file:
    CONFIG.chats = json.load(file)
    for key in CONFIG.chats:
        CONFIG.chats[key] = set(CONFIG.chats[key])

female_names = {'Валентина', 'Алена', 'Елена', 'Ксения', 'Анастасия', 'Татьяна', 'Милана', 'Олеся', 'Виктория', 'Надежда', 'Юлия', 'Ярослава', 'София', 'Мария',
                'Софья', 'Дарья', 'Алина', 'Валерия', 'Ирина', 'Арина', 'Елизавета'}

messages = [
    [
        ({"verdict": "(RT)|(TL)|(PE)|(WA)", "penalty": "1"}, [
            "*{name}* начал работать над задачей *{task}*, но понял, что не может найти подходящее решение.",
            "Стоило подумать, а не сразу отсылать свой код. У *{name}* первый штраф по задаче *{task}*",
            "Ой, *{name}* решил отправить код без компиляции. Первый штраф за *{task}* уже в кармане.",
            "*{name}*, взялся за задачу *{task}*, но осознал, что не стоило писать код в блокноте.",
            "*{name}*, приступил к задаче *{task}*, но застрял в раздумьях.",
            "Не спеши, *{name}*, подумай еще раз перед отправкой кода. Штраф за неверную посылку по задаче *{task}* уже прилетел.",
            "Казалось бы, простая задача... Но видимо не для всех. *{name}* получил свой первый штраф за задачу *{task}*",
            "*{name}* старался, писал код... И все это ради того, чтобы получить *{verdict}* по задаче *{task}*",
            "Снова неудача! *{name}* не смог сдать задачу *{task}* с первой попытки",
            "*{name}* решил, что *{verdict}* по задаче *{task}* ему нравится больше, чем *OK*"
        ]),
        ({"verdict": "OK", "penalty": "0"}, [
            "*{name}* уничтожил задачу *{task}* с первой попытки!",
            "*{name}* сдал задачу *{task}* с первой попытки. Наверное, ему просто повезло...",
            "*{name}* мастерски справился с задачей *{task}* с первого раза."
        ]),
        ({"verdict": "OK", "penalty": "[1-9][0-9]*"}, [
            "*{name}* сдал задачу *{task}* после {penalty} неверных посылок.",
            "Ученик *{name}*, изворачиваясь как кот, смог поймать задачу *{task}* с {penalty} попытками, будто это нить из клубка.",
            "Задача *{task}* не могла пройти мимо ученика *{name}*, так что он ее решил после {penalty} попыток, словно с чашкой кофе в руках.",
            "Ученик *{name}* решил задачу *{task}* с {penalty} попытками, и его успех был таким громким, что можно было услышать аплодисменты по всему кружку.",
            "Задача *{task}* пыталась противостоять ученику *{name}*, но он с {penalty} попытками доказал ей, кто здесь настоящий босс.",
            "Ученик *{name}*, с {penalty} попытками на счету, без проблем разгадал задачу *{task}*, и даже сервера восторженно аплодировали.",
            "Ученик *{name}*, с {penalty} попытками в запасе, покорил задачу *{task}*, словно владелец клавиатуры-танка.",
            "Задача *{task}* пыталась сбежать от ученика *{name}*, но после {penalty} попыток он ее настиг и решил с легкостью.",
            "Ученик *{name}*, с {penalty} попытками, справился с задачей *{task}* так легко, словно это была задачка для младших классов.",
            "Ученик *{name}*, несмотря на {penalty} ошибки, успешно выполнил задание *{task}*."
        ]),
        ({"verdict": "(RT)|(TL)|(PE)|(WA)", "penalty": "[1-9]0"}, [
            "Бесконечность не предел! У *{name}* уже {penalty} неверных посылок по задаче *{task}*.",
            "У *{name}* только что стало {penalty} неверных посылок по задаче *{task}*. Может ему стоило выбрать географию, а не программирование?",
            "*{name}* получает {penalty} штраф по задаче *{task}*. Кажется, пора забрать у него ноутбук.",
            "*{name}* никак не может справиться с вердиктом *{verdict}* в задаче *{task}*. У него уже *{penalty}* неверных посылок!"
        ]),
        ({"verdict": "RJ"}, [
            "BAN! *{name}* - *{task}*"
        ]),
    ],
    [
        ({"verdict": "(RT)|(TL)|(PE)|(WA)", "penalty": "1"}, [
            "*{name}* начала работать над задачей *{task}*, но поняла, что не может найти подходящее решение.",
            "Стоило подумать, а не сразу отсылать свой код. У *{name}* первый штраф по задаче *{task}*",
            "Ой, *{name}* решила отправить код без компиляции. Первый штраф за *{task}* уже в кармане.",
            "*{name}*, взялась за задачу *{task}*, но осознала, что не стоило писать код в блокноте.",
            "*{name}*, приступила к задаче *{task}*, но застряла в раздумьях.",
            "Не спеши, *{name}*, подумай еще раз перед отправкой кода. Штраф за неверную посылку по задаче *{task}* уже прилетел.",
            "Казалось бы, простая задача... Но видимо не для всех. *{name}* получила свой первый штраф за задачу *{task}*",
            "*{name}* старалась, писала код... И все это ради того, чтобы получить *{verdict}* по задаче *{task}*",
            "Снова неудача! *{name}* не смогла сдать задачу *{task}* с первой попытки",
            "*{name}* решила, что *{verdict}* по задаче *{task}* ей нравится больше, чем *OK*"
        ]),
        ({"verdict": "OK", "penalty": "0"}, [
            "*{name}* уничтожила задачу *{task}* с первой попытки!",
            "*{name}* сдала задачу *{task}* с первой попытки. Наверное, ей просто повезло...",
            "*{name}* мастерски справилась с задачей *{task}* с первого раза."
        ]),
        ({"verdict": "OK", "penalty": "[1-9][0-9]*"}, [
            "*{name}* сдала задачу *{task}* после {penalty} неверных посылок.",
            "Ученица *{name}*, изворачиваясь как кошка, смогла поймать задачу *{task}* с {penalty} попытками, будто это нить из клубка.",
            "Задача *{task}* не могла пройти мимо ученицы *{name}*, так что она ее решила после {penalty} попыток, словно с чашкой кофе в руках.",
            "Ученица *{name}* решила задачу *{task}* с {penalty} попытками, и ее успех был таким громким, что можно было услышать аплодисменты по всему кружку.",
            "Задача *{task}* пыталась противостоять ученице *{name}*, но она с {penalty} попытками доказала ей, кто здесь настоящий босс.",
            "Ученица *{name}*, с {penalty} попытками на счету, без проблем разгадала задачу *{task}*, и даже сервера восторженно аплодировали.",
            "Ученица *{name}*, с {penalty} попытками в запасе, покорила задачу *{task}*, словно владелец клавиатуры-танка.",
            "Задача *{task}* пыталась сбежать от ученицы *{name}*, но после {penalty} попыток она ее настигла и решила с легкостью.",
            "Ученица *{name}*, с {penalty} попытками, справилась с задачей *{task}* так легко, словно это была задачка для младших классов.",
            "Ученица *{name}*, несмотря на {penalty} ошибки, успешно выполнила задание *{task}*."
        ]),
        ({"verdict": "(RT)|(TL)|(PE)|(WA)", "penalty": "[1-9]0"}, [
            "Бесконечность не предел! У *{name}* уже {penalty} неверных посылок по задаче *{task}*.",
            "У *{name}* только что стало {penalty} неверных посылок по задаче *{task}*. Может ей стоило выбрать географию, а не программирование?",
            "*{name}* получает {penalty} штраф по задаче *{task}*. Кажется, пора забрать у нее ноутбук.",
            "*{name}* никак не может справиться с вердиктом *{verdict}* в задаче *{task}*. У нее уже *{penalty}* неверных посылок!"
        ]),
        ({"verdict": "RJ"}, [
            "BAN! *{name}* - *{task}*"
        ]),
    ]
]

title_replacements = {
    'Графы 4': 'Графы 4',
    'Геометрия 1': 'Геометрия 1',
    'Графы 3': 'Графы 3',
    'Динамическое программирование 2': 'ДП 2',
    'Дерево отрезков 2': 'ДО 2',
    'Дерево отрезков 1': 'ДО 1',
    'Динамическое программирование 1': 'ДП 1',
    'Графы 2': 'Графы 2',
    'Задачи с двойным запуском': 'Двойной запуск',
    'Бинарный и тернарный поиск. Интерактивные задачи': 'Поиски+Интерактивки',
    'Теория чисел': 'ТЧ',
    'C++, стресс-тестирование и дебаг': 'Дебаг',
    'Строки 2': 'Строки 2',
    'Строки 1': 'Строки 1',
    'Графы 1': 'Графы 1'
}
reversed_title_replacements = {value: key for key, value in title_replacements.items()}

first_solve_message = [
    "⚡ *{name}* стал первым, кто решил задачу *{task}*!",
    "⚡ *{name}* стала первой, кто решил задачу *{task}*!"
]

first_solves_message = """Первые решившие задачу *{task}*:
🥇{first}
🥈{second}
🥉{third}"""
