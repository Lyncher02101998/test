import telebot
from telebot import types
import mysql.connector
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import chardet
import imaplib
import email
import re
import threading
import time


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
#'itsupport@bcc.kz',
mailru_user = 'bcc_bot@mail.ru'
mailru_password = 'Zfmsp62L2McNYfSJtZEN'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru', 'sultan.amangeldiyev@bcc.kz']

# Параметры для специальной почты
special_email = 'bcc_bot@mail.ru'
special_email_password = ' '

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
registered_requests = set()

def process_registered_email(msg):
    subject = msg['Subject']
    match = re.search(r'#(\d+)', subject)
    if match:
        request_id = match.group(1)
        registered_requests.add(request_id)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'Здравствуйте {message.from_user.first_name}, введите ID Банкомата/Терминала, для получения статуса или отправки заявки')
    user_requests[message.chat.id] = {'id': None, 'processed': False}

def create_request(chat_id, terminal_id, failure_type):
    cur = conn.cursor()
    today_date = date.today().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "сохранено"))
    conn.commit()
    
    subject = f'ID:~{terminal_id}'
    body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
    send_email(subject, body)
    
    bot.send_message(chat_id, f'Заявка на идентификатор терминала {terminal_id} успешно сохранена на сегодня.')



@bot.message_handler(content_types=['text'])
def info(message):
    global mess
    mess = message.text
    chat_id = message.chat.id
    cur = conn.cursor()

    cur.execute('SELECT ID FROM terminal WHERE ID = "' + message.text + '"')
    id = cur.fetchone()

    if id is not None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
        markup.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
        markup.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
        markup.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
        markup.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

        bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=markup)

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
        cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "сохранено"))
        conn.commit()

        subject = f'ID:~{terminal_id}'
        body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
        send_email(subject, body)

        bot.send_message(callback.message.chat.id, f'Запрос на идентификатор терминала {terminal_id} успешно сохранен на сегодня.')
    else:
        cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
        existing_done_entries_count = cur.fetchone()[0]

        if existing_done_entries_count > 0:
            timestamp = datetime.now().strftime('%Y-%м-%d %H:%M:%S')
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "сохранено"))
            conn.commit()

            subject = f'ID:~{terminal_id}'
            body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
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

imap_server = 'imap.mail.ru'
username = 'bcc_bot@mail.ru'
password = 'Zfmsp62L2McNYfSJtZEN'

# # Подключение к почтовому серверу
# mail = imaplib.IMAP4_SSL(imap_server)
# mail.login(username, password)

# # Выбор папки "Register" для чтения уведомлений о зарегистрированных запросах
# mail.select('Register')

# # Поиск сообщений в выбранной папке
# result, data = mail.search(None, 'ALL')

# if result == 'OK':
#     for num in data[0].split():
#         result, message_data = mail.fetch(num, '(RFC822)')
#         if result == 'OK':
#             raw_email = message_data[0][1]
#             msg = email.message_from_bytes(raw_email)
#             subject = msg['Subject']
#             # Извлеките номер заявки и другую информацию из темы письма и обновите базу данных

# # Повторите аналогичные шаги для папки "Closed" для уведомлений о решенных запросах
# mail.select('Closed')
# result, data = mail.search(None, 'ALL')
# if result == 'OK':
#     for num in data[0].split():
#         result, message_data = mail.fetch(num, '(RFC822)')
#         if result == 'OK':
#             raw_email = message_data[0][1]
#             msg = email.message_from_bytes(raw_email)
#             subject = msg['Subject']
#             # Извлеките номер заявки и обновите базу данных, пометив ее как выполненную

# # Закрыть соединение с почтовым сервером
# mail.logout()

def update_requests_status():
    while True:
        # Подключение к почтовому серверу
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)

        # Выбор папки "Register" для чтения уведомлений о зарегистрированных запросах
        mail.select('Register')

        # Поиск сообщений в выбранной папке
        result, data = mail.search(None, 'ALL')

        if result == 'OK':
            for num in data[0].split():
                result, message_data = mail.fetch(num, '(RFC822)')
                if result == 'OK':
                    raw_email = message_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = msg['Subject']
                    # Извлеките номер заявки из темы письма
                    match = re.search(r'#(\d+)', subject)
                    if match:
                        request_number = match.group(1)
                        # Извлеките ID банкомата из тела письма
                        body = get_text_from_email(msg)
                        match = re.search(r'~(\d{8})', body)
                        if match:
                            terminal_id = match.group(1)
                            cur = conn.cursor()
                            # Проверьте, существует ли запись с соответствующим ID и статусом "сохранено"
                            cur.execute("SELECT * FROM requests WHERE terminal_id = %s AND status = 'сохранено'", (terminal_id,))
                            existing_request = cur.fetchone()
                            if existing_request:
                                # Обновите статус, установите номер заявки и сохраните изменения
                                cur.execute("UPDATE requests SET status = 'зарегистрировано', request_number = %s WHERE ID = %s", (request_number, existing_request[0]))
                                conn.commit()
                                print(f'Обновлена заявка с ID {existing_request[0]}: статус "зарегистрировано", номер заявки {request_number}')
                            else:
                                print(f'Не найдена запись с ID {terminal_id} и статусом "сохранено"')
                            cur.close()
                        else:
                            print('ID банкомата не найден в теле письма')
                    else:
                        print('Номер заявки не найден в теме письма')

        # Закрыть соединение с почтовым сервером
        mail.logout()

        time.sleep(60)  # Проверка почты каждую минуту

# Запустите функцию обновления статуса в отдельном потоке
update_thread = threading.Thread(target=update_requests_status)
update_thread.daemon = True  # Поток будет завершен, когда основной процесс завершится
update_thread.start()

# Запуск бота
bot.polling(none_stop=True)

# Закрыть соединение с базой данных
conn.close()
