# generate_session_and_list_dialogs.py
import asyncio
from pyrogram import Client

API_ID = 37831214
API_HASH = "1a10843db60c599ce2ec67bc6a55f1c2"

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