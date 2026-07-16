import os
from config import DATA


def get_series():

    series = []

    for item in sorted(os.listdir(DATA)):

        path = os.path.join(DATA, item)

        if os.path.isdir(path):
            series.append(item)

    return series


def get_sets(series):

    folder = os.path.join(DATA, series)

    sets = []

    if not os.path.exists(folder):
        return sets

    for item in sorted(os.listdir(folder)):

        path = os.path.join(folder, item)

        if os.path.isfile(path):
            continue

        sets.append(item)

    return sets


def get_cards(series, set_name):

    folder = os.path.join(DATA, series, set_name)

    cards = []

    if not os.path.exists(folder):
        return cards

    for item in sorted(os.listdir(folder)):

        if item.endswith(".ts"):
            cards.append(item)

    return cards