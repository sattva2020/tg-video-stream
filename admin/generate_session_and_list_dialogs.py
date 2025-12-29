# generate_session_and_list_dialogs.py
import asyncio
import os
from pyrogram import Client

# Try to get from env, otherwise use placeholders
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

if not API_ID or not API_HASH:
    print("Error: API_ID and API_HASH must be set in environment variables.")
    print("Example: API_ID=12345 API_HASH=abcdef... python generate_session_and_list_dialogs.py")
    exit(1)

async def main():
    print("Будем генерировать StringSession; вам потребуется ввести номер телефона и код из Telegram.")
    # Откроем временный in_memory клиент — Pyrogram сам попросит номер/код при необходимости
    async with Client(name="tmp_session", api_id=API_ID, api_hash=API_HASH, in_memory=True) as app:
        # Экспортируем строку сессии (работает для Pyrogram >=2.x)
        try:
            session_string = await app.export_session_string()
        except Exception as e:
            print("Не удалось экспортировать session string:", e)
            raise

        print("\n--- ВАША SESSION STRING (сохраните где-то безопасно) ---")
        print(session_string)
        print("------------------------------------------------------\n")

        # Список диалогов (последние 50) для выбора chat_id
        print("Получаем список диалогов (последние 50).")
        async for dialog in app.get_dialogs(limit=50):
            chat = dialog.chat
            title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or getattr(chat, 'username', None) or "<no-title>"
            print(f"chat_id={chat.id}\ttype={chat.type}\ttitle='{title}'")

        print("\nСкопируйте нужный числовой chat_id для записи в .env (например: -1001234567890 для канала).")

if __name__ == "__main__":
    asyncio.run(main())