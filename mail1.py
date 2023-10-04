import telebot
import types
import mysql.connector
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re
import subprocess
import time



# Параметры для подключения к MySQL

mysql_host = 'localhost'
mysql_user = 'sa'
mysql_password = 'Orapas$123'
mysql_database = 'teldb'

# Соединение с MySQL
try:
    conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
except Exception as e:
        print("Нет подключение к базе !!!")

# Инициализируем бота с помощью токена
bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')
print("Бот запущен!")

# Mail.ru SMTP Configuration

mailru_user = 'bcc_example@mail.ru'
mailru_password = 'q4ibtMju9idi0sXZqv9k'
recipient_emails = ['bcc_example@mail.ru'] #'itsupport@bcc.kz'почта на отправку заявки

# Параметры для специальной почты
special_email = 'bcc_example@mail.ru'
special_email_password = 'q4ibtMju9idi0sXZqv9k'

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

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("Заявка отправлено успешно!")
    except Exception as e:
        print("Ошибка при отправке заявки:", e)

user_requests = {}
registered_requests = set()
user_context = {}

def process_registered_email(msg):
    subject = msg['Subject']
    match = re.search(r'#(\d+)', subject)
    if match:
        request_id = match.group(1)
        registered_requests.add(request_id)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')
    user_context[message.chat.id] = {'id': None, 'processed': False}


@bot.message_handler(content_types=['text'])
def info(message):
    global mess
    mess = message.text
    chat_id = message.chat.id
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()


    if id is not None:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
        keyboard.add(telebot.types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
        keyboard.add(telebot.types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
        keyboard.add(telebot.types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
        keyboard.add(telebot.types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

        bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=keyboard)

    else:
        bot.reply_to(message, f'Не верное ID терминала, попробуйте снова')

    user_requests[message.chat.id] = {'id': mess, 'processed': False}

def save_request_to_db(terminal_id, failure_type, callback):
    cur = conn.cursor()

    # Проверяем, существует ли уже запись с таким же terminal_id и сегодняшней датой
    cur.execute('SELECT COUNT(*) FROM requests WHERE terminal_id = "' + terminal_id + '" ')
    existing_entries_count = cur.fetchone()[0]

    # Удаление заявки из словаря user_requests
    # del user_requests[callback.message.chat.id]

    if existing_entries_count == 0:
        # Если на сегодня нет записей, сохраняем запрос в БД со статусом "в работе"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                    (terminal_id, failure_type, timestamp, "сохранено"))
        conn.commit()

        # Отправляем уведомление на почту о новой заявке
        subject = f'ID:~{terminal_id}'
        body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Заявка на идентификатор терминала {terminal_id} отправлена!')

    else:
        bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!')



# def hide_status_message(chat_id, message_id):
#     bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='Скрыто')


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    chat_id = callback.message.chat.id
    
    if chat_id not in user_context:
        bot.send_message(chat_id, "Пожалуйста, начните снова /start")
        return
    
    if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=callback.message.message_id, reply_markup=None)
        bot.delete_message(chat_id=chat_id, message_id=callback.message.message_id)  # Удалить сообщение "Прошу выбрать тип сбоя для отправки заявки"
        terminal_id = user_context[chat_id]['id']
        
        if terminal_id is not None and not user_context[chat_id]['processed']:
            save_request_to_db(terminal_id=terminal_id, failure_type=callback.data, callback=callback)
            user_context[chat_id]['processed'] = True

        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM requests WHERE terminal_id = "' + mess + '" ')
        existing_entries_count = cur.fetchone()[0]
        cur.close()
    
#     if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:
#         bot.edit_message_reply_markup(chat_id=chat_id, message_id=callback.message.message_id, reply_markup=None)
#         bot.delete_message(chat_id=chat_id, message_id=callback.message.message_id)  # Удалить сообщение "Прошу выбрать тип сбоя для отправки заявки"
#         terminal_id = user_context[chat_id]['id']
        
#         if terminal_id is not None and not user_context[chat_id]['processed']:
#             save_request_to_db(terminal_id=terminal_id, failure_type=callback.data, callback=callback)
#             user_context[chat_id]['processed'] = True

        

        # if existing_entries_count == 0:
        #     # Удаление заявки из словаря user_requests
        #     del bot.reply_to
        #     del user_requests[callback.message.chat.id]

# Запуск бота
bot.polling(none_stop=True)

# Закрыть соединение с базой данных
conn.close()

# while True:
#     try:
#         subprocess.run(['python', 'C:/Users/Администратор/Desktop/Sultan/python1/mail1.py'])
#         time.sleep(5)  # Подождать 1 час перед следующим запуском
#         print("Бот перезапущен")
#     except Exception as e:
#         print(f"Произошла ошибка: {e}")