from tabulate import tabulate

from utils.files import load_from_file
from utils.standings import get_total_scores, USERS
from utils.times import get_archive_name, get_current_time


def generate_leaderboard(date):
    old_stats = load_from_file(get_archive_name(date))
    UPDATES = {
        "+": [],
        "-": []
    }
    new_stats = get_total_scores()

    for user_id in USERS:
        old_ok, old_penalty = old_stats.get(user_id, (0, 0))
        ok, penalty = new_stats.get(user_id, (0, 0))
        full_name = USERS[user_id]["name"]
        UPDATES["+"].append((ok - old_ok, ok, old_ok, full_name))
        UPDATES["-"].append((penalty - old_penalty, penalty, old_penalty, full_name))
    UPDATES["+"].sort(reverse=True)
    UPDATES["-"].sort(reverse=True)
    headers = ("*", "Имя", "Δ", "Было", "Стало")

    date = date.strftime("%d.%m")
    if date != get_current_time().strftime("%d.%m"):
        date += f' - {get_current_time().strftime("%d.%m")}'
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["+"][:10], 1))
    score_result = f"Топ 10 по успешным посылкам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    table_data = ((i, x[3], x[0], x[2], x[1]) for i, x in enumerate(UPDATES["-"][:10], 1))
    penalty_result = f"Топ 10 по штрафам за {date}\n" + "```\n" + tabulate(table_data, headers, tablefmt="psql") + "\n```"
    return score_result, penalty_result
