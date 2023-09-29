# def get_text_from_email(msg):
#     text = ""
#     if msg.is_multipart():
#         for part in msg.walk():
#             if part.get_content_type() == 'text/plain':
#                 charset = part.get_content_charset() or chardet.detect(part.get_payload(decode=True))['encoding']
#                 decoded_text = part.get_payload(decode=True).decode(charset)
#                 text += decoded_text
#     else:
#         charset = msg.get_content_charset() or chardet.detect(msg.get_payload(decode=True))['encoding']
#         decoded_text = msg.get_payload(decode=True).decode(charset)
#         text += decoded_text
#     return text



# def process_received_email(msg):
#     print("Processing received email...")
#     subject = msg['subject']
#     body = get_text_from_email(msg)

#     if "выполнено" in body.lower():
#         terminal_id_match = re.search(r'ID Банкомата/Терминала:\s*(\d+)', body, re.IGNORECASE)
#         if terminal_id_match:
#             terminal_id = terminal_id_match.group(1)
#             print("Found terminal ID:", terminal_id)
#             update_request_status_in_db(terminal_id, 'выполнено')
#             print("Status updated.")

# def email_listener():
#     while True:
#         try:
#             print("Listening for new emails...")
#             mail = imaplib.IMAP4_SSL('imap.mail.ru')
#             mail.login(special_email, special_email_password)
#             mail.select('bccexample')

#             status, response = mail.search(None, 'UNSEEN')

#             if status == 'OK':
#                 for message_num in response[0].split():
#                     print("Processing message:", message_num)
#                     status, msg_data = mail.fetch(message_num, '(RFC822)')
#                     if status == 'OK':
#                         msg = email.message_from_bytes(msg_data[0][1])
#                         process_received_email(msg)
#                         mail.store(message_num, '+FLAGS', '\Seen')
#             mail.logout()
#             time.sleep(10)

#         except Exception as e:
#             print("Error while listening for emails:", e) 


# def update_request_status_in_db(terminal_id, status):
#     cur = conn.cursor()
#     today_date = date.today().strftime('%Y-%m-%d')
#     print("Executing SQL query...")
#     print("UPDATE requests SET status = %s WHERE terminal_id = %s AND DATE(timestamp) = %s", (status, terminal_id, today_date))
#     cur.execute("UPDATE requests SET status = %s WHERE terminal_id = %s AND DATE(timestamp) = %s", (status, terminal_id, today_date))
#     conn.commit()
#     cur.close()

    
# Запуск прослушивания почты в отдельном потоке
# email_thread = threading.Thread(target=email_listener)
# email_thread.daemon = True
# email_thread.start()
