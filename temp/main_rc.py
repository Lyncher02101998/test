import time
from register_closed import ClosedEmailProcessor

# Создаем экземпляры классов для обработки папок
closed_processor = ClosedEmailProcessor()
i = 0
# Бесконечный цикл
while True:
    try:    
    #Обработка писем в папке "Closed"   
        print("------------",i,"-------------")
        time.sleep(5)
        i += 1
        closed_processor.process_emails()
        
    except:
        pass
