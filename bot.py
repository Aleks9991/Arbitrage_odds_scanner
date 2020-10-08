import re
import os

from datetime import datetime
from itertools import groupby

from telebot import TeleBot
from telebot import types

from oddsportalparser.helper import get_next_matches_table, get_events, get_event_urls, get_stakes
from oddsportalparser.text_writter import gen_file
from config import *

bot = TeleBot(API_TOKEN)


def __gr(it, fmt):
    return groupby(
        it,
        key=lambda e: datetime.fromtimestamp(e[1]).strftime(fmt)
    )


def get_events_markup():
    events = get_events(get_next_matches_table())
    events.sort(key=lambda e: e[1])
    markup = types.InlineKeyboardMarkup()
    btns = []
    for h, el in __gr(events, '%H'):
        time = f'{h}:00-{h}:59'
        btns.append(
            types.InlineKeyboardButton(
                f'{time} ({len(list(el))})',
                callback_data=f't_{time}'
            )
        )
    markup.add(*tuple(btns))
    markup.add(
        types.InlineKeyboardButton(
            '🔄 Обновить список',
            callback_data=f'update_events_{hash(markup)}'
        )
    )
    return markup


@bot.message_handler(commands='/events')
def events_command(msg: types.Message):
    bot.send_message(
        msg.chat.id,
        f'*Список предстоящих матчей*\n'
        f'_Выберите время начала матча_',
        reply_markup=get_events_markup(),
        parse_mode='Markdown'
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith('update_events'))
def update_events(call: types.CallbackQuery):
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_events_markup()
    )


@bot.callback_query_handler(func=lambda c: re.match(r't_\d{2}:00-\d{2}:59$', c.data))
def time_selected(call: types.CallbackQuery):
    d_time = call.data[2:]
    events = get_events(get_next_matches_table())
    el = list(filter(
        lambda e: datetime.fromtimestamp(e[1]).strftime('%H') == d_time[:2],
        events
    ))
    el_str = ''
    for e in el:
        t = datetime.fromtimestamp(e[1]).strftime('%H:%M')
        el_str += f'\n_{t}_ *{e[2]}* (/e\_{e[0]})'
    bot.send_message(
        call.message.chat.id,
        f'*Список матчей сегодня в {d_time}*\n'
        f'Всего событий: {len(el)}\n'
        f'{el_str}',
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda m: re.match('/e_\w{8}', m.text))
def match_selected(msg: types.Message):
    event_id = msg.text[3:]
    urls = get_event_urls(get_next_matches_table())
    url = next((url for url in urls if url[:-1].endswith(event_id)), None)
    if url is None:
        bot.send_message(
            msg.chat.id,
            'Данный матч не найден или уже начался'
        )
    else:
        st = get_stakes(url)
        if st['stakes']:
            filepath = gen_file(get_stakes(url))
            bot.send_document(
                msg.chat.id,
                open(filepath, 'rb'),
                caption='Файл с арбитражными исходами на выбранный матч'
            )
            os.remove(filepath)
        else:
            bot.send_message(
                msg.chat.id,
                'На данный матч арбитражных исходов не найдено'
            )


bot.polling(none_stop=True, timeout=60)
