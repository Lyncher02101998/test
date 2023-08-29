import requests
import json
import mysql.connector
import urllib3
from mysql.connector import Error
from datetime import datetime, date

# Инициализация базы данных
mysql_host = 'localhost' 
mysql_user = 'user'
mysql_password = ''
mysql_database = 'teldb'

conn = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_password, database=mysql_database)

# Данные для сервисного деска
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL и параметры для API сервисного деска
service_desk_create_url = "https://service-desk-dev.bank.corp.centercredit.kz/gateway/services/rest/createServiceCall?accessKey=e55ea853-cdd5-42d1-a490-0efe97ae3c34&params=requestContent,user"
service_desk_access_key = ""
service_desk_user_params = "requestContent,user"
service_desk_headers = {
    'Content-Type': 'text/plain',
    'Cookie': 'JSESSIONID=F0F23A7752BC05BEA5A409BD58F803A1'
}

# Типы сбоев
failure_types = {
    'cash_out': 'Не работает снятие',
    'cash_in': 'Не работает пополнение',
    'out_service': 'Устройство не в сервисе',
    'offline': 'Устройство выключено',
    'stuck': 'Устройство зависло'
}

def create_request(atm_id, failure_type):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO requests (terminal_id, timestamp, status, failure_type)
            VALUES (%s, %s, %s, %s)
        """, (atm_id, datetime.now(), 'зарегистрировано', failure_type))
        conn.commit()
        cursor.close()

        # Отправка заявки в сервисный деск
        payload = {
            'slmService': 'service$215629501',
            'route': 'catalogs$35664',
            'descriptionInRTF': failure_types[failure_type],
            'location': 'location$89401',
            'place': 'location$89401',
            'clientEmployee': 'employee$52233',
            'userName': 'employee$52233'
        }   

        response = requests.post(
            service_desk_create_url,
            headers=service_desk_headers,
            data=json.dumps(payload),
            params={'accessKey': service_desk_access_key, 'params': service_desk_user_params},
            verify=False
        )

        if response.status_code == 200:
            return True
        else:
            return False

    except Error as e:
        print(f'Error creating request: {e}')
        return False

def save_request_to_db(atm_id, failure_type):
    cur = conn.cursor()
    cur.execute("INSERT INTO requests (terminal_id, timestamp, status, failure_type) VALUES (%s, %s, %s, %s)", (atm_id, datetime.now(), "зарегистрировано", failure_type))
    conn.commit()
    cur.close()

# Пример  
atm_id = "00000139"
failure_type = "cash_out"
create_request(atm_id, failure_type)

conn.close()
