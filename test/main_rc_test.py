import time
from register_closed_test import RegisterEmailProcessor
from register_closed_test import ClosedEmailProcessor

# Создаем экземпляры классов для обработки папок
register_processor = RegisterEmailProcessor()
closed_processor = ClosedEmailProcessor()

# Бесконечный цикл
while True:
    # Обработка писем в папке "Register"
    try:
        register_processor.process_emails()
    # Обработка писем в папке "Closed"    
        closed_processor.process_emails()
    except:
        pass

    time.sleep(5)
