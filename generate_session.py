import os
from pyrogram import Client

API_ID = int(os.getenv("API_ID") or input("API_ID: ").strip())
API_HASH = os.getenv("API_HASH") or input("API_HASH: ").strip()

app = Client("session_gen", api_id=API_ID, api_hash=API_HASH)

async def main():
    await app.start()
    print("\n=== SESSION STRING ===")
    print(await app.export_session_string())
    print("======================\n")
    await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
