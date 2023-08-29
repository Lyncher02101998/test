
from telegram.ext import Updater

BOT_TOKEN = ('6376709843:AAFbZ6GrQqrFWCQZml1A7t-Y-SLwHarFhl0')  # Замените на свой токен

updater = BOT_TOKEN
dispatcher = updater.dispatcher

# Добавьте обработчики команд и сообщений здесь

updater.start_polling()
