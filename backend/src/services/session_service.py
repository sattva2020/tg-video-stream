import os
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List

import redis
from fastapi import HTTPException, status

from auth import jwt


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class SessionService:
    def __init__(self):
        url = os.getenv("REDIS_URL")
        self.redis = redis.from_url(url, decode_responses=True) if url else None
        self.refresh_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
        self.access_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
        self.lockout_threshold = int(os.getenv("LOGIN_LOCKOUT_THRESHOLD", 5))
        self.lockout_window_minutes = int(os.getenv("LOGIN_LOCKOUT_WINDOW_MINUTES", 15))

    def _require_redis(self):
        if not self.redis:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis is required for this operation")

    def issue_tokens(self, user) -> TokenPair:
        """Выдаёт access+refresh и сохраняет refresh в Redis для ротации/отзыва."""
        self._require_redis()
        jti = str(uuid.uuid4())
        role_value = user.role.value if hasattr(user.role, "value") else str(user.role) if user.role else None
        access = jwt.create_access_token(
            {"sub": str(user.id), "role": role_value},
            expires_delta=timedelta(minutes=self.access_minutes),
        )
        refresh = jwt.create_refresh_token(
            {"sub": str(user.id), "role": role_value, "jti": jti},
            expires_delta=timedelta(days=self.refresh_days),
        )
        self._store_refresh(user.id, jti)
        return TokenPair(access_token=access, refresh_token=refresh)

    def rotate_refresh(self, token: str) -> TokenPair:
        """Проверяет refresh, удаляет старый jti, выдаёт новую пару."""
        self._require_redis()
        payload = jwt.decode_refresh_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        jti = payload.get("jti")
        sub = payload.get("sub")
        role = payload.get("role")
        if not jti or not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        key = f"auth:refresh:{jti}"
        if not self.redis.get(key):
            # либо устарел, либо отозван
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        # удалить старый jti
        self.redis.delete(key)
        self.redis.srem(f"auth:user-refresh:{sub}", jti)

        # выдать новую пару
        new_jti = str(uuid.uuid4())
        access = jwt.create_access_token(
            {"sub": sub, "role": role},
            expires_delta=timedelta(minutes=self.access_minutes),
        )
        refresh = jwt.create_refresh_token(
            {"sub": sub, "role": role, "jti": new_jti},
            expires_delta=timedelta(days=self.refresh_days),
        )
        self._store_refresh(sub, new_jti)
        return TokenPair(access_token=access, refresh_token=refresh)

    def _store_refresh(self, user_id: Any, jti: str):
        ttl = self.refresh_days * 86400
        user_str = str(user_id)
        key = f"auth:refresh:{jti}"
        user_set = f"auth:user-refresh:{user_str}"
        pipe = self.redis.pipeline()
        pipe.setex(key, ttl, user_str)
        pipe.sadd(user_set, jti)
        pipe.expire(user_set, ttl)
        pipe.execute()

    def revoke_all(self, user_id: Any):
        """Отзывает все refresh токены пользователя (logout from all devices)."""
        self._require_redis()
        user_set = f"auth:user-refresh:{user_id}"
        jtis = self.redis.smembers(user_set) or []
        if jtis:
            pipe = self.redis.pipeline()
            for jti in jtis:
                pipe.delete(f"auth:refresh:{jti}")
            pipe.delete(user_set)
            pipe.execute()

    def list_active_sessions(self, user_id: Any) -> List[Dict[str, Any]]:
        """Возвращает список активных refresh токенов с TTL."""
        self._require_redis()
        user_set = f"auth:user-refresh:{user_id}"
        jtis = self.redis.smembers(user_set) or []
        sessions: List[Dict[str, Any]] = []
        for jti in jtis:
            ttl = self.redis.ttl(f"auth:refresh:{jti}")
            if ttl and ttl > 0:
                sessions.append({"jti": jti, "ttl_sec": ttl})
            else:
                # автоочистка неактуальных ссылок
                self.redis.srem(user_set, jti)
        return sessions

    # --- Login lockout helpers ---
    def is_locked(self, identifier: str) -> bool:
        if not self.redis:
            return False
        return self.redis.exists(self._lock_key(identifier)) == 1

    def register_failure(self, identifier: str):
        if not self.redis:
            return
        fail_key = self._fail_key(identifier)
        lock_key = self._lock_key(identifier)
        count = self.redis.incr(fail_key)
        self.redis.expire(fail_key, self.lockout_window_minutes * 60)
        if count >= self.lockout_threshold:
            self.redis.setex(lock_key, self.lockout_window_minutes * 60, "1")

    def clear_failures(self, identifier: str):
        if not self.redis:
            return
        self.redis.delete(self._fail_key(identifier))
        self.redis.delete(self._lock_key(identifier))

    @staticmethod
    def _fail_key(identifier: str) -> str:
        return f"auth:fail:{identifier.lower()}"

    @staticmethod
    def _lock_key(identifier: str) -> str:
        return f"auth:lock:{identifier.lower()}"


session_service = SessionService()
