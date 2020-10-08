import re
import json
import requests

from datetime import datetime
from urllib.parse import unquote

from bs4 import BeautifulSoup


USER_AGENT = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'
}

SCANNABLE_BET_TYPES = ('2', '3', '5', '6', '10', '13')
HANDICAP_BET_TYPES = ('2', '5')


def get_dict_from_request(url, pattern=r'{[\S\s]+}', referer=None):
    headers = {}
    if referer is not None:
        headers.update({'Referer': referer})
    headers.update(USER_AGENT)
    r = requests.get(url, headers=headers)
    data = re.findall(pattern, r.content.decode('utf-8'))[0]
    return json.loads(data)


def get_next_matches_table():
    date_str = str(datetime.now().strftime('%Y%m%d'))
    matches_url = 'https://www.oddsportal.com/matches/soccer/'
    p = r'new PageNextMatches\(({[\S\s]+})\);var menu_open'
    xhashf = get_dict_from_request(matches_url, p)['xHashf'][date_str]

    url = f'https://fb.oddsportal.com/ajax-next-games/1/3/1/{date_str}/{unquote(xhashf)}.dat'
    return get_dict_from_request(url, referer=matches_url)['d']


def parse_event_urls(table):
    soup = BeautifulSoup(table, 'html.parser')
    trs = soup.select('.table-main tr[xeid]:not(.deactivate)')
    f = lambda tr: tr.select_one('a[href^="/soccer/"]')['href']
    return list(map(f, trs))


def __prepare_surebets(bt, sc, odds):
    d = {
        'bt': bt,
        'sc': sc,
        'opts': {
            '0': {},
            '1': {}
        }
    }
    for odd in odds[0]:
        if odd == 1:
            continue
        min_pair_odd = 1 / (1 - 1 / odd)
        pair_odds = list(filter(lambda odd: odd > min_pair_odd, odds[1]))
        if pair_odds:
            d['opts']['0'][str(odd)] = odds[0][odd]
            for p_odd in pair_odds:
                d['opts']['1'][str(p_odd)] = odds[1][p_odd]
    return d


def get_stakes(match_url):
    event_url = f'https://www.oddsportal.com{match_url}'
    p = r'new PageEvent\(({[\S\s]+})\);var menu_open'
    data = get_dict_from_request(event_url, p)
    xhashf = data['xhashf']
    url = f'https://fb.oddsportal.com/feed/match/1-1-{data["id"]}-{{bt}}-{{sc}}-{unquote(xhashf)}.dat'
    available_bt = get_dict_from_request(
        url.format(bt=1, sc=2),
        referer=event_url
    )['d']['nav']
    
    st = {
        'id': data['id'],
        'home': data['home'],
        'away': data['away'],
        'event_url': event_url,
        'stakes': []
    }
    for bt in available_bt:
        if bt in SCANNABLE_BET_TYPES:
            for sc in available_bt[bt]:
                od = get_dict_from_request(
                    url.format(bt=bt, sc=sc),
                    referer=event_url
                )['d']['oddsdata']['back']
                for bet in od:
                    odds = ({}, {})
                    f = str if type(od[bet]['OutcomeID']) == dict else int
                    for bk_id in od[bet]['odds']:
                        for i, dict_  in enumerate(odds):
                            odd = float(od[bet]['odds'][bk_id][f(i)])
                            if odd not in dict_:
                                dict_[odd] = []
                            dict_[odd].append(bk_id)
                    s = 1 / max(odds[0]) + 1 / max(odds[1])
                    if s < 1:
                        d = __prepare_surebets(bt, sc, odds)
                        if bt in HANDICAP_BET_TYPES:
                            d.update({
                                'handicap': od[bet]['handicapValue']
                            })
                        st['stakes'].append(d)
    return st


def parse_event_dates(table, evnets_ids):
    d = {}
    soup = BeautifulSoup(table, 'html.parser')
    for e_id in evnets_ids:
        td = soup.select_one(f'tr[xeid="{e_id}"] td.table-time')
        d[e_id] = int(re.findall(r't(\d+)', td['class'][2])[0])
    return d


__all__ = [
    'get_next_matches_table',
    'parse_event_urls',
    'get_stakes',
    'parse_event_dates',
    'get_dict_from_request',
    'USER_AGENT',
    'HANDICAP_BET_TYPES'
]
