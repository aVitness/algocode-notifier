import copy

import aiohttp

from config import STANDINGS_PAGES

USERS = {}
USERS_BY_NAME = {}
CONTESTS = {}


class Standings:
    def __init__(self, url):
        self.url = url
        self.data = {}
        self.old_data = {}

        self.scores = {}

    async def load(self, retries=2):
        if retries == 0:
            return False
        self.old_data = copy.deepcopy(self.data)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                self.data = await response.json(encoding="utf-8")
                status = response.status
        if status != 200:
            return await self.load(retries - 1)

        for user in self["users"]:
            user["id"] = str(user["id"])
            USERS[user["id"]] = user
            USERS_BY_NAME[user["name"]] = user

        self.scores = {}
        for contest in self["contests"]:
            contest["id"] = str(contest["id"])
            CONTESTS[contest["id"]] = contest
            for user_id, solves in contest["users"].items():
                if user_id not in self.scores:
                    self.scores[user_id] = [0, 0]
                for result in solves:
                    self.scores[user_id][1] += result["penalty"]
                    if result["verdict"] == "OK":
                        self.scores[user_id][0] += 1
        return True

    def __getitem__(self, item):
        return self.data.get(item, [])


STANDINGS = [Standings(url) for url in STANDINGS_PAGES]


def get_total_scores():
    scores = {}
    for table in STANDINGS:
        for user_id, score in table.scores.items():
            if user_id not in scores:
                scores[user_id] = [0, 0]
            scores[user_id][0] += score[0]
            scores[user_id][1] += score[1]
    return scores
