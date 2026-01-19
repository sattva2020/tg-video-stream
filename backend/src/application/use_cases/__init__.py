"""
Application Layer Use Cases

Use Cases — это orchestrators, которые координируют:
- Domain entities (бизнес-логика)
- Port interfaces (абстракции Infrastructure)
- DTOs (boundary objects)

Dependency Rule: Use Cases зависят только от Domain + Ports (не от Infrastructure/Frameworks).
"""

from .auth import AuthenticateUserUseCase, RegisterUserUseCase
from .streaming import CreateStreamUseCase, StartBroadcastUseCase, StopBroadcastUseCase

__all__ = [
    # Auth Use Cases
    "AuthenticateUserUseCase",
    "RegisterUserUseCase",
    # Streaming Use Cases
    "CreateStreamUseCase",
    "StartBroadcastUseCase",
    "StopBroadcastUseCase",
]
