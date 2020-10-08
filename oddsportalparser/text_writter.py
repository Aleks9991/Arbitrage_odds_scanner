import json
import requests

from datetime import datetime
from bs4 import BeautifulSoup

from oddsportalparser.helper import USER_AGENT, HANDICAP_BET_TYPES, get_dict_from_request

SCOPES = {
    '1': 'FT including OT',
    '2': 'Full Time',
    '3': '1st Half',
    '4': '2nd Half'
}


def __get_bookies():
    base_url = 'https://www.oddsportal.com'
    r = requests.get(base_url, headers=USER_AGENT)
    soup = BeautifulSoup(r.content.decode('utf-8'), 'html.parser')
    src = soup.select_one('script[src^="/res/x/bookies-"]')['src']
    bookies = get_dict_from_request(base_url + src, r'({[\S\s]+});var')
    for b in bookies:
        bookies[b] = bookies[b]['WebName']
    return bookies


def __calc_profit(odds): 
    return round((1 / sum(map(lambda odd: 1 / odd, odds)) - 1) * 100, 2)


with open('oddsportalparser/bet_types.json', 'r') as fp:
    BET_TYPES = json.load(fp)

BOOKIES = __get_bookies()


def gen_file(s):
    text = ''
    text += f'{s["home"]} - {s["away"]}\n'
    for st in s['stakes']:
        bet = BET_TYPES[st['bt']]['name']
        if st['bt'] in HANDICAP_BET_TYPES:
            bet += ' ' + st['handicap']
        odds = []
        for i in ('0', '1'):
            odds.append(list(map(float, st['opts'][i].keys())))
        mp = __calc_profit(map(max, odds))
        text += f'\n{bet} ({SCOPES[st["sc"]]}), MAX PROFIT: {mp}%\n'
        for odd in odds[0]:
            min_pair_odd = 1 / (1 - 1 / odd)
            pair_odds = list(filter(lambda odd: odd > min_pair_odd, odds[1]))
            bl = [BOOKIES[bk] for bk in st['opts']['0'][str(odd)]]
            sep = ' ' if len(pair_odds) == 1 else ':\n'
            text += f'{odd} in {", ".join(bl)} pairs with{sep}'
            for i, p_odd in enumerate(pair_odds, start=1):
                if len(pair_odds) > 1:
                    text += f'\t{i}) '
                pbl = [BOOKIES[bk] for bk in st['opts']['1'][str(p_odd)]]
                pr = __calc_profit((odd, p_odd))
                text += f'{p_odd} in {", ".join(pbl)}, PROFIT: {pr}%\n'

    filepath = f'stakes/{s["id"]}.txt'
    with open(filepath, 'w') as fp:
        fp.write(text)
    return filepath
