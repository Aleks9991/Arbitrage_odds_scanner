import os
import time
import json

from multiprocessing import Pool

from helper import *


table = get_next_matches_table()
urls = parse_event_urls(table)

with Pool(25) as p:
    data = p.map(get_stakes, urls)
for d in data:
    if not d['stakes']:
        data.remove(d)

if data:
    dates = parse_event_dates(table, map(lambda d: d['id'], data))
    for d in data:
        d['date'] = dates[d['id']]

path = f'results/{int(time.time())}'
os.mkdir(path)
with open(os.path.join(path, 'stakes.json'), 'w') as fp:
    json.dump(data, fp, separators=(',', ':'))

print(len(urls))
