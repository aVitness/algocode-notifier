import json
import random
import re
import sys
import time
from datetime import datetime

import psycopg
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from tabulate import tabulate

from data import *

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


def replace_decl(s):
    for x, repl in (("1 неверных посылок", "1 неверной посылки"), ("1 попытками", "1 попыткой")):
        s = s.replace(x, repl)
    return s


def send_messages(name, changes):
    for old, new, task in changes:
        for pattern, messages_list in messages[name.split()[1] in female_names]:
            if re.fullmatch(pattern, new):
                bot.send_message(CHAT_ID, replace_decl(random.choice(messages_list).format(name=name, task=task, tries=new[1:])), parse_mode="markdown")
                break


def send_new_solves(name, solves):
    for task in solves:
        bot.send_message(CHAT_ID, first_solve_message.format(name=name, task=task), parse_mode="markdown")

def find_people_results(source, skip):
    s = re.findall(r'<td class=""[^>]*>[0-9]+</td><td class=""[^>]*>[Bs]+</td><td class="name"[^>]*>[а-яА-ЯёЁ\- ]+</td>', source)
    A = set()
    last_pos = source.rfind(s[0])
    for i in range(len(s)):
        if last_pos == -1:
            break
        if i == len(s) - 1:
            unparsed = source[source.rfind(s[i], last_pos):]
        else:
            unparsed = source[last_pos:source.rfind(s[i + 1], last_pos)]
            last_pos = source.rfind(s[i + 1], last_pos)
        parsed = re.findall(r"<td class=[^>]*>(.*?)</td>", unparsed)

        if 150 < len(parsed) < 300:
            parsed = tuple(parsed[v] for v in range(len(parsed)) if v not in skip)
            A.add(parsed)
    return sorted(A, key=lambda x: int(x[0]))


def find_tasks(source):
    titles = list(map(title_replacements.get, re.findall(r'<td class="gray contest_title"[^>]*><a href="[^"]*">(.*?)</a></td>', source)))
    tasks = re.findall(r'td class="problem_letter gray"[^>]*title="([^"]*)"[^>]*>([A-Z]*)</td>', source)
    result = []
    prev = ""
    i = 5
    to_skip = []
    for task, letter in tasks:
        if letter < prev:
            to_skip.append(i)
            i += 1
            del titles[0]
        if f"{titles[0]} - {letter} ({task})" not in result:
            result.append(f"{titles[0]} - {letter} ({task})")
        prev = letter
        i += 1
    to_skip.append(i)
    return result, to_skip


def leaderboard():
    filename = f'{datetime.now().strftime("%m-%d")}'
    with psycopg.connect(DATABASE) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT data FROM algocode WHERE id = %s", (filename + "_first",))
            old_A, = cursor.fetchone()
            old_A = json.loads(old_A)
            cursor.execute("SELECT data FROM algocode WHERE id = %s", (filename,))
            A, = cursor.fetchone()
            A = json.loads(A)
    pairs = [[x, y] for x in old_A for y in A if x[2] == y[2]]
    UPDATES = {
        "+": [],
        "-": []
    }

    for x, y in pairs:
        _, _, full_name, old_ok, old_penalty = x[:5]
        _, _, _, ok, penalty = y[:5]
        old_ok, old_penalty, ok, penalty = map(int, (old_ok, old_penalty, ok, penalty))
        UPDATES["+"].append((ok - old_ok, ok, old_ok, full_name))
        UPDATES["-"].append((penalty - old_penalty, penalty, old_penalty, full_name))
    UPDATES["+"].sort(reverse=True)
    UPDATES["-"].sort(reverse=True)
    headers = ("*", "Имя", "Δ", "Было", "Стало")

    date = datetime.now().strftime("%d.%m")
    data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["+"][:10], 1))
    result = f"Топ 10 по успешным посылкам за {date}\n" + "```\n" + tabulate(data, headers, tablefmt="psql") + "\n```"
    message = bot.send_message(ME_CHAT_ID, result, parse_mode="markdown")
    # bot.unpin_all_chat_messages(chat_id=message.chat.id)
    # bot.pin_chat_message(chat_id=message.chat.id, message_id=message.message_id, disable_notification=True)
    # bot.delete_message(chat_id=message.chat.id, message_id=message.message_id + 1)
    data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["-"][:10], 1))
    result = f"Топ 10 по штрафам за {date}\n" + "```\n" + tabulate(data, headers, tablefmt="psql") + "\n```"
    message = bot.send_message(ME_CHAT_ID, result, parse_mode="markdown")
    # bot.pin_chat_message(chat_id=message.chat.id, message_id=message.message_id, disable_notification=True)
    # bot.delete_message(chat_id=message.chat.id, message_id=message.message_id + 1)


def task_stats():
    headers = ("~ Задача", "Попыток", "Решавших", "Успешных", "% успешных", "% решивших")
    align = ("left", "right", "right", "right", "right", "right")
    driver.get("https://algocode.ru/standings/b_fall_2023/")
    time.sleep(3.5)
    source = driver.page_source
    source = re.sub(r'(<td class[^>]*title="([+-][0-9]+)[^>]*>)<p class="small">[+-]∞</p></td>', lambda m: f'{m[1]}{m[2]}</td>', source)
    tasks, skip = find_tasks(source)
    A = find_people_results(source, set(skip))

    data = []
    for i in range(len(tasks)):
        current = [tasks[i], 0, 0, 0, None, None]
        for x in A:
            if x[5 + i]:
                current[1] += int(x[5 + i][1:] or "1")
                current[2] += 1
            if x[5 + i].startswith("+"):
                current[3] += 1
        if current[2] == 0:
            current[4] = current[5] = "0.0%"
        else:
            current[4] = f"{current[3] / current[1] * 100:.2f}%"
            current[5] = f"{current[3] / current[2] * 100:.2f}%"
        data.append(current)
    print(tabulate(data, headers, colalign=align))


def load_old():
    filename = f'{datetime.now().strftime("%m-%d")}'
    with psycopg.connect(DATABASE) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT data FROM algocode WHERE id = %s", (filename,))
            data, = cursor.fetchone()
    return json.loads(data)


def check_if_not_exists(A):
    filename = f'{datetime.now().strftime("%m-%d")}'
    with psycopg.connect(DATABASE) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT data FROM algocode WHERE id = %s", (filename,))
            data = cursor.fetchone()
            if data is None:
                A = json.dumps(A)
                cursor.execute("INSERT INTO algocode (id, data) VALUES (%s, %s)", (filename, A))
                cursor.execute("INSERT INTO algocode (id, data) VALUES (%s, %s)", (filename + "_first", A))
                connection.commit()
                return True
    return False


def save(A):
    filename = f'{datetime.now().strftime("%m-%d")}'
    with psycopg.connect(DATABASE) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE algocode SET data = %s WHERE id = %s", (json.dumps(A), filename))
            connection.commit()


if "local" in sys.argv:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
else:
    # for github
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import chromedriver_autoinstaller
    from pyvirtualdisplay import Display

    display = Display(visible=0, size=(800, 800))
    display.start()

    chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists
    # and if it doesn't exist, download it automatically,
    # then add chromedriver to path

    chrome_options = webdriver.ChromeOptions()
    # Add your options as needed
    options = [
        # Define window size here
        "--window-size=1200,1200",
        "--ignore-certificate-errors"

        # "--headless",
        # "--disable-gpu",
        # "--window-size=1920,1200",
        # "--ignore-certificate-errors",
        # "--disable-extensions",
        # "--no-sandbox",
        # "--disable-dev-shm-usage",
        # '--remote-debugging-port=9222'
    ]

    for option in options:
        chrome_options.add_argument(option)

    driver = webdriver.Chrome(options=chrome_options)


def job():
    print(datetime.now())
    driver.get("https://algocode.ru/standings/b_fall_2023/")
    time.sleep(5)
    source = driver.page_source
    print(len(source))
    source = re.sub(r'(<td class[^>]*title="([+-][0-9]+)[^>]*>)<p class="small">[+-]∞</p></td>', lambda m: f'{m[1]}{m[2]}</td>', source)
    try:
        tasks, skip = find_tasks(source)
        A = find_people_results(source, set(skip))
    except IndexError:
        print(">>>>> IndexError?")
        exit(0)
    print(len(json.dumps(A)))
    exit()
    if check_if_not_exists(A):
        return

    old_A = load_old()
    if len(A[0]) > len(old_A[0]):
        save(A)
        exit()
    total_solves = [0] * len(tasks)
    for x in old_A:
        for i, v in enumerate(x[5:]):
            if v.startswith("+"):
                total_solves[i] += 1

    pairs = [[x, y] for x in old_A for y in A if x[2] == y[2]]
    for x, y in pairs:
        pos, type, full_name, ok, penalty = x[:5]
        changes = []
        new_solves = []
        for i, (old, new) in enumerate(zip(x[5:], y[5:])):
            if old != new:
                if re.fullmatch("\+.*", new) and total_solves[i] == 0:
                    new_solves.append(tasks[i])
                changes.append((old, new, tasks[i]))
        if changes:
            send_messages(full_name, changes)
        if new_solves:
            send_new_solves(full_name, new_solves)
    save(A)
    
if "leaderboard" in sys.argv:
    leaderboard()
    exit()

job()
