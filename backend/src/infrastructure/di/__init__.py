"""
Dependency Injection для проекта.

Этот пакет управляет зависимостями между слоями архитектуры.
"""

from .container import Container, get_container, init_container

__all__ = [
    "Container",
    "get_container",
    "init_container",
]
