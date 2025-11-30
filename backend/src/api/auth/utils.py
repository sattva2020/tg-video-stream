"""
Вспомогательные утилиты для auth модуля.
"""
from fastapi import Request

# Серверная локализация (fallback). В продакшене использовать i18n.
MESSAGE_LOCALIZATIONS = {
    'ru': {
        'auth.email_registered': 'Пользователь с таким email уже существует',
        'auth.google_account_exists': 'Аккаунт уже зарегистрирован через Google — свяжите учётные записи.',
        'auth.account_pending': 'Аккаунт ожидает одобрения администратора',
        'auth.account_rejected': 'Аккаунт отклонён администрацией',
    }
}


def format_auth_error(
    code: str,
    hint: str,
    message: str | None = None,
    message_key: str | None = None,
    req: Request | None = None
) -> dict:
    """
    Формирует payload ошибки для auth endpoints.
    
    Если Accept-Language включает 'ru', возвращает локализованное сообщение.
    Иначе возвращает message_key для клиентской локализации.
    """
    accept = ''
    if req:
        accept = req.headers.get('accept-language', '') or ''
    prefers_ru = 'ru' in accept.lower()

    if prefers_ru:
        # Если есть серверная локализация для ключа — используем её
        if message_key and message_key in MESSAGE_LOCALIZATIONS.get('ru', {}):
            return {'code': code, 'message': MESSAGE_LOCALIZATIONS['ru'][message_key], 'hint': hint}
        if message:
            return {'code': code, 'message': message, 'hint': hint}
        if message_key:
            return {'code': code, 'message': message_key, 'hint': hint}
    
    # Default: возвращаем message_key для клиентской локализации
    if message_key:
        return {'code': code, 'message_key': message_key, 'hint': hint}
    if message:
        return {'code': code, 'message': message, 'hint': hint}
    return {'code': code, 'hint': hint}
