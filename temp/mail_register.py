# Импорт библиотеки pyTelegramBotAPI
import time
import mysql.connector
import imaplib
import socket
socket.setdefaulttimeout(60)

# try:
#     mail = imaplib.IMAP4_SSL(host='imap.mail.ru', timeout=300) #timeout=300
#     print(mail)
# except Exception as e:
#         print("Ошибка:", e) 
# mail.login('bcc_bot@mail.ru', 'Zfmsp62L2McNYfSJtZEN')
# mail.list()
# mail.select("Register")

#------------------------------------------------------------------------

while True:

    try:
        mail = imaplib.IMAP4_SSL(host='imap.mail.ru', timeout=60) #timeout=300
        print(mail)
        
        
        mail.login('bcc_bot@mail.ru', 'Zfmsp62L2McNYfSJtZEN')
        mail.list()
        mail.select("Register")

        result, data = mail.search(None, "ALL")
            
        ids = data[0]
        id_list = ids.split()

        none_list = []



        if id_list == []:
            print("Нет данных")
        else:
            latest_email_id = id_list[-1]
            result, data = mail.fetch(latest_email_id, "(RFC822)")
            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')



            index = raw_email_string.find("~") #пойск символа 

            index2 = index+1 #минус первый символ "~"
            index3 = index2+8 #получаем конечный индекс

            ida = raw_email_string [index2:index3] #ищем 8 символов

            print(ida)
                
                
            #Обновление в базе на статус "В работе"
            #------------------------------ 
            # Параметры подключения к MySQL
            mysql_host = 'localhost'
            mysql_user = 'user'
            mysql_password = ''
            mysql_database = 'teldb'

            # Создайте соединение с базой данных
            conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
            cursor = conn.cursor()

            update_query = 'UPDATE requests SET status = "В работе" WHERE terminal_id = %s'
            cursor.execute(update_query, (ida,))

            # Сохраните изменения в базе данных
            conn.commit()


            #Удаление флагов \Deleted
            typ, data = mail.search(None, 'ALL')
            for num in data[-1].split():
                mail.store(num, '-FLAGS', '\Deleted')


            #Удаление сообщение
            mail.store(latest_email_id, '+FLAGS', '\Deleted')
            mail.expunge()

            
    except:
       pass 
    time.sleep(5)