#!/bin/bash
# Генерирует Pyrogram SESSION_STRING через интерактивный режим на сервере
# Использование: ./generate_pyrogram_session.sh <phone_number>

set -e

PHONE="${1:-}"
if [ -z "$PHONE" ]; then
    echo "Usage: $0 <phone_number>"
    echo "Example: $0 +380673229820"
    exit 1
fi

API_ID=37831214
API_HASH="1a10843db60c599ce2ec67bc6a55f1c2"
RELEASE_DIR="/opt/tg_video_streamer/current"

echo "[*] Connecting to remote server..."
ssh -i ~/.ssh/id_rsa_n8n -q root@37.53.91.144 << SSHEOF
cd $RELEASE_DIR
source venv/bin/activate

cat > /tmp/gen_session.py << 'PYEOF'
import asyncio
import sys
from pyrogram import Client

API_ID = $API_ID
API_HASH = "$API_HASH"
PHONE = sys.argv[1] if len(sys.argv) > 1 else "$PHONE"

async def main():
    app = Client("temp_auth", api_id=API_ID, api_hash=API_HASH, in_memory=True, phone_number=PHONE)
    try:
        await app.connect()
        
        # Если не авторизован
        if not await app.is_user_authorized():
            print("[*] Sending code request...")
            sent_code = await app.send_code(PHONE)
            
            print(f"[*] Code sent. Check your Telegram...")
            code = input("[?] Enter confirmation code: ").strip()
            
            print("[*] Signing in...")
            await app.sign_in(PHONE, sent_code.phone_code_hash, code)
        
        # Экспортируем session string
        print("\n[✓] Authorization successful!")
        session_string = await app.export_session_string()
        
        print("\n" + "="*60)
        print("SESSION_STRING (copy this to your .env):")
        print("="*60)
        print(session_string)
        print("="*60 + "\n")
        
        # Получаем информацию пользователя
        me = await app.get_me()
        print(f"[✓] Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})")
        
        await app.disconnect()
        return session_string
    except Exception as e:
        print(f"[✗] Error: {e}", file=sys.stderr)
        await app.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
PYEOF

python3 /tmp/gen_session.py "$PHONE"

deactivate
SSHEOF
