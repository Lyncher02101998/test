import mysql.connector
from datetime import date, datetime
import telebot
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


# Параметры для подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

#'itsupport@bcc.kz',
mailru_user = 'bcc_bot@mail.ru'
mailru_password = 'Zfmsp62L2McNYfSJtZEN'
recipient_emails = ['sultan.amangeldiyev@narxoz.kz', 'kenzhe_03@mail.ru', 'bcc_bot@mail.ru',  'sultan.amangeldiyev@bcc.kz']

bot = telebot.TeleBot('YOUR_TELEGRAM_BOT_TOKEN')

# Соединение с MySQL
conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)




def save_request_to_db(terminal_id, failure_type, callback):
    try:
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
        else:
            cur.execute("SELECT COUNT(*) FROM requests WHERE terminal_id = %s AND DATE(timestamp) = %s AND status = 'выполнено'", (terminal_id, today_date))
            existing_done_entries_count = cur.fetchone()[0]

            if existing_done_entries_count > 0:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "сохранено"))
                conn.commit()

                subject = f'ID:~{terminal_id}'
                body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
                send_email(subject, body)

                bot.send_message(callback.message.chat.id, f'Заявка по терминалу {terminal_id} уже существует. Инцидент в работе!.')

        cur.close()
    except Exception as e:
        print("Ошибка при сохранении заявки в базе данных:", e)


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
