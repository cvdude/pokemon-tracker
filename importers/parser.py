import re


def find(pattern, text):

    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)

    if m:
        return m.group(1).strip()

    return None


def parse_card(text):

    card = {}

    card["name"] = find(r'en:\s*"([^"]+)"', text)
    card["artist"] = find(r'illustrator:\s*"([^"]+)"', text)
    card["rarity"] = find(r'rarity:\s*"([^"]+)"', text)
    card["hp"] = find(r'hp:\s*([0-9]+)', text)
    card["stage"] = find(r'stage:\s*"([^"]+)"', text)
    card["category"] = find(r'category:\s*"([^"]+)"', text)
    card["suffix"] = find(r'suffix:\s*"([^"]+)"', text)
    card["illustrator"] = find(r'illustrator:\s*"([^"]+)"', text)
    card["dex_id"] = find(r'dexId:\s*\[\s*([0-9]+)', text)
    card["evolves_from"] = find(r'evolveFrom:.*?en:\s*"([^"]+)"', text)
    card["regulation_mark"] = find(r'regulationMark:\s*"([^"]+)"', text)

    return card