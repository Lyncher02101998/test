
import telebot
from telebot import types
import mysql.connector
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders



# Параметры для подключения к MySQL
while True:
    try:
        mysql_host = 'localhost'
        mysql_user = 'root'
        mysql_password = ''
        mysql_database = 'teldb'
        
        # Соединение с MySQL
        try:
            conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)
        except Exception as e:
                print("Нет подключение к базе !!!")

        # Инициализируем бота с помощью токена
        bot = telebot.TeleBot('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')
        timenow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("Бот запущен!", timenow)

        # Mail.ru SMTP Configuration

        mailru_user = 'bcc_bot@mail.ru'
        mailru_password = 'Zfmsp62L2McNYfSJtZEN'
        recipient_emails = ['itsupport@bcc.kz'] #'itsupport@bcc.kz'почта на отправку заявки

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

                timetoo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                print("Заявка Service Desk отправлено успешно!", timetoo)
            except Exception as e:
                print("Ошибка при отправке заявки в Service Desk:", e)

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
            # Инициализируем данные пользователя с пустым ID
            user_requests[message.chat.id] = {'id': None, 'processed': False}
    
            # Отправляем сообщение с клавиатурой и просьбой ввести ID
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            item = types.KeyboardButton("Отправить фотографию")
            markup.add(item)
    
            bot.send_message(message.chat.id, f'Здравствуйте, {message.from_user.first_name}! Наберите 8-ми значный ID устройства АТМ\ИПТ, для отправки заявки или получения статуса.', reply_markup=markup)

        def create_request(chat_id, terminal_id, failure_type):
            cur = conn.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)", (terminal_id, failure_type, timestamp, "сохранено"))
            conn.commit()
            
            subject = f'ID:~{terminal_id}'
            body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
            send_email(subject, body)
        
        # Обработчик фотографий
        @bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            chat_id = message.chat.id
            file_id = message.photo[-1].file_id  # Получаем ID файла фотографии
    
            # Получаем информацию о файле
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
    
            # Скачиваем фотографию
            downloaded_file = bot.download_file(file_path)
    
            # Сохраняем фотографию на сервере (по желанию)
            with open("downloaded_photo.jpg", "wb") as photo_file:
                photo_file.write(downloaded_file)
    
            # Отправляем фотографию на почту
            send_photo_to_email("your_email@gmail.com", "your_password", "recipient_email@example.com", downloaded_file)

            bot.send_message(chat_id, "Фотография успешно отправлена на вашу почту!")

        def send_photo_to_email(sender_email, sender_password, recipient_email, photo_data):
            try:
                # Создаем объект MIMEMultipart
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient_email
                msg['Subject'] = "Фотография с бота"  # Тема письма

                # Добавляем текстовое сообщение (необязательно)
                text = "Фотография с бота"
                msg.attach(MIMEText(text, 'plain'))

                # Добавляем фотографию в виде вложения
                image = MIMEImage(photo_data, name="photo.jpg")
                msg.attach(image)

                # Создаем соединение с SMTP-сервером Gmail
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()

                # Входим в аккаунт отправителя
                server.login(sender_email, sender_password)

                # Отправляем письмо
                server.sendmail(sender_email, recipient_email, msg.as_string())

                # Закрываем соединение
                server.quit()

                print("Фотография успешно отправлена на почту!")

            except Exception as e:
                print("Ошибка при отправке фотографии на почту:", e)

        #Проверяем есть ли такой ID 
        @bot.message_handler(content_types=['text'])
        def info(message):
            global mess
            mess = message.text
            cur = conn.cursor()

            cur.execute('SELECT ID FROM terminal WHERE ID = "' + mess + '"')
            id = cur.fetchone()

            if mess == "/help":
                bot.send_message(message.chat.id, f'⚙ Справочник на стадий разработки')
            
            else:
                if id is not None:
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton('Не работает снятие.', callback_data='cash_out'))
                    keyboard.add(types.InlineKeyboardButton('Не работает пополнение.', callback_data='cash_in'))
                    keyboard.add(types.InlineKeyboardButton('Устройство не в сервисе.', callback_data='out_service'))
                    keyboard.add(types.InlineKeyboardButton('Устройство выключено.', callback_data='offline'))
                    keyboard.add(types.InlineKeyboardButton('Устройство зависло.', callback_data='stuck'))

                    bot.reply_to(message, f'Прошу выбрать тип сбоя для отправки заявки', reply_markup=keyboard)

                else:
                    bot.reply_to(message, f'Не верное ID устройство, попробуйте снова❌')

                    mess = None

                user_requests[message.chat.id] = {'id': mess, 'processed': False}

        
        

        # Проверяем, существует ли уже запись с таким же terminal_id
        def save_request_to_db(terminal_id, failure_type, callback):
            cur = conn.cursor()
            
            try:
             cur.execute('SELECT terminal_id FROM requests WHERE terminal_id = "' + terminal_id + '" ')
             existing_entries_count = cur.fetchone()
            except Exception as e:
                print("Нет подключение к базе !!!")

            if mess == None:

                bot.send_message(f'Не верное ID устройство, попробуйте снова❌')
            
            else:               

                if existing_entries_count == None:
                    # Если нет записей, сохраняем запрос в БД со статусом "в работе"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cur.execute("INSERT INTO requests (terminal_id, failure_type, timestamp, status) VALUES (%s, %s, %s, %s)",
                                (terminal_id, failure_type, timestamp, "сохранено"))
                    

                    # Отправляем уведомление на почту о новой заявке
                    subject = f'ID:~{terminal_id}'
                    body = f'TB001\n~{terminal_id}\nТип сбоя:{failure_type}.'
                    send_email(subject, body)

                    bot.send_message(callback.message.chat.id, f'Заявка по данному инциденту ID:{terminal_id} отправлена✅')
                    #print ("Заявка сохранена",timestamp)
                    
                    
                    conn.commit()
                    cur.close()
                    
                else:
                    bot.send_message(callback.message.chat.id, f'Заявка по устройству ID:{terminal_id} уже существует. Инцидент в работе❗')
                    
                    
                    conn.commit() 
                    cur.close()
                


        @bot.callback_query_handler(func=lambda callback: True)
        def callback_message(callback):
            if callback.data in ['cash_out', 'cash_in', 'out_service', 'offline', 'stuck']:

                try:
                 save_request_to_db(terminal_id=mess, failure_type=callback.data, callback=callback)
                except Exception as e:
                 print("Нет глобальнй переменной")
 
        
    
        # Запуск бота
        
        bot.polling(none_stop=True)
        conn.close()
    except:
        pass
   
