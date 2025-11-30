import logging
import uuid
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PasswordHashInvalid
from src.core.config import settings
from src.services.encryption import encryption_service
from src.database import SessionLocal
from src.models.telegram import TelegramAccount
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class TelegramAuthService:
    def __init__(self):
        self.api_id = settings.API_ID
        self.api_hash = settings.API_HASH
        self.redis_url = settings.REDIS_URL

    async def _get_redis(self):
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def send_code(self, phone: str):
        # Use a random session name to avoid conflicts
        session_name = f"auth_{uuid.uuid4()}"
        client = Client(name=session_name, api_id=self.api_id, api_hash=self.api_hash, in_memory=True)
        await client.connect()
        try:
            sent_code = await client.send_code(phone)
            phone_code_hash = sent_code.phone_code_hash
            
            # Store hash in Redis (expire in 5 mins)
            r = await self._get_redis()
            await r.setex(f"auth:{phone}:hash", 300, phone_code_hash)
            await r.close()
            
            return {"status": "code_sent", "phone_code_hash": phone_code_hash}
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            raise e
        finally:
            await client.disconnect()

    async def sign_in(self, user_id: str, phone: str, code: str, password: str = None):
        # Retrieve hash
        r = await self._get_redis()
        phone_code_hash = await r.get(f"auth:{phone}:hash")
        await r.close()

        if not phone_code_hash:
            raise ValueError("Code expired or invalid flow")

        session_name = f"auth_{uuid.uuid4()}"
        client = Client(name=session_name, api_id=self.api_id, api_hash=self.api_hash, in_memory=True)
        await client.connect()
        
        try:
            try:
                user = await client.sign_in(phone, phone_code_hash, code)
            except SessionPasswordNeeded:
                if not password:
                    return {"status": "2fa_required"}
                user = await client.check_password(password)
            
            session_string = await client.export_session_string()
            
            # Encrypt and Save
            encrypted_session = encryption_service.encrypt(session_string)
            
            db = SessionLocal()
            try:
                # Check if account exists
                existing = db.query(TelegramAccount).filter(TelegramAccount.user_id == user_id, TelegramAccount.phone == phone).first()
                if existing:
                    existing.encrypted_session = encrypted_session
                    existing.tg_user_id = user.id
                    existing.first_name = user.first_name
                    existing.username = user.username
                    existing.photo_url = None # TODO: Fetch photo
                else:
                    new_account = TelegramAccount(
                        user_id=user_id,
                        phone=phone,
                        encrypted_session=encrypted_session,
                        tg_user_id=user.id,
                        first_name=user.first_name,
                        username=user.username
                    )
                    db.add(new_account)
                db.commit()
            finally:
                db.close()
                
            return {"status": "success", "user": {"id": user.id, "username": user.username}}
            
        except (PhoneCodeInvalid, PasswordHashInvalid) as e:
            raise ValueError("Invalid code or password")
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            raise e
        finally:
            await client.disconnect()

telegram_auth_service = TelegramAuthService()
