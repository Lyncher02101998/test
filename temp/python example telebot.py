#! /usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import mysql.connector
from datetime import datetime
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Mail.ru SMTP Configuration
mailru_user = 'amangeldiyev03@inbox.ru'
mailru_password = '0LGNRmXkc5tY5fCsZGaP'  # Замените на ваш пароль от почты "mail.ru"
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru']  # Замените на адреса получателей

def send_email(subject, body):
    try:
        # Создаем объект сообщения
        msg = MIMEMultipart()
        msg['From'] = mailru_user
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = subject

        # Добавляем текст сообщения в формате MIME
        msg.attach(MIMEText(body, 'plain'))

        # Создаем SMTP-сессию для сервера "mail.ru"
        server = smtplib.SMTP('smtp.mail.ru', 587)
        server.starttls()

        # Авторизуемся на сервере "mail.ru" с вашими учетными данными
        server.login(mailru_user, mailru_password)

        # Отправляем письмо
        server.sendmail(mailru_user, recipient_emails, msg.as_string())

        # Закрываем SMTP-сессию
        server.quit()

        print("Уведомление отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке уведомления:", e)

# Создаем словарь для отслеживания идентификаторов чатов и соответствующих им запросов
user_requests = {}

# Обработчик команды "/start"
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id,
                     f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')

    # Проверяем, если есть запрос, который уже обработан, и обновляем его статус на "выполнено"
    if message.chat.id in user_requests and user_requests[message.chat.id]['processed']:
        cur = conn.cursor()
        terminal_id = user_requests[message.chat.id]['id']
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
        conn.commit()
        bot.send_message(message.chat.id, f'Заявка по терминалу {terminal_id} обработана и выполнена!')
        cur.close()

    # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора
    user_requests[message.chat.id] = {'id': None, 'processed': False}

# Обработчик команды "/done"
@bot.message_handler(commands=['done'])
def mark_request_as_done(message):
    bot.send_message(message.chat.id, 'Введите ID Банкомата/Терминала для которого нужно изменить статус на "выполнено"')
    # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора для команды /done
    user_requests[message.chat.id] = {'id': None, 'processed': False, 'done': True}

    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (mess, today_date))
    existing_done_entries_count = cur.fetchone()[0]

    if existing_done_entries_count == 0:
        bot.send_message(message.chat.id, f'Заявка по терминалу {mess} еще не выполнена сегодня.')
    else:
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        conn.commit()
        bot.send_message(message.chat.id, f'Заявка по терминалу {mess} выполнено.')
        
    cur.close()

# Обработчик сообщений с текстом
@bot.message_handler(content_types=['text'])
def info(message):
    global mess

    # Проверка ID в базе
    mess = message.text
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    # Проверка ID в таблице zabbix
    if id is not None:
        # Проверяем, существует ли уже запись с таким же terminal_id и сегодняшней датой
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        existing_entries_count = cur.fetchone()[0]

        # Получаем статус последней заявки по данному терминалу
        cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (mess,))
        last_status = cur.fetchone()

        if existing_entries_count == 0 or (last_status and last_status[0] == "выполнено"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)
        else:  # Если заявка уже обработана и в статусе "выполнено", разрешаем повторно зафиксировать заявку
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Заявка по данному терминалу {mess} уже выполнена, но вы можете повторно зафиксировать заявку. Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')

    cur.close()

    # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора
    user_requests[message.chat.id] = {'id': mess, 'processed': False}

# Функция для сохранения запроса в БД
# Функция для сохранения запроса в БД
def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()

    # Проверяем, существует ли уже запись с таким же terminal_id и сегодняшней датой
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        # Если на сегодня нет записей, сохраняем запрос в БД со статусом "в работе"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                    (terminal_id, failure_type, timestamp, "в работе"))
        conn.commit()

        # Отправляем уведомление на почту о новой заявке
        subject = f'Новая заявка на терминал {terminal_id}'
        body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        # Проверяем, существуют ли выполненные заявки для данного банкомата на сегодня
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            # Если есть хотя бы одна выполненная заявка на текущий день, сохраняем новую заявку со статусом "в работе"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                        (terminal_id, failure_type, timestamp, "в работе"))
            conn.commit()

            # Отправляем уведомление на почту о новой заявке
            subject = f'Новая заявка на терминал {terminal_id}'
            body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
        else:
            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

    cur.close()



# Обработчик действий при нажатии кнопки
@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.send_message(callback.message.chat.id, f'Заявка по данному (ID {mess} Тип: {callback.data}) отправлена!')
        save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)

        # Сбрасываем флаг обработки запроса, чтобы можно было снова зафиксировать обращение по этому банкомату
        user_requests[callback.message.chat.id]['processed'] = False

        # Проверяем, была ли команда /done введена для этого запроса
        if user_requests[callback.message.chat.id].get('done', False):
            cur = conn.cursor()
            today_date = date.today().strftime('%Y-%m-%d')
            cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
            conn.commit()
            
            # Отправляем уведомление на почту об выполнении заявки
            subject = f'Заявка на терминал {mess} выполнена'
            body = f'Заявка на терминал {mess} выполнена.'
            send_email(subject, body) 

            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {mess} выполнена.')
            cur.close()

    else:
        bot.send_message(callback.message.chat.id, f'Ошибка!')

# Функция для работы бота онлайн
bot.infinity_polling()

# Не забудьте закрыть соединение, когда закончите работу с базой данных
conn.close


# тут не работает обработка заявки
#! /usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import mysql.connector
from datetime import datetime
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
from email.parser import BytesParser
from email.policy import default
import email
import re
import time
import quopri
import chardet

# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Mail.ru SMTP Configuration
mailru_user = 'amangeldiyev03@inbox.ru'
mailru_password = 'BhUfckkEhhV3HX6vtmk3'  # Замените на ваш пароль от почты "mail.ru"
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru']  # Замените на адреса получателей

# Параметры для специальной почты
special_email = 'bcc_bot@mail.ru'
special_email_password = '4Hur55f1jbKpazTj8hSV'


def send_email(subject, body):
    try:
        # Создаем объект сообщения
        msg = MIMEMultipart()
        msg['From'] = mailru_user
        msg['To'] = ', '.join(recipient_emails) 
        msg.attach(MIMEText(body, 'plain'))

        # Создаем SMTP-сессию для сервера "mail.ru"
        server = smtplib.SMTP('smtp.mail.ru', 587)
        server.starttls()

        # Авторизуемся на сервере "mail.ru" с вашими учетными данными
        server.login(mailru_user, mailru_password)

        # Отправляем письмо
        server.sendmail(mailru_user, recipient_emails, msg.as_string())

        # Закрываем SMTP-сессию
        server.quit()

        print("Уведомление отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке уведомления:", e)

# Создаем словарь для отслеживания идентификаторов чатов и соответствующих им запросов
user_requests = {}

# Обработчик команды "/start"
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id,
                     f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')

    # Проверяем, если есть запрос, который уже обработан, и обновляем его статус на "выполнено"
    if message.chat.id in user_requests and user_requests[message.chat.id]['processed']:
        cur = conn.cursor()
        terminal_id = user_requests[message.chat.id]['id']
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
        conn.commit()
        bot.send_message(message.chat.id, f'Заявка по терминалу {terminal_id} обработана и выполнена!')
        cur.close()

    # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора
    user_requests[message.chat.id] = {'id': None, 'processed': False}

# # Обработчик команды "/done"
# @bot.message_handler(commands=['done'])
# def mark_request_as_done(message):
#     bot.send_message(message.chat.id, 'Введите ID Банкомата/Терминала для которого нужно изменить статус на "выполнено"')
#     # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора для команды /done
#     user_requests[message.chat.id] = {'id': None, 'processed': False, 'done': True}

#     cur = conn.cursor()
#     today_date = date.today().strftime('%Y-%m-%d')
#     cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (mess, today_date))
#     existing_done_entries_count = cur.fetchone()[0]

#     if existing_done_entries_count == 0:
#         bot.send_message(message.chat.id, f'Заявка по терминалу {mess} еще не выполнена сегодня.')
#     else:
#         cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
#         conn.commit()
#         bot.send_message(message.chat.id, f'Заявка по терминалу {mess} выполнено.')

#     cur.close()

# Обработчик сообщений с текстом
@bot.message_handler(content_types=['text'])
def info(message):
    global mess

    # Проверка ID в базе
    mess = message.text
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    # Проверка ID в таблице zabbix
    if id is not None:
        # Проверяем, существует ли уже запись с таким же terminal_id и сегодняшней датой
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        existing_entries_count = cur.fetchone()[0]

        # Получаем статус последней заявки по данному терминалу
        cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (mess,))
        last_status = cur.fetchone()

        if existing_entries_count == 0 or (last_status and last_status[0] == "выполнено"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)
        else:  # Если заявка уже обработана и в статусе "выполнено", разрешаем повторно зафиксировать заявку
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Заявка по данному терминалу {mess} уже выполнена, но вы можете повторно зафиксировать заявку. Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')

    cur.close()

    # Обновляем запись идентификатора пользователя в словаре при вводе нового идентификатора
    user_requests[message.chat.id] = {'id': mess, 'processed': False}

# Функция для сохранения запроса в БД
def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()

    # Проверяем, существует ли уже запись с таким же terminal_id и сегодняшней датой
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        # Если на сегодня нет записей, сохраняем запрос в БД со статусом "в работе"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                    (terminal_id, failure_type, timestamp, "в работе"))
        conn.commit()

        # Отправляем уведомление на почту о новой заявке
        subject = f'Новая заявка на терминал {terminal_id}'
        body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        # Проверяем, существуют ли выполненные заявки для данного банкомата на сегодня
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            # Если есть хотя бы одна выполненная заявка на текущий день, сохраняем новую заявку со статусом "в работе"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                        (terminal_id, failure_type, timestamp, "в работе"))
            conn.commit()

            # Отправляем уведомление на почту о новой заявке
            subject = f'Новая заявка на терминал {terminal_id}'
            body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
        else:
            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

    cur.close()

# Обработчик действий при нажатии кнопки
@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.send_message(callback.message.chat.id, f'Заявка по данному (ID {mess} Тип: {callback.data}) отправлена!')
        save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)

        # Сбрасываем флаг обработки запроса, чтобы можно было снова зафиксировать обращение по этому банкомату
        user_requests[callback.message.chat.id]['processed'] = False

        # Проверяем, была ли команда /done введена для этого запроса
        if user_requests[callback.message.chat.id].get('done', False):
            cur = conn.cursor()
            today_date = date.today().strftime('%Y-%m-%d')
            cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
            conn.commit()

            # Отправляем уведомление на почту об выполнении заявки
            subject = f'Заявка на терминал {mess} выполнена'
            body = f'Заявка на терминал {mess} выполнена.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {mess} выполнена.')
            cur.close()

    else:
        bot.send_message(callback.message.chat.id, f'Ошибка!')

        
def get_text_from_email(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset() or chardet.detect(part.get_payload(decode=True))['encoding']
                decoded_text = part.get_payload(decode=True).decode(charset)
                text += decoded_text
    else:
        charset = msg.get_content_charset() or chardet.detect(msg.get_payload(decode=True))['encoding']
        decoded_text = msg.get_payload(decode=True).decode(charset)
        text += decoded_text
    return text




# Функция для обновления статуса заявки в БД
def update_request_status_in_db(terminal_id, status):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("UPDATE requests SET status = %s WHERE terminal_id = %s AND DATE(timestamp) = %s", (status, terminal_id, today_date))
    conn.commit()
    cur.close()

def process_received_email(msg):
    subject = msg['subject']
    body = get_text_from_email(msg)

    # Check if "выполнено" is in the body of the email
    if "выполнено" in body.lower():
        terminal_id = re.search(r'ID Банкомата/Терминала:\s*(\S+)', body, re.IGNORECASE)
        if terminal_id:
            terminal_id = terminal_id.group(1)
            update_request_status_in_db(terminal_id, "выполнено")



def email_listener():
    while True:
        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL('imap.mail.ru')

            # Login to the mailbox
            mail.login(special_email, special_email_password)

            # Select the mailbox you want to listen to (e.g., 'INBOX')
            mail.select('bccbot')

            # Search for all unseen messages
            status, response = mail.search(None, 'UNSEEN')

            if status == 'OK':
                for message_num in response[0].split():
                    # Fetch the email message
                    status, msg_data = mail.fetch(message_num, '(RFC822)')
                    if status == 'OK':
                        msg = email.message_from_bytes(msg_data[0][1])

                        process_received_email(msg)

                        # Extract the subject and body of the email
                        subject = msg['subject']
                        body = msg.get_paylo(preferencelist=('plain',)).get_content()

                        # Process the email and update the status in the database
                        if subject.startswith('Заявка выполнена') and 'Терминал' in body:
                            # Extract the terminal_id from the email body
                            terminal_id_match = re.search(r'Терминал (\d+)', body)
                            if terminal_id_match:
                                terminal_id = terminal_id_match.group(1)

                                # Update the status in the database to 'выполнено'
                                update_request_status_in_db(terminal_id, 'выполнено')

                        # Mark the email as seen
                        mail.store(message_num, '+FLAGS', '\Seen')

            # Logout from the mailbox
            mail.logout()

            # Wait for 10 seconds before checking for new emails again
            time.sleep(10)

        except Exception as e:
            print("Error while listening for emails:", e)

# Start the email listener in a separate thread
import threading
email_listener_thread = threading.Thread(target=email_listener)
email_listener_thread.daemon = True
email_listener_thread.start()




# Запускаем бота
bot.infinity_polling()

# Не забудьте закрыть соединение, когда закончите работу с базой данных
conn.close()




# 3 почтага сообщение жберп выполнено ауыстыру

#! /usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import mysql.connector
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email
import re
import time
import chardet
import threading

# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Mail.ru SMTP Configuration
mailru_user = 'amangeldiyev03@inbox.ru'
mailru_password = 'BhUfckkEhhV3HX6vtmk3'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru']

# Параметры для специальной почты
special_email = 'amangeldiyev03@inbox.ru'
special_email_password = 'BhUfckkEhhV3HX6vtmk3'

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = mailru_user
        msg['To'] = ', '.join(recipient_emails)
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.mail.ru', 587)
        server.starttls()
        server.login(mailru_user, mailru_password)
        server.sendmail(mailru_user, recipient_emails, msg.as_string())
        server.quit()

        print("Уведомление отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке уведомления:", e)

user_requests = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')
    if message.chat.id in user_requests and user_requests[message.chat.id]['processed']:
        cur = conn.cursor()
        terminal_id = user_requests[message.chat.id]['id']
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
        conn.commit()
        bot.send_message(message.chat.id, f'Заявка по терминалу {terminal_id} обработана и выполнена!')
        cur.close()

    user_requests[message.chat.id] = {'id': None, 'processed': False}

@bot.message_handler(content_types=['text'])
def info(message):
    global mess
    mess = message.text
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    if id is not None:
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        existing_entries_count = cur.fetchone()[0]
        cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (mess,))
        last_status = cur.fetchone()

        if existing_entries_count == 0 or (last_status and last_status[0] == "выполнено"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Заявка по данному терминалу {mess} уже выполнена, но вы можете повторно зафиксировать заявку. Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')
    
    user_requests[message.chat.id] = {'id': mess, 'processed': False}

def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
        conn.commit()

        subject = f'Новая заявка на терминал {terminal_id}'
        body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
            conn.commit()

            subject = f'Новая заявка на терминал {terminal_id}'
            body = f'Зарегистрирована новая заявка на терминал {terminal_id} с типом сбоя: {failure_type}.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
        else:
            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

    cur.close()

@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.send_message(callback.message.chat.id, f'Заявка по данному (ID {mess} Тип: {callback.data}) отправлена!')
        save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)

        user_requests[callback.message.chat.id]['processed'] = False

        if user_requests[callback.message.chat.id].get('done', False):
            cur = conn.cursor()
            today_date = date.today().strftime('%Y-%m-%d')
            cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
            conn.commit()

            subject = f'Заявка на терминал {mess} выполнена'
            body = f'Заявка на терминал {mess} выполнена.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {mess} выполнена.')
            cur.close()

def get_text_from_email(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset() or chardet.detect(part.get_payload(decode=True))['encoding']
                decoded_text = part.get_payload(decode=True).decode(charset)
                text += decoded_text
    else:
        charset = msg.get_content_charset() or chardet.detect(msg.get_payload(decode=True))['encoding']
        decoded_text = msg.get_payload(decode=True).decode(charset)
        text += decoded_text
    return text



def process_received_email(msg):
    print("Processing received email...")
    subject = msg['subject']
    body = get_text_from_email(msg)

    if "заявка выполнено" in body.lower():
        terminal_id_match = re.search(r'ID Банкомата/Терминала:\s*(\d+)', body, re.IGNORECASE)
        if terminal_id_match:
            terminal_id = terminal_id_match.group(1)
            print("Found terminal ID:", terminal_id)
            update_request_status_in_db(terminal_id, 'выполнено')
            print("Status updated.")

def email_listener():
    while True:
        try:
            print("Listening for new emails...")
            mail = imaplib.IMAP4_SSL('imap.mail.ru')
            mail.login(special_email, special_email_password)
            mail.select('bccexample')

            status, response = mail.search(None, 'UNSEEN')

            if status == 'OK':
                for message_num in response[0].split():
                    print("Processing message:", message_num)
                    status, msg_data = mail.fetch(message_num, '(RFC822)')
                    if status == 'OK':
                        msg = email.message_from_bytes(msg_data[0][1])
                        process_received_email(msg)
                        mail.store(message_num, '+FLAGS', '\Seen')
            mail.logout()
            time.sleep(10)

        except Exception as e:
            print("Error while listening for emails:", e) 


def update_request_status_in_db(terminal_id, status):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    print("Executing SQL query...")
    print("UPDATE requests SET status = %s WHERE terminal_id = %s AND DATE(timestamp) = %s", (status, terminal_id, today_date))
    cur.execute("UPDATE requests SET status = %s WHERE terminal_id = %s AND DATE(timestamp) = %s", (status, terminal_id, today_date))
    conn.commit()
    cur.close()

    
# Запуск прослушивания почты в отдельном потоке
email_thread = threading.Thread(target=email_listener)
email_thread.daemon = True
email_thread.start()

# Запуск бота
bot.polling(none_stop=True)
conn.close()


# счетчик жумыс истеп тур базамен связано

import telebot
from telebot import types
import mysql.connector
from datetime import datetime, date

# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Предварительно определенные ID банкоматов и их наименования
atm_data = {
    "00000144": "ATM1",
    "00000250": "ATM2",
    "00001189": "ATM3"
}

# Типы сбоев
failure_types = {
    'cash_out': 'Не работает снятие',
    'cash_in': 'Не работает пополнение',
    'out_service': 'Устройство не в сервисе',
    'offline': 'Устройство выключено',
    'stuck': 'Устройство зависло'
}

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

user_requests = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала для отправки заявки')
    user_requests[message.chat.id] = {'id': None, 'date': None, 'counter': 0}

@bot.message_handler(content_types=['text'])
def process_request(message):
    atm_id = message.text
    if atm_id in atm_data:
        send_failure_menu(message.chat.id, atm_id)
    else:
        bot.send_message(message.chat.id, f'Некорректный ID Банкомата/Терминала.')

def send_failure_menu(chat_id, atm_id):
    markup = types.InlineKeyboardMarkup()
    for key, value in failure_types.items():
        markup.add(types.InlineKeyboardButton(value, callback_data=f'{key}:{atm_id}'))
    bot.send_message(chat_id, 'Выберите тип сбоя:', reply_markup=markup)

@bot.callback_query_handler(func=lambda callback: callback.data.startswith(tuple(failure_types.keys())))
def callback_message(callback):
    failure_type, atm_id = callback.data.split(':')

    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    
    # Проверяем, есть ли уже запись для данного банкомата и текущей даты
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (atm_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        save_request_to_db(atm_id, failure_type)
        bot.send_message(callback.message.chat.id, f'Спасибо, ваша заявка для банкомата ({atm_id}) с типом сбоя "{failure_types[failure_type]}" успешно зарегистрирована.')
    else:
        cur.execute("UPDATE requests SET counter = counter + 1 WHERE terminal_id = %s AND DATE(timestamp) = %s", (atm_id, today_date))
        conn.commit()
        bot.send_message(callback.message.chat.id, f'Спасибо, ваша заявка для банкомата {atm_data[atm_id]} ({atm_id}) с типом сбоя "{failure_types[failure_type]}" успешно зарегистрирована.')

    conn.commit()
    cur.close()


def save_request_to_db(atm_id, failure_type):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("INSERT INTO requests (terminal_id, timestamp, status, failure_type) VALUES (%s, %s, %s, %s)", (atm_id, datetime.now(), "зарегистрировано", failure_type))
    conn.commit()
    cur.close()

# Запуск бота
bot.polling(none_stop=True)
conn.close()

#4 соединение с сервисдеском

import telebot
from telebot import types
import mysql.connector
from datetime import datetime, date

# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')


# Предварительно определенные ID банкоматов
atm_ids = [
    "00000139", "00000140", "00000141", "00000142", "00000143", "00000144",
    "00000146", "00000147", "00000148", "00000201", "00000202", "00000203",
    "00000204", "00000205", "00000206", "00000208", "00000211", "00000212",
    "00000250", "00000255", "00000258", "00000772", "00000787", "00001169",
    "00001170", "00001171", "00001172", "00001173", "00001174", "00001175",
    "00001176", "00001177", "00001178", "00001179", "00001180", "00001181",
    "00001182", "00001726", "00001727", "00001766", "00002037", "00004340",
    "00004551", "00004562", "00004571", "00004578", "00004582", "00004587",
    "00004593", "00004596", "00004598", "00004601", "00004604", "00004605",
    "00004610", "00004611", "00004613", "00004615", "00004619", "00004620",
    "00004627", "00004628", "00004633", "00004638", "00004641", "00004646",
    "00004648", "00004652", "00004653", "00004655", "00004662", "00004663",
    "00004667", "00004669", "00004672", "00004675", "00004685", "00004686",
    "00004695", "00004700", "00004704", "00004705", "00004706", "00004708",
    "00004711", "00004713", "00004718", "00004719  ", "00004723", "00004726",
    "00004727", "00004732", "00004733", "00004739", "00004745", "00004747",
    "00004750", "00004756", "00004759", "00004764", "00004766", "00004770",
    "00004773", "00004777", "00004782", "00004783", "00004785", "00004788",
    "00004794", "00004795", "00004796", "00004797", "00004798", "00004801",
    "00010306", "00010307", "00010904", "00010932", "00010946", "00010947",
    "00011009", "00011754", "00011755", "00011757", "00011759", "00011762",
    "00011768", "00011769", "00011771", "00011773", "00011809", "00011810",
    "00011811", "00011812", "00011813", "00011815", "00011816", "00011843",
    "00011845", "00011848", "00011849", "00011850", "00011852", "00011855",
    "00011858", "00013022", "00013023", "00013025", "00013026", "00013030",
    "00013048", "00013049", "00013055", "00013058", "00013059", "00013061",
    "00013062", "00013064", "00013074", "00013079", "00013303", "00013343",
    "00013357", "00013358", "00013359", "00013360", "00013361", "00013362",
    "00013363", "00013364", "00013365", "00013375", "00013376", "00013377",
    "00013378", "00013379", "00013380", "00013381", "00013382", "00013385",
    "00013387", "00013392", "00013488", "00013489", "00013490", "00013491",
    "00013492", "00013494", "00013495", "00013496", "00014618", "00030360",
    "00030373", "00030374", "00030375", "00030378", "00030379", "00030380",
    "00030381", "00030816", "00030817", "00030818", "00030819", "00031504",
    "00031505", "00031506", "00031507", "00031508", "00031510", "00031511",
    "00031512", "00031513", "00031514", "00031515", "00031516", "00031517",
    "00031518", "00031520", "00031521", "00031522", "00031523", "00031528",
    "00031529", "00031530", "00031531", "00031532", "00031533", "00031534",
    "00031535", "00031536", "00031537", "00032402", "00032403", "00032404",
    "00032405", "00032406", "00032407", "00032408", "00032409", "00032410",
    "00032411", "00032413", "00032414", "00032415", "00032416", "00032418",
    "00032419", "00032421", "00032422", "00032722", "00032723", "00032724",
    "00032725", "00032726", "00032727", "00032728", "00032729", "00032741",
    "00033471", "00033472", "00033473", "00033489", "00033490", "00033783",
    "00033784", "00033785", "00033819", "00033821", "00033823", "00033826",
    "00033827", "00033829", "00033830", "00033831", "00033832", "00033833",
    "00033835", "00033843", "00033846", "00033919", "00033920", "00033921",
    "00033923", "00033924", "00033926", "00033927", "00033930", "00033931",
    "00033932", "00033933", "00033934", "00033935", "00033936", "00033937",
    "00033938", "00033939", "00033940", "00033941", "00033942", "00033943",
    "00033944", "00033945", "00033946", "00033947", "00033948", "00033949",
    "00033950", "00033951", "00034825", "00040301", "00040308", "00040309",
    "00040310", "00040311", "00040312", "00040313", "00040314", "00040315",
    "00040322", "00040338", "00040339", "00040340", "00040341", "00040517",
    "00040518", "00040540", "00040639", "00040640", "00040644", "00040645",
    "00040689", "00040690", "00040738", "00040739", "00040740", "00040741",
    "00040742", "00040743", "00050634", "00050637", "00050702", "00050703",
    "00050939", "00050940", "00051282", "00051289", "00051349", "00051355",
    "00051360", "00051361", "00051363", "00051364", "00051367", "00051368",
    "00051369", "00051370", "00060385", "00060386", "00060390", "00060391",
    "00060395", "00060396", "00060399", "00060404", "00060422", "00060423",
    "00060425", "00060426", "00060701", "00060702", "00060714", "00060715",
    "00060716", "00060900", "00060901", "00060902", "00060940", "00060941",
    "00060974", "00060975", "00061001", "00061032", "00061033", "00061034",
    "00070007", "00070070", "00070071", "00070072", "00070073", "00070130",
    "00070131", "00070132", "00070133", "00070262", "00070263", "00070354",
    "00070355", "00070417", "00070444", "00070445", "00070446", "00070447",
    "00080138", "00080335", "00080336", "00080337", "00080338", "00080339",
    "00080353", "00080354", "00080355", "00080356", "00080357", "00080368",
    "00080369", "00080385", "00080386", "00080387", "00080388", "00080711",
    "00080712", "00080713", "00080714", "00080715", "00080716", "00080717",
    "00080718", "00080719", "00080720", "00080721", "00080722", "00080723",
    "00080724", "00080725", "00080837", "00080838", "00080839", "00081309",
    "00081310", "00081434", "00081435", "00081523", "00081524", "00081548",
    "00081562", "00081563", "00081564", "00081597", "00081614", "00081615",
    "00081616", "00081617", "00081676", "00081677", "00081678", "00090116",
    "00090117", "00090118", "00090158", "00090159", "00090160", "00090161",
    "00090323", "00090324", "00090374", "00090408", "00090426", "00090450",
    "00090464", "00090465", "00090477", "00090493", "00090510", "00090511",
    "00090526", "00090629", "00100599", "00100613", "00100614", "00100616",
    "00100617", "00100618", "00100619", "00100621", "00100622", "00100623",
    "00100624", "00100741", "00100742", "00100743", "00100744", "00100745",
    "00100746", "00100747", "00101214", "00101227", "00101235", "00101274",
    "00101275", "00101432", "00101433", "00101434", "00101446", "00101464",
    "00101465", "00101522", "00101523", "00101532", "00101536", "00110205",
    "00110207", "00110208", "00110209", "00110210", "00110211", "00110236",
    "00110237", "00110238", "00110241", "00110247", "00110248", "00110249",
    "00110250", "00110251", "00110252", "00110398", "00110418", "00110459",
    "00110460", "00110461", "00110462", "00110465", "00110466", "00110467",
    "00110468", "00110469", "00120099", "00120101", "00120102", "00120129",
    "00120130", "00120274", "00120303", "00120311", "00120390", "00120391",
    "00120392", "00120480", "00120531", "00120559", "00120560", "00130455",
    "00130456", "00130457", "00130458", "00130522", "00130523", "00130524",
    "00130718", "00130719", "00130830", "00130832", "00130833", "00130834",
    "00130835", "00130865", "00130866", "00130867", "00130868", "00130869",
    "00130870", "00130871", "00130872", "00150093", "00150094", "00150096",
    "00150251", "00150252", "00150253", "00150254", "00150255", "00150340",
    "00150345", "00150351", "00150355", "00150359", "00150363", "00150367",
    "00150369", "00150370", "00150371", "00150372", "00150373", "00150374",
    "00150375", "00150376", "00150377", "00150378", "00150379", "00150380",
    "00150433", "00150434", "00150435", "00150436", "00150437", "00150438",
    "00150439", "00150440", "00150441", "00150442", "00150443", "00150444",
    "00150445", "00150629", "00150630", "00150718", "00150733", "00150754",
    "00150761", "00150805", "00150807", "00150808", "00150809", "00150810",
    "00150811", "00150812", "00150813", "00150817", "00150820", "00150827",
    "00150828", "00150829", "00150830", "00150831", "00150832", "00160114",
    "00160142", "00160233", "00160235", "00160236", "00160241", "00160243",
    "00160245", "00160246", "00160248", "00160249", "00160250", "00160251",
    "00160252", "00160253", "00160279", "00160290", "00160291", "00160294",
    "00160295", "00160296", "00160470", "00160471", "00160472", "00160473",
    "00160560", "00160563", "00160566", "00160567", "00160576", "00160577",
    "00160580", "00160581", "00160716", "00160746", "00160749", "00170184",
    "00170185", "00170186", "00170188", "00170189", "00170192", "00170193",
    "00170368", "00170370", "00170373", "00170374", "00170377", "00170383",
    "00170388", "00170391", "00170392", "00170395", "00170399", "00170400",
    "00170492", "00170493", "00170494", "00170495", "00170496", "00170497",
    "00170498", "00170589", "00170729", "00170730", "00170731", "00170782",
    "00170784", "00170836", "00170837", "00170839", "00170840", "00170842",
    "00170843", "00170844", "00170896", "00170897", "00170898", "00170926",
    "00171052", "00180146", "00180148", "00180150", "00180152", "00180154",
    "00180156", "00180226", "00180228", "00180229", "00180230", "00180231",
    "00180232", "00180233", "00180234", "00180235", "00180376", "00180454",
    "00180468", "00180470", "00180478", "00180502", "00180645", "00180646",
    "00180647", "00180648", "00180728", "00180793", "00180795", "00180827",
    "00180829", "00190176", "00190308", "00190309", "00190310", "00190311",
    "00190312", "00190511", "00190512", "00190513", "00190514", "00190515",
    "00190516", "00190517", "00190518", "00190520", "00190521", "00190522",
    "00190523", "00190524", "00190525", "00190593", "00190595", "00190596",
    "00190597", "00190598", "00190599", "00190600", "00190846", "00190847",
    "00190848", "00190870", "00190871", "00190971", "00190973", "00190974",
    "00190976", "00190977", "00190980", "00190988", "00190989", "00190999",
    "00191001", "00191166", "00191170", "00191171", "00191174", "00191175",
    "00191177", "00200066", "00200163", "00200164", "00200334", "00200336",
    "00200338", "00200339", "00200583", "00200600", "00200608", "00200609",
    "00200619", "00200620", "00200628", "00200629", "00200677", "00200678",
    "00200684", "00200685", "00201093", "00201094", "00201095", "00201096",
    "00201097", "00201208", "00201209", "00201210", "00201211", "00201212",
    "00201244", "00201253", "00201254", "00201261", "00201262", "00201263",
    "00201264", "00201265", "00201266", "00201267", "00201268", "00201463",
    "ATM04030", "ATM04036", "ATM04037", "ATM04046", "ATM04052", "ATM04054", 
    "ATM04061", "ATM04081", "ATM04086", "ATM04094","ATM04095", "ATM04100", 
    "ATM04113", "ATM04117", "ATM04119", "ATM04121", "ATM04123", "ATM04125", 
    "ATM04127", "ATM04129","ATM04133", "ATM04139", "ATM04140", "ATM04142", 
    "ATM04149", "ATM04150", "ATM04157", "ATM04158", "ATM04162", "ATM04164",
    "ATM04170", "ATM04171", "ATM04173", "ATM04178", "ATM04179", "ATM04186",
    "ATM04187", "ATM04223", "ATM04237", "51930324", "51930329", "51930322", 
    "50630213", "50830384", "50830383", "51030364", "50830361", "51630135", 
    "51160064", "51160001", "51160038", "51160040", "51160041", "51160042", 
    "51160043", "51160044", "51160046", "51160047", "51160049", "51160050",
    "51160051", "51160052", "51160053", "51160054", "51160055", "51160098", 
    "51160099", "51160056", "51160096", "50130868", "50130316", "50130734", 
    "50130735", "50130737", "50130738", "50130740", "50130743", "50131977", 
    "50131978", "50131980", "50131981", "50131928", "50131941", "50131942", 
    "50131944", "50132170", "50131936", "50131937", "50133265", "50133270",
    "50133269", "50133444", "50133253", "52660083", "51830538", "52760073", 
    "51730078", "51730198", "51730199", "51730799", "51730800", "51660061", 
    "50630108", "50630682", "50630683", "50630684", "51460089", "51460080", 
    "50430096", "50430063", "50430204", "50430205", "50430609", "50430784", 
    "52460057", "52460058", "52460059", "52460060", "52030146", "52030073",
    "52030340", "52030341", "52030342", "52030343", "52030344", "52031197", 
    "52031198", "52031199", "51560079", "51560093", "50530037", "50530093", 
    "50530092", "50530471", "50530472", "50531011", "50531009", "50531013", 
    "52860074", "51930057", "51930955", "51930958", "51930959", "52560072", 
    "51630057", "51630058", "51630055", "51630145", "51860087", "51860088",
    "51860063", "50730012", "50730013", "50730075", "50730311", "50730312", 
    "52260067", "52260068", "52260101", "52260100", "51330066", "51330789", 
    "51330790", "52960062", "52960090", "52960091", "52960092", "51530257", 
    "51530683", "51530684", "51530685", "52360082", "51230573", "51230595", 
    "51260075", "51260076", "51260077", "50330361", "50330740", "50331626",
    "50331637", "50331627", "50331634", "50333672", "50333673", "50333674", 
    "50333675", "50333905", "52160078", "51130016", "51130138", "51130471", 
    "51760069", "51760070", "51760094", "50830079", "50830132", "50831256", 
    "50831257", "50831258", "50831255", "51960084", "52060086", "51030123", 
    "51360081", "50930032", "53060066", "53060085", "53060065", "50130140"
]

# Типы сбоев
failure_types = {
    'cash_out': 'Не работает снятие',
    'cash_in': 'Не работает пополнение',
    'out_service': 'Устройство не в сервисе',
    'offline': 'Устройство выключено',
    'stuck': 'Устройство зависло'
}

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала для отправки заявки')

@bot.message_handler(content_types=['text'])
def process_request(message):
    atm_id = message.text
    if atm_id in atm_ids:
        send_failure_menu(message.chat.id, atm_id)
    else:
        bot.send_message(message.chat.id, f'Некорректный ID Банкомата/Терминала.')

def send_failure_menu(chat_id, atm_id):
    markup = types.InlineKeyboardMarkup()
    for key, value in failure_types.items():
        markup.add(types.InlineKeyboardButton(value, callback_data=f'{key}:{atm_id}'))
    bot.send_message(chat_id, 'Выберите тип сбоя:', reply_markup=markup)

@bot.callback_query_handler(func=lambda callback: callback.data.startswith(tuple(failure_types.keys())))
def callback_message(callback):
    failure_type, atm_id = callback.data.split(':')

    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')

    # Проверяем, есть ли уже запись для данного банкомата и текущей даты
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (atm_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    # # Проверяем статус последней записи для данного банкомата
    # cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (atm_id,))
    # last_status = cur.fetchone()

    # # if last_status and last_status[0] == "выполнено":
    # #     update_existing_request(atm_id, failure_type)
    # #     bot.send_message(callback.message.chat.id, f'Спасибо, тип сбоя для банкомата ({atm_id}) успешно обновлен.')
    if existing_entries_count > 0:
        bot.send_message(callback.message.chat.id, f'Заявка для банкомата ({atm_id}) с типом сбоя "{failure_types[failure_type]}" уже существует. Инцидент в работе!')
    else:
        save_request_to_db(atm_id, failure_type)
        bot.send_message(callback.message.chat.id, f'Спасибо, ваша заявка для банкомата ({atm_id}) с типом сбоя "{failure_types[failure_type]}" успешно зарегистрирована.')

    conn.commit()
    cur.close()
    

    # Ваш основной файл


# ... (ваш существующий код чат-бота)



# def update_existing_request(atm_id, failure_type):
#     cur = conn.cursor()
#     cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (atm_id,))
#     last_status = cur.fetchone()

#     if last_status and last_status[0] == "выполнено":
#         cur.execute("UPDATE requests SET failure_type = %s WHERE terminal_id = %s AND status = 'выполнено'", (failure_type, atm_id))
#         conn.commit()
#         cur.close()

def save_request_to_db(atm_id, failure_type):
    cur = conn.cursor()
    cur.execute("INSERT INTO requests (terminal_id, timestamp, status, failure_type) VALUES (%s, %s, %s, %s)", (atm_id, datetime.now(), "зарегистрировано", failure_type))
    conn.commit()
    cur.close()



# Запуск бота
bot.polling(none_stop=True)
conn.close()


##отправка в почту смс и начала изменение статуса в чатботе
#! /usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import mysql.connector
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import chardet
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Mail.ru SMTP Configuration
mailru_user = 'amangeldiyev03@inbox.ru'
mailru_password = 'BhUfckkEhhV3HX6vtmk3'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru', 'sultan.amangeldiyev@bcc.kz']

# Параметры для специальной почты
special_email = 'amangeldiyev03@inbox.ru'
special_email_password = 'BhUfckkEhhV3HX6vtmk3'

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = mailru_user
        msg['To'] = ', '.join(recipient_emails)
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.mail.ru', 587)
        server.starttls()
        server.login(mailru_user, mailru_password)
        server.sendmail(mailru_user, recipient_emails, msg.as_string())
        server.quit()

        print("Уведомление отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке уведомления:", e)

user_requests = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')
    if message.chat.id in user_requests and user_requests[message.chat.id]['processed']:
        cur = conn.cursor()
        terminal_id = user_requests[message.chat.id]['id']
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
        conn.commit()
        bot.send_message(message.chat.id, f'Заявка по терминалу {terminal_id} обработана и выполнена!')
        cur.close()

    user_requests[message.chat.id] = {'id': None, 'processed': False}

authorized_user_usernames = ['@asm_003']

def handle_closed_command(update, context):
    user_username = update.message.from_user.username  # Получаем username отправителя
    if user_username in authorized_user_usernames:  # Проверяем, что отправитель является одним из авторизованных пользователей
        args = context.args
        if len(args) != 2:
            update.message.reply_text("Пожалуйста, используйте команду /closed <ID банкомата> <номер заявки>")
            return
        
        terminal_id = args[0]
        request_number = args[1]
        
        cur = conn.cursor()
        cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND request_number = %s", (terminal_id, request_number))
        conn.commit()
        cur.close()
        
        update.message.reply_text(f"Заявка с номером {request_number} для банкомата {terminal_id} успешно закрыта.")
    else:
        update.message.reply_text("У вас нет прав доступа к этой команде.")

BOT_TOKEN = ('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Добавляем обработчик команды /closed
    dispatcher.add_handler(CommandHandler("closed", handle_closed_command))

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

@bot.message_handler(content_types=['text'])
def info(message):
    global mess
    mess = message.text
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    if id is not None:
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        existing_entries_count = cur.fetchone()[0]
        cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (mess,))
        last_status = cur.fetchone()

        if existing_entries_count == 0 or (last_status and last_status[0] == "выполнено"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Заявка по данному терминалу {mess} в работе, но вы можете повторно зафиксировать заявку. Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')
    
    user_requests[message.chat.id] = {'id': mess, 'processed': False}

def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
        conn.commit()

        subject = f'Новая заявка на терминал {terminal_id}'
        body = f'TB001\n{terminal_id} с типом сбоя: {failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
            conn.commit()

            subject = f'Новая заявка на терминал {terminal_id}'
            body = f'TB001\n{terminal_id} с типом сбоя: {failure_type}.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
        else:
            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

    cur.close()


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.send_message(callback.message.chat.id, f'Заявка по данному (ID {mess} Тип: {callback.data}) отправлена!')
        save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)

        user_requests[callback.message.chat.id]['processed'] = False

        if user_requests[callback.message.chat.id].get('done', False):
            cur = conn.cursor()
            today_date = date.today().strftime('%Y-%m-%d')
            cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
            conn.commit()

            subject = f'Заявка на терминал {mess} выполнена'
            body = f'Заявка на терминал {mess} выполнена.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {mess} выполнена.')
            cur.close()

def get_text_from_email(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset() or chardet.detect(part.get_payload(decode=True))['encoding']
                decoded_text = part.get_payload(decode=True).decode(charset)
                text += decoded_text
    else:
        charset = msg.get_content_charset() or chardet.detect(msg.get_payload(decode=True))['encoding']
        decoded_text = msg.get_payload(decode=True).decode(charset)
        text += decoded_text
    return text
    

# Запуск бота
bot.polling(none_stop=True)
conn.close()


#в почту отправляется уведомление но в базе статус не меняется
def process_closed_command(message):
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "Пожалуйста, используйте команду /closed <ID банкомата> <номер заявки>")
        return
    
    terminal_id = args[1]
    request_number = args[2]
    
    cur = conn.cursor()
    cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND request_number = %s", (terminal_id, request_number))
    conn.commit()
    cur.close()
    
    subject = f'Заявка на терминал {terminal_id} выполнена'
    body = f'Заявка на терминал {terminal_id} с номером {request_number} выполнена.'
    send_email(subject, body)
    
    bot.send_message(message.chat.id, f'Заявка с номером {request_number} для банкомата {terminal_id} успешно закрыта и выполнена.')





    ## ограничение по командам
#! /usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import mysql.connector
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import chardet


# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')

# Mail.ru SMTP Configuration
mailru_user = 'bcc_bot@mail.ru'
mailru_password = 'rH5zf4N6q8nT9cR9b6fU'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru', 'itsupport@bcc.kz', 'sultan.amangeldiyev@bcc.kz']

# Параметры для специальной почты
special_email = 'bcc_bot@mail.ru'
special_email_password = 'rH5zf4N6q8nT9cR9b6fU'

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = mailru_user
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = subject  # Устанавливаем тему (Subject) письма
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.mail.ru', 587)
        server.starttls()
        server.login(mailru_user, mailru_password)
        server.sendmail(mailru_user, recipient_emails, msg.as_string())
        server.quit()

        print("Уведомление отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке уведомления:", e)

user_requests = {}
AUTHORIZED_USERNAMES1 = ['asm_003', 'Shalgimb']
@bot.message_handler(commands=['start'])
def start_message(message):
    user_username = message.from_user.username
    
    if user_username in AUTHORIZED_USERNAMES1:
        bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')
        # Остальной код для обработки команды
    else:
        bot.send_message(message.chat.id, "У вас нет прав доступа к этой команде.")

    user_requests[message.chat.id] = {'id': None, 'processed': False}

AUTHORIZED_USERNAMES2 = ['asm_003', 'Shalgimb']  # Здесь нужно указать разрешенные юзернеймы

@bot.message_handler(commands=['closed'])
def process_closed_command(message):
    user_username = message.from_user.username
    
    if user_username not in AUTHORIZED_USERNAMES2:
        bot.send_message(message.chat.id, "У вас нет прав доступа к этой команде.")
        return
    
    user_requests.setdefault(message.chat.id, {})['closed'] = True
    bot.send_message(message.chat.id, "Введите ID банкомата, чтобы удалить заявку")

@bot.message_handler(func=lambda message: user_requests.get(message.chat.id, {}).get('closed', False))
def close_request_step1(message):
    terminal_id = message.text.upper().replace(" ", "")  # Приводим к верхнему регистру и убираем пробелы
    
    cur = conn.cursor()
    cur.execute("DELETE FROM requests WHERE terminal_id = %s AND status = 'в работе'", (terminal_id,))
    conn.commit()
    
    bot.send_message(message.chat.id, f'Заявка по банкомату ID:{terminal_id} успешно удалена из базы данных.')

    # Очищаем данные о закрытии заявки
    user_requests[message.chat.id].pop('closed', None)
    cur.close()

@bot.message_handler(content_types=['text'])
def info(message):
    global mess
    mess = message.text
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    if id is not None:
        today_date = date.today().strftime('%Y-%m-%d')
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
        existing_entries_count = cur.fetchone()[0]
        cur.execute("SELECT status FROM requests WHERE terminal_id = %s ORDER BY timestamp DESC LIMIT 1", (mess,))
        last_status = cur.fetchone()

        if existing_entries_count == 0 or (last_status and last_status[0] == "выполнено"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
            markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
            markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
            markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
            markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

            bot.reply_to(message, f'Заявка по данному терминалу {mess} в работе, но вы можете повторно зафиксировать заявку. Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')
    
    user_requests[message.chat.id] = {'id': mess, 'processed': False}

def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s", (terminal_id, today_date))
    existing_entries_count = cur.fetchone()[0]

    if existing_entries_count == 0:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
        conn.commit()

        subject = f'Новая заявка на терминал {terminal_id}'
        body = f'TB001\n{terminal_id} с типом сбоя: {failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "в работе"))
            conn.commit()

            subject = f'Новая заявка на терминал {terminal_id}'
            body = f'TB001\n{terminal_id} с типом сбоя: {failure_type}.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
        else:
            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

    cur.close()


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.send_message(callback.message.chat.id, f'Заявка по данному (ID {mess} Тип: {callback.data}) отправлена!')
        save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)

        user_requests[callback.message.chat.id]['processed'] = False

        if user_requests[callback.message.chat.id].get('done', False):
            cur = conn.cursor()
            today_date = date.today().strftime('%Y-%m-%d')
            cur.execute("UPDATE requests SET status = 'выполнено' WHERE terminal_id = %s AND DATE(timestamp) = %s", (mess, today_date))
            conn.commit()

            subject = f'Заявка на терминал {mess} выполнена'
            body = f'Заявка на терминал {mess} выполнена.'
            send_email(subject, body)

            bot.send_message(callback.message.chat.id, f'Заявка по терминалу {mess} выполнена.')
            cur.close()

def get_text_from_email(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset() or chardet.detect(part.get_payload(decode=True))['encoding']
                decoded_text = part.get_payload(decode=True).decode(charset)
                text += decoded_text
    else:
        charset = msg.get_content_charset() or chardet.detect(msg.get_payload(decode=True))['encoding']
        decoded_text = msg.get_payload(decode=True).decode(charset)
        text += decoded_text
    return text


# Запуск бота
bot.polling(none_stop=True)
conn.close()

