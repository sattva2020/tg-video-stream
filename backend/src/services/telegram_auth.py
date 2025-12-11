import logging
import uuid
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PhoneCodeInvalid, 
    PasswordHashInvalid,
    FloodWait,
    PhoneNumberFlood,
    PhoneCodeExpired,
    PhoneNumberBanned,
    PhonePasswordFlood,
    PeerFlood,
)
from src.core.config import settings
from src.services.encryption import encryption_service
from src.services.telegram_rate_limiter import rate_limiter, LimitType
from src.database import SessionLocal
from src.models.telegram import TelegramAccount
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Все ошибки лимитов для перехвата
LIMIT_ERRORS = (FloodWait, PhoneNumberFlood, PhoneCodeExpired, PhoneNumberBanned, PhonePasswordFlood, PeerFlood)

# In-memory storage for pending auth clients
# Key: phone number, Value: (client, phone_code_hash)
_pending_clients: dict[str, tuple[Client, str]] = {}


class RateLimitError(Exception):
    """Ошибка лимита Telegram API"""
    def __init__(self, limit_info):
        self.limit_info = limit_info
        super().__init__(limit_info.message)


class TelegramAuthService:
    def __init__(self):
        self.api_id = settings.API_ID
        self.api_hash = settings.API_HASH
        self.redis_url = settings.REDIS_URL

    async def _get_redis(self):
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def send_code(self, phone: str):
        print(f"[send_code] Starting for phone: {phone}", flush=True)
        print(f"[send_code] API_ID={self.api_id}, API_HASH={self.api_hash[:8]}...", flush=True)
        
        # Проверяем активные лимиты для этого номера
        existing_limit = await rate_limiter.check_limit(phone)
        if existing_limit and existing_limit.is_active:
            print(f"[send_code] Active limit found: {existing_limit.type.value}, wait={existing_limit.remaining_seconds}s", flush=True)
            raise RateLimitError(existing_limit)
        
        # Cleanup old pending client if exists
        if phone in _pending_clients:
            old_client, _ = _pending_clients.pop(phone)
            try:
                await old_client.disconnect()
                print(f"[send_code] Cleaned up old client for {phone}", flush=True)
            except Exception:
                pass
        
        # Create new client
        session_name = f"auth_{uuid.uuid4()}"
        client = Client(name=session_name, api_id=self.api_id, api_hash=self.api_hash, in_memory=True)
        
        try:
            print("[send_code] Connecting to Telegram...", flush=True)
            await client.connect()
            print("[send_code] Connected! Sending code...", flush=True)
            
            sent_code = await client.send_code(phone)
            phone_code_hash = sent_code.phone_code_hash
            
            # Очищаем предыдущие лимиты при успехе
            await rate_limiter.clear_limit(phone)
            
            print(f"[send_code] Code sent! type={sent_code.type}, hash={phone_code_hash[:10]}...", flush=True)
            
            # Store client in memory (DO NOT export session - it fails before auth)
            _pending_clients[phone] = (client, phone_code_hash)
            print(f"[send_code] Client stored in memory for {phone}", flush=True)
            
            # Also store hash in Redis for timeout tracking
            r = await self._get_redis()
            await r.setex(f"auth:{phone}:hash", 300, phone_code_hash)
            await r.close()
            
            return {"status": "code_sent", "phone_code_hash": phone_code_hash}
        
        except LIMIT_ERRORS as e:
            # Обрабатываем ошибки лимитов
            limit_info = rate_limiter.parse_error(e)
            limit_info.phone = phone
            await rate_limiter.record_limit(phone, limit_info)
            print(f"[send_code] LIMIT ERROR: {limit_info.type.value}, wait={limit_info.wait_seconds}s", flush=True)
            raise RateLimitError(limit_info)
            
        except Exception as e:
            print(f"[send_code] ERROR: {type(e).__name__}: {e}", flush=True)
            # Проверяем, не лимит ли это в текстовом виде
            error_str = str(e).upper()
            if any(keyword in error_str for keyword in ['FLOOD', 'UNAVAILABLE', 'LIMIT', 'WAIT', 'BANNED']):
                limit_info = rate_limiter.parse_error(e)
                limit_info.phone = phone
                await rate_limiter.record_limit(phone, limit_info)
                raise RateLimitError(limit_info)
            try:
                await client.disconnect()
            except Exception:
                pass
            raise e

    async def sign_in(self, user_id: str, phone: str, code: str, password: str = None):
        print(f"[sign_in] Starting for phone: {phone}, code: {code[:2]}***", flush=True)
        
        # Get client from memory
        if phone not in _pending_clients:
            print(f"[sign_in] No pending client for {phone}", flush=True)
            raise ValueError("Session expired. Please request a new code.")
        
        client, phone_code_hash = _pending_clients[phone]
        print(f"[sign_in] Found client, hash={phone_code_hash[:10]}...", flush=True)

        try:
            # Ensure client is connected before sign_in
            if not client.is_connected:
                print("[sign_in] Client disconnected, reconnecting...", flush=True)
                await client.connect()
                print("[sign_in] Reconnected!", flush=True)
            
            try:
                print("[sign_in] Calling sign_in...", flush=True)
                user = await client.sign_in(phone, phone_code_hash, code)
                print(f"[sign_in] Success! user_id={user.id}", flush=True)
            except SessionPasswordNeeded:
                print("[sign_in] 2FA required", flush=True)
                if not password:
                    return {"status": "2fa_required"}
                user = await client.check_password(password)
                print(f"[sign_in] 2FA passed! user_id={user.id}", flush=True)

            # Now we can export session string (user is authenticated)
            print("[sign_in] Exporting session...", flush=True)
            final_session_string = await client.export_session_string()
            print(f"[sign_in] Session exported, len={len(final_session_string)}", flush=True)

            # Encrypt and Save
            encrypted_session = encryption_service.encrypt(final_session_string)

            db = SessionLocal()
            try:
                existing = db.query(TelegramAccount).filter(
                    TelegramAccount.user_id == user_id, 
                    TelegramAccount.phone == phone
                ).first()
                
                if existing:
                    existing.encrypted_session = encrypted_session
                    existing.tg_user_id = user.id
                    existing.first_name = user.first_name
                    existing.username = user.username
                    existing.photo_url = None
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
                print(f"[sign_in] Account saved to DB", flush=True)

            finally:
                db.close()

            # Cleanup
            del _pending_clients[phone]
            r = await self._get_redis()
            await r.delete(f"auth:{phone}:hash")
            await r.close()

            return {"status": "success", "user": {"id": user.id, "username": user.username}}

        except (PhoneCodeInvalid, PasswordHashInvalid) as e:
            print(f"[sign_in] Invalid code/password: {e}", flush=True)
            raise ValueError("Invalid code or password")
        except Exception as e:
            print(f"[sign_in] ERROR: {type(e).__name__}: {e}", flush=True)
            raise e
        finally:
            # Disconnect client
            try:
                await client.disconnect()
            except Exception:
                pass

    async def sign_in_public(self, phone: str, code: str, password: str | None = None):
        """
        Авторизация в Telegram для страницы входа.
        Не сохраняет аккаунт в БД, только возвращает данные пользователя.
        """
        print(f"[sign_in_public] Starting for phone: {phone}, code: {code[:2]}***", flush=True)
        
        # Get client from memory
        if phone not in _pending_clients:
            print(f"[sign_in_public] No pending client for {phone}", flush=True)
            raise ValueError("Сессия истекла. Запросите новый код.")
        
        client, phone_code_hash = _pending_clients[phone]
        print(f"[sign_in_public] Found client, hash={phone_code_hash[:10]}...", flush=True)

        should_disconnect = True  # Flag to control client disconnection
        
        try:
            try:
                print("[sign_in_public] Calling sign_in...", flush=True)
                user = await client.sign_in(phone, phone_code_hash, code)
                print(f"[sign_in_public] Success! user_id={user.id}", flush=True)
            except SessionPasswordNeeded:
                print("[sign_in_public] 2FA required", flush=True)
                if not password:
                    # DON'T disconnect - we need the client for the next request with password
                    should_disconnect = False
                    print("[sign_in_public] Keeping client connected for 2FA", flush=True)
                    return {"status": "2fa_required"}
                # Password provided, try to authenticate
                print("[sign_in_public] Checking 2FA password...", flush=True)
                user = await client.check_password(password)
                print(f"[sign_in_public] 2FA passed! user_id={user.id}", flush=True)

            # Export session string before disconnecting
            session_string = await client.export_session_string()
            print(f"[sign_in_public] Session exported, length={len(session_string)}", flush=True)

            # Cleanup - only on success
            del _pending_clients[phone]
            r = await self._get_redis()
            await r.delete(f"auth:{phone}:hash")
            await r.close()

            return {
                "status": "success",
                "telegram_id": user.id,
                "first_name": user.first_name,
                "username": user.username,
                "phone": phone,
                "session_string": session_string  # For saving TelegramAccount
            }

        except (PhoneCodeInvalid, PasswordHashInvalid) as e:
            print(f"[sign_in_public] Invalid code/password: {e}", flush=True)
            # Cleanup on error
            if phone in _pending_clients:
                del _pending_clients[phone]
            raise ValueError("Неверный код или пароль")
        except Exception as e:
            print(f"[sign_in_public] ERROR: {type(e).__name__}: {e}", flush=True)
            # Cleanup on error
            if phone in _pending_clients:
                del _pending_clients[phone]
            raise e
        finally:
            # Disconnect client only if needed
            if should_disconnect:
                try:
                    await client.disconnect()
                    print("[sign_in_public] Client disconnected", flush=True)
                except Exception:
                    pass

    async def resend_code(self, phone: str):
        """Resend code via alternative method (SMS/call instead of app notification)"""
        print(f"[resend_code] Starting for phone: {phone}", flush=True)
        
        # Get client from memory
        if phone not in _pending_clients:
            print(f"[resend_code] No pending client for {phone}", flush=True)
            raise ValueError("Session expired. Please request a new code first.")
        
        client, phone_code_hash = _pending_clients[phone]
        print(f"[resend_code] Found client, hash={phone_code_hash[:10]}...", flush=True)

        try:
            # Call resend_code to request alternative delivery method
            sent_code = await client.resend_code(phone, phone_code_hash)
            new_hash = sent_code.phone_code_hash
            
            # Get code type for logging
            code_type = type(sent_code.type).__name__
            next_type = type(sent_code.next_type).__name__ if sent_code.next_type else None
            timeout = sent_code.timeout if hasattr(sent_code, 'timeout') else None
            
            print(f"[resend_code] Code resent! type={code_type}, next_type={next_type}, timeout={timeout}", flush=True)
            
            # Update stored hash
            _pending_clients[phone] = (client, new_hash)
            
            # Update Redis
            r = await self._get_redis()
            await r.setex(f"auth:{phone}:hash", 300, new_hash)
            await r.close()
            
            return {
                "status": "code_resent", 
                "phone_code_hash": new_hash,
                "code_type": code_type,
                "next_type": next_type,
                "timeout": timeout
            }
            
        except Exception as e:
            print(f"[resend_code] ERROR: {type(e).__name__}: {e}", flush=True)
            raise e


telegram_auth_service = TelegramAuthService()
