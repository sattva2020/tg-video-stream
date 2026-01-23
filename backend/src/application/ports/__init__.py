"""
Application Ports (Interfaces)

Этот пакет содержит интерфейсы (порты) для внешних зависимостей.
Application layer определяет контракты, Infrastructure layer их реализует.

Соблюдается Dependency Inversion Principle:
- Application зависит от абстракций (Protocol)
- Infrastructure зависит от Application (реализует порты)
- Domain не зависит ни от чего (чистая бизнес-логика)
"""

from src.application.ports.i_stream_repository import IStreamRepository
from src.application.ports.i_user_repository import IUserRepository
from src.application.ports.i_poll_repository import IPollRepository
from src.application.ports.i_question_repository import IQuestionRepository

__all__ = [
    "IStreamRepository",
    "IUserRepository",
    "IPollRepository",
    "IQuestionRepository",
]
