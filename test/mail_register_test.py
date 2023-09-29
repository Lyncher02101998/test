import time
import mysql.connector
import imaplib

# Определение констант
IMAP_HOST = 'imap.mail.ru'
IMAP_TIMEOUT = 300
EMAIL_USERNAME = 'bcc_bot@mail.ru'
EMAIL_PASSWORD = 'Zfmsp62L2McNYfSJtZEN'
DB_HOST = 'localhost'
DB_USER = 'user'
DB_PASSWORD = ''
DB_DATABASE = 'teldb'

# Установка таймаута для сокетов
import socket
socket.setdefaulttimeout(300)

while True:
    try:
        # Подключение к почтовому серверу
        mail = imaplib.IMAP4_SSL(host='imap.mail.ru', timeout=300)
        mail.login('bcc_bot@mail.ru', 'Zfmsp62L2McNYfSJtZEN')
        mail.select("Register")

        result, data = mail.search(None, "ALL")
        ids = data[0]
        id_list = ids.split()

        if id_list == []:
            print("Нет данных")
        else:
            latest_email_id = id_list[-1]
            result, data = mail.fetch(latest_email_id, "(RFC822)")
            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')

            index = raw_email_string.find("~")
            index2 = index + 1
            index3 = index2 + 8
            ida = raw_email_string[index2:index3]
            print(ida)

            # Подключение к базе данных
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE)
            cursor = conn.cursor()

            update_query = 'UPDATE requests SET status = "В работе" WHERE terminal_id = %s'
            cursor.execute(update_query, (ida,))
            conn.commit()
            conn.close()

            typ, data = mail.search(None, 'ALL')
            for num in data[-1].split():
                mail.store(num, '-FLAGS', '\Deleted')

            mail.store(latest_email_id, '+FLAGS', '\Deleted')
            mail.expunge()

        time.sleep(5)

    except Exception as e:
        # Обработка ошибок
        print(f"Произошла ошибка: {str(e)}")
        time.sleep(60)  # Подождать 60 секунд перед повторной попыткой
