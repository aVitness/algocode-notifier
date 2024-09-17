import re

import pymorphy3
from pytrovich.enums import Case, Gender
from pytrovich.enums import NamePart
from pytrovich.maker import PetrovichDeclinationMaker

with open("utils/female_names_rus.txt", mode="r", encoding="utf-8") as file:
    female_names = set(file.read().split())

morph = pymorphy3.MorphAnalyzer()
gender_regex = re.compile(r"\[([^\[\]]+)\]")
number_regex = re.compile(r"%([^%]+)%")
case_regex = re.compile(r"@([^@]+)@")
maker = PetrovichDeclinationMaker()
case_translations = {"gent": Case.GENITIVE, "datv": Case.DATIVE, "accs": Case.ACCUSATIVE, "ablt": Case.INSTRUMENTAL, "loct": Case.PREPOSITIONAL}


def detect(name):
    return (Gender.MALE, Gender.FEMALE)[name in female_names]


def fix_number(match):
    number, word, case = match[1].split()
    return f"{number} {morph.parse(word)[0].inflect({case}).make_agree_with_number(int(number)).word}"


def fix_case(match):
    surname, name, case = match[1].split()
    case = case_translations[case]

    gender = detect(name)
    name = maker.make(NamePart.FIRSTNAME, gender, case, name)
    surname = maker.make(NamePart.LASTNAME, gender, case, surname)
    return f"{surname} {name}"


def fix_main_message(message, is_female):
    message = gender_regex.sub(lambda match: match[1].split("/")[is_female], message)
    message = number_regex.sub(fix_number, message)
    message = case_regex.sub(fix_case, message)
    return message
