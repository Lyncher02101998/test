import imaplib
import mysql.connector
import time

# Параметры подключения к MySQL
mysql_host = 'localhost'
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

class EmailProcessor:
    def __init__(self, mailbox):
        self.mailbox = mailbox
        self.mail = imaplib.IMAP4_SSL('imap.mail.ru')
        self.mail.login('bcc_bot@mail.ru', 'Zfmsp62L2McNYfSJtZEN')
        self.mail.select(mailbox)

    def process_emails(self):
        result, data = self.mail.search(None, "ALL")
        ids = data[0]
        id_list = ids.split()

        if id_list == []:
            print(f"Нет данных {self.mailbox}")
        else:
            latest_email_id = id_list[-1]
            result, data = self.mail.fetch(latest_email_id, "(RFC822)")
            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')

            index = raw_email_string.find("~")
            index2 = index + 1
            index3 = index2 + 8
            ida = raw_email_string[index2:index3]
            print(ida)

            try:
                conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
            except Exception as e:
                print("Нет подключение к базе !!!")
                return

            cursor = conn.cursor()

            if self.mailbox == "Register":
                update_query = 'UPDATE requests SET status = "В работе" WHERE terminal_id = %s'
                cursor.execute(update_query, (ida,))
            elif self.mailbox == "Closed":
                delete_query = 'DELETE from requests where terminal_id = %s'
                cursor.execute(delete_query, (ida,))

            conn.commit()
            cursor.close()
            conn.close()

            typ, data = self.mail.search(None, 'ALL')
            for num in data[-1].split():
                self.mail.store(num, '-FLAGS', '\Deleted')

            self.mail.store(latest_email_id, '+FLAGS', '\Deleted')
            self.mail.expunge()

if __name__ == "__main__":
    while True:
        register_processor = EmailProcessor("Register")
        register_processor.process_emails()

        closed_processor = EmailProcessor("Closed")
        closed_processor.process_emails()

        # Подождите, прежде чем проверить почту снова, чтобы не нагружать сервер
        time.sleep(10) 
