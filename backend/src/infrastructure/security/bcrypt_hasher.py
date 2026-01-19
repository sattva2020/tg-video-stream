"""
Bcrypt реализация хеширования паролей.

Этот модуль реализует IPasswordHasher port используя bcrypt алгоритм.
"""

import bcrypt
from src.application.ports.i_password_hasher import IPasswordHasher
from src.domain.errors import HashingError


class BcryptPasswordHasher:
    """
    Bcrypt реализация IPasswordHasher.
    
    Использует bcrypt с автоматически сгенерированной солью (salt).
    Bcrypt - industry standard для хеширования паролей.
    """
    
    def __init__(self, rounds: int = 12):
        """
        Инициализация hasher.
        
        Args:
            rounds: Количество раундов хеширования (cost factor).
                   По умолчанию 12 (good balance между security и performance).
                   Больше rounds = медленнее но безопаснее.
        """
        self._rounds = rounds
    
    async def hash(self, plain_password: str) -> str:
        """
        Хешировать пароль используя bcrypt.
        
        Args:
            plain_password: Пароль в открытом виде
            
        Returns:
            Хешированный пароль (строка с солью и метаданными)
            
        Raises:
            HashingError: При ошибке хеширования
        """
        try:
            # Генерируем соль и хешируем
            salt = bcrypt.gensalt(rounds=self._rounds)
            hashed_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
            
            # Возвращаем как строку
            return hashed_bytes.decode('utf-8')
            
        except Exception as e:
            raise HashingError(f"Failed to hash password: {e}") from e
    
    async def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверить пароль против хеша.
        
        Args:
            plain_password: Пароль в открытом виде для проверки
            hashed_password: Хешированный пароль из БД
            
        Returns:
            True если пароль совпадает, False иначе
            
        Raises:
            HashingError: При ошибке верификации
        """
        try:
            # bcrypt.checkpw автоматически извлекает соль из хеша
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
            
        except Exception as e:
            raise HashingError(f"Failed to verify password: {e}") from e
