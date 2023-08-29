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
mailru_user = 'bcc_bot@mail.ru'
mailru_password = 'rH5zf4N6q8nT9cR9b6fU'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru', 'sultan.amangeldiyev@bcc.kz']

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

