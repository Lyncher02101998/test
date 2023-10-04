#from msilib.schema import SelfReg
from typing import Self
import mysql.connector
import imaplib
import email
from email.header import decode_header
import time
from datetime import date, datetime


# Параметры подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

i = 1

while True:
   try: 
        timenow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
        print("------------",i,"-------------")
        print(timenow)
        i += 1
        d = mail = imaplib.IMAP4_SSL('imap.mail.ru')
        print(d)
        mail.login('bcc_example@mail.ru', 'q4ibtMju9idi0sXZqv9k')
        mail.select("Closed")


        result, data = mail.search(None, "ALL")
        ids = data[0]
        id_list = ids.split()
            
        while id_list != []:

         latest_email_id = id_list[0]
         result, data = mail.fetch(latest_email_id, "(RFC822)")
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
         sub2 = sub [0:5] #ищем 5 символов

         if sub2 == "Решен":

            try:
                conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
            except Exception as e:
                print("Нет подключение к базе !!!")
            cursor = conn.cursor()
                        
            print(ida)
            print(sub2)
            delete_query = 'DELETE from requests where terminal_id = %s'
            cursor.execute(delete_query, (ida,))

            # Сохраните изменения в базе данных
            conn.commit()
            cursor.close()
            conn.close() 

            # Удаление флагов \Deleted
            typ, data = mail.search(None, 'ALL')
            for num in data[-1].split():
             mail.store(num, '-FLAGS', '\Deleted')

            # Удаление сообщения
            mail.store(latest_email_id, '+FLAGS', '\Deleted')
            mail.expunge()

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
            typ, data = mail.search(None, 'ALL')
            for num in data[-1].split():
                mail.store(num, '-FLAGS', '\Deleted')

            # Удаление сообщения
            mail.store(latest_email_id, '+FLAGS', '\Deleted')
            mail.expunge()
        
        else:
          print("Нет данных для обработки.")   
      
   except:
    pass
   lo = mail.logout
   print(lo)
   time.sleep(180)