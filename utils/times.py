import time
from datetime import datetime, timedelta

from pytz import timezone

from config import TIMEZONE, ARCHIVE_FORMAT

page_authors = {}


def get_current_time():
    return datetime.now(tz=timezone(TIMEZONE))


def get_next_daily_leaderboard():
    next_time = get_current_time().replace(hour=23, minute=0, second=0)
    if get_current_time() >= next_time:
        next_time += timedelta(days=1)
    return next_time


def get_next_weekly_leaderboard():
    next_time = get_current_time().replace(hour=15, minute=55, second=0) + timedelta(days=(5 - get_current_time().weekday()) % 7)
    if get_current_time() >= next_time:
        next_time += timedelta(days=7)
    return next_time


def get_archive_name(date):
    return date.strftime(ARCHIVE_FORMAT)


def take_page(callback):
    current_time = int(time.time())
    user, last_used = page_authors.get(callback.message.message_id, (None, 0))
    if user == callback.from_user.id or current_time - last_used >= 45:
        page_authors[callback.message.message_id] = (callback.from_user.id, current_time)
        return True
    return False


def format_time(seconds):
    if seconds <= 0:
        return None
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}"
