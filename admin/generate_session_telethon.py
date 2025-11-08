from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env файла
load_dotenv()

API_ID = int(os.getenv('API_ID', '37831214'))
API_HASH = os.getenv('API_HASH', '1a10843db60c599ce2ec67bc6a55f1c2')

def main():
    phone = input('Enter phone (e.g. +380673229820): ').strip()
    # Используем временную сессию, которая будет экспортирована
    session = StringSession()
    client = TelegramClient(session, API_ID, API_HASH)
    client.connect()
    try:
        if not client.is_user_authorized():
            print('Requesting code (force_sms=True) ...')
            client.send_code_request(phone, force_sms=True)
            code = input('Enter the confirmation code you received: ').strip()
            try:
                client.sign_in(phone=phone, code=code)
            except SessionPasswordNeededError:
                pwd = input('Two-step password required. Enter password: ').strip()
                client.sign_in(password=pwd)

        print('\n--- ВАША SESSION STRING (сохраните в безопасном месте) ---')
        print(client.session.save())
        print('------------------------------------------------------\n')

        print('Последние диалоги (id, title):')
        for dialog in client.iter_dialogs(limit=50):
            chat = dialog.entity
            title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or getattr(chat, 'username', None) or '<no-title>'
            print(f"chat_id={chat.id}\ttitle='{title}'")

    finally:
        client.disconnect()

if __name__ == '__main__':
    main()
