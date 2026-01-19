"""
IPasswordHasher Port Interface

Контракт для хеширования и верификации паролей.
"""

from typing import Protocol


class IPasswordHasher(Protocol):
    """
    Интерфейс сервиса хеширования паролей.
    
    Изолирует Application layer от конкретной реализации (bcrypt, argon2, scrypt).
    Позволяет легко менять алгоритм хеширования без изменения Use Cases.
    
    Examples:
        >>> hashed = await hasher.hash("my_password")
        >>> is_valid = await hasher.verify("my_password", hashed)
        >>> assert is_valid is True
    """
    
    async def hash(self, plain_password: str) -> str:
        """
        Хешировать пароль.
        
        Args:
            plain_password: Пароль в открытом виде
            
        Returns:
            Хешированный пароль (строка с солью и метаданными)
            
        Raises:
            HashingError: При ошибке хеширования
        """
        ...
    
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
        ...
