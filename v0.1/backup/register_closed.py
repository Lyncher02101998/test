#from msilib.schema import SelfReg
from typing import Self
import mysql.connector
import imaplib
import email
from email.header import decode_header


# Параметры подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'


class ClosedEmailProcessor:
    def __init__(self):
        self.mail = imaplib.IMAP4_SSL('imap.mail.ru')
        self.mail.login('bcc_bot@mail.ru', 'Zfmsp62L2McNYfSJtZEN')
        self.mail.select("Closed")

    def process_emails(self):
        result, data = self.mail.search(None, "ALL")
        ids = data[0]
        id_list = ids.split()
           
        if id_list == []:
         print("Нет данных для обработки.")

        else:
         latest_email_id = id_list[-1]
         result, data = self.mail.fetch(latest_email_id, "(RFC822)")
         raw_email = data[0][1]
         raw_email_string = raw_email.decode('utf-8')

         #Поиск ID устроиства в теле письма
         index = raw_email_string.find("~")  # поиск символа
         index2 = index + 1  # минус первый символ "~"
         index3 = index2 + 8  # получаем конечный индекс
         ida = raw_email_string[index2:index3]  # ищем 8 символов
            
         #Читаем заголовок "Решен"
         msg = email.message_from_bytes(data[0][1])
         sub = decode_header(msg["Subject"])[0][0].decode()
         en = sub [0:5] #ищем 5 символов

         # Создайте соединение с базой данных

        if en == "Решен":
                    
                try:
                 conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
                except Exception as e:
                 print("Нет подключение к базе !!!")
                cursor = conn.cursor()
                    
                print(en)
                print(ida)
                delete_query = 'DELETE from requests where terminal_id = %s'
                cursor.execute(delete_query, (ida,))

                # Сохраните изменения в базе данных
                conn.commit()
                cursor.close()
                conn.close() 

                # Удаление флагов \Deleted
                typ, data = self.mail.search(None, 'ALL')
                for num in data[-1].split():
                    self.mail.store(num, '-FLAGS', '\Deleted')

                # Удаление сообщения
                self.mail.store(latest_email_id, '+FLAGS', '\Deleted')
                self.mail.expunge()

        else:
                    try:
                        conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
                    except Exception as e:
                        print("Нет подключение к базе !!!")
                    cursor = conn.cursor()
                    
                    print(ida)
                    print("В работе")
                    update_query = 'UPDATE requests SET status = "В работе" WHERE terminal_id = %s'
                    cursor.execute(update_query, (ida,))
                    
                    # Сохраните изменения в базе данных
                    conn.commit()
                    cursor.close()
                    conn.close() 

                    # Удаление флагов \Deleted
                    typ, data = self.mail.search(None, 'ALL')
                    for num in data[-1].split():
                        self.mail.store(num, '-FLAGS', '\Deleted')

                    # Удаление сообщения
                    self.mail.store(latest_email_id, '+FLAGS', '\Deleted')
                    self.mail.expunge()