"""
Application Ports (Interfaces)

Этот пакет содержит интерфейсы (порты) для внешних зависимостей.
Application layer определяет контракты, Infrastructure layer их реализует.

Соблюдается Dependency Inversion Principle:
- Application зависит от абстракций (Protocol)
- Infrastructure зависит от Application (реализует порты)
- Domain не зависит ни от чего (чистая бизнес-логика)
"""
