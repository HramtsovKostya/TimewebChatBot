# --------------------------------- MAIN ----------------------------------

import config as cfg
import libs.api as api
import libs.saver as saver

import datetime as dt
import schedule as sch
import math as math
import time

from threading import Thread
from telebot import TeleBot
from telebot import types as ts

# -------------------------------------------------------------------------

__bot = TeleBot(cfg.BOT_TOKEN)


@__bot.message_handler(commands=['start'])
def welcome(msg: ts.Message):
    cfg.CHAT_ID = msg.chat.id

    text = 'Добро пожаловать, <b>' + msg.from_user.first_name + '</b>!'
    kb = ts.ReplyKeyboardMarkup(resize_keyboard=True)

    btn_accounts = ts.KeyboardButton('Управление аккаунтами')
    kb.add(btn_accounts)

    btn_notices = ts.KeyboardButton('Рассылка уведомлений')
    kb.add(btn_notices)

    __bot.send_message(msg.chat.id, text, reply_markup=kb, parse_mode='html')


@__bot.message_handler(content_types=['text'])
def start_dialog(msg: ts.Message):
    if msg.text == 'Управление аккаунтами':
        kb = ts.InlineKeyboardMarkup()

        btn_add = ts.InlineKeyboardButton('Добавить', callback_data='add_user')
        btn_delete = ts.InlineKeyboardButton('Удалить', callback_data='delete_user')
        kb.add(btn_add, btn_delete)

        btn_cancel = ts.InlineKeyboardButton('Отмена', callback_data='cancel')
        kb.add(btn_cancel)

        __bot.send_message(msg.chat.id, 'Выберите действие с аккаунтом:', reply_markup=kb)

    elif msg.text == 'Рассылка уведомлений':
        kb = ts.InlineKeyboardMarkup()

        for user in saver.load_users():
            login = user['login']
            btn_user = ts.InlineKeyboardButton(login, callback_data=login)
            kb.add(btn_user)

        btn_cancel = ts.InlineKeyboardButton(text='Отмена', callback_data='cancel')
        kb.add(btn_cancel)

        text = 'Выберите хостинг из списка:'
        __bot.send_message(msg.chat.id, text, reply_markup=kb)

    else:
        __bot.send_message(msg.chat.id, 'Я не знаю, что ответить')


@__bot.callback_query_handler(lambda c: c.data == 'add_user')
def add_user(call: ts.CallbackQuery):
    text = 'Введите логин и пароль от хостинга:'
    __bot.delete_message(call.message.chat.id, call.message.message_id)

    kb = ts.InlineKeyboardMarkup()
    btn_cancel = ts.InlineKeyboardButton('Отмена', callback_data='cancel')
    kb.add(btn_cancel)

    msg = __bot.send_message(call.message.chat.id, text, reply_markup=kb)
    __bot.register_next_step_handler(msg, get_account_auth)


def get_account_auth(msg: ts.Message):
    login, password = msg.text.split(' ')

    if api.get_token(login, password) == 201:
        saver.add_user({
            'login': login,
            'password': password,
            'notify': True
        })

        text = 'Хостинг <b>' + login + '</b> успешно добавлен!'
        __bot.send_message(msg.chat.id, text, parse_mode='html')

    else:
        text = 'Не удалось найти хостинг <b>' + login + '</b>!'
        __bot.send_message(msg.chat.id, text, parse_mode='html')


@__bot.callback_query_handler(lambda c: c.data == 'delete_user')
def delete_user(call: ts.CallbackQuery):
    kb = ts.InlineKeyboardMarkup()

    for user in saver.load_users():
        login = user['login']
        btn_user = ts.InlineKeyboardButton(login, callback_data='delete:' + login)
        kb.add(btn_user)

    btn_cancel = ts.InlineKeyboardButton(text='Отмена', callback_data='cancel')
    kb.add(btn_cancel)

    text = 'Выберите хостинг из списка:'
    __bot.send_message(call.message.chat.id, text, reply_markup=kb)


@__bot.callback_query_handler(lambda c: c.data in ['delete:' + u['login'] for u in saver.load_users()])
def select_delete(call: ts.CallbackQuery):
    login = call.data.removeprefix('delete:')

    sel_user = [u for u in saver.load_users() if login == u['login']][0]
    saver.del_user(sel_user)

    text = 'Данные хостинга <b>' + login + '</b> успешно удалены!'

    __bot.edit_message_text(text, call.message.chat.id,
                            call.message.message_id, parse_mode='html')


@__bot.callback_query_handler(lambda c: c.data in [u['login'] for u in saver.load_users()])
def select_user(call: ts.CallbackQuery):
    sel_user = [u for u in saver.load_users() if call.data == u['login']][0]

    data = 'notify:' + sel_user['login']
    notify = sel_user['notify']

    btn_text = 'Отключить' if notify else 'Включить'
    text = 'Рассылка уведомлений ' + ('включена!' if notify else 'отключена!')

    kb = ts.InlineKeyboardMarkup()
    btn_notify = ts.InlineKeyboardButton(text=btn_text, callback_data=data)
    btn_cancel = ts.InlineKeyboardButton(text='Отмена', callback_data='cancel')
    kb.add(btn_notify, btn_cancel)

    __bot.edit_message_text(text, call.message.chat.id,
                            call.message.message_id, reply_markup=kb)


@__bot.callback_query_handler(lambda c: c.data in ['notify:' + u['login'] for u in saver.load_users()])
def select_notice(call: ts.CallbackQuery):
    login = call.data.removeprefix('notify:')

    sel_user = [u for u in saver.load_users() if login == u['login']][0]
    notify = sel_user['notify'] = not sel_user['notify']
    saver.edit_user(sel_user)

    text = 'Рассылка уведомлений для хостинга <b>' + login + '</b> успешно '
    text += 'включена!' if notify else 'отключена!'

    __bot.edit_message_text(text, call.message.chat.id,
                            call.message.message_id, parse_mode='html')


@__bot.callback_query_handler(func=lambda c: c.data == 'cancel')
def select_cancel(call: ts.CallbackQuery):
    __bot.delete_message(call.message.chat.id, call.message.message_id)
    __bot.clear_step_handler_by_chat_id(call.message.chat.id)


# -------------------------------------------------------------------------

@sch.repeat(sch.every(1).minutes)
def send_notice():
    for user in saver.load_users():
        if user['notify']:
            api.get_token(user['login'], user['password'])
            data = api.get_finances()

            balance = data['balance']
            cost = data['monthly_cost']

            days = math.floor(balance / cost * 30)
            date = dt.datetime.now() + dt.timedelta(days=days)

            text = 'Оплата хостинга <b>' + user['login'] + '</b> на сумму '
            text += str(cost) + ' руб\nХостинг отключится '
            text += str(date.strftime('%d.%m.%Y')) + 'г.'

            __bot.send_message(cfg.CHAT_ID, text, parse_mode='html')


# -------------------------------------------------------------------------

def run_schedule():
    while True:
        sch.run_pending()
        time.sleep(1)


# -------------------------------------------------------------------------

if __name__ == '__main__':
    thread = Thread(target=run_schedule)
    thread.start()

    try:
        __bot.polling(non_stop=True, timeout=25)

    except Exception as ex:
        print('Первышено время ожидания от сервера!')
        time.sleep(15)

    thread.join()

# -------------------------------------------------------------------------
