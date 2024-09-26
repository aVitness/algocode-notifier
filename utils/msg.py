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
    data = match[1].split()
    middlename = None
    if len(data) == 3:
        surname, name, case = data
    elif len(data) == 4:
        surname, name, middlename, case = data
    else:
        return data[0]

    case = case_translations[case]
    gender = detect(name)

    name = maker.make(NamePart.FIRSTNAME, gender, case, name)
    surname = maker.make(NamePart.LASTNAME, gender, case, surname)
    result = f"{surname} {name}"
    if middlename is not None:
        middlename = maker.make(NamePart.MIDDLENAME, gender, case, middlename)
        result += f" {middlename}"
    return result


def fix_main_message(message, is_female):
    message = gender_regex.sub(lambda match: match[1].split("/")[is_female], message)
    message = number_regex.sub(fix_number, message)
    message = case_regex.sub(fix_case, message)
    return message
