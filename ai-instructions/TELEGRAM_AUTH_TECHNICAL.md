# Telegram Authentication Flow - Technical Reference

## 📋 Обзор

Telegram авторизация в проекте использует **Pyrogram** для создания пользовательских сессий.
Процесс состоит из двух этапов:
1. **send_code** - отправка кода на телефон пользователя
2. **sign_in** - авторизация по коду (и опционально 2FA паролю)

## 🔐 Критические требования

### 1. Клиент должен оставаться подключенным

**ВАЖНО:** `phone_code_hash` валиден **только для текущего соединения**.

```python
# ✅ ПРАВИЛЬНО: Клиент остаётся подключенным
client = Client(..., no_updates=True)  # Предотвращает auto-disconnect
await client.connect()
phone_code_hash = await client.send_code(phone)
# ... клиент остаётся подключенным ...
await client.sign_in(phone, phone_code_hash, code)

# ❌ НЕПРАВИЛЬНО: Reconnect делает phone_code_hash невалидным
await client.connect()
phone_code_hash = await client.send_code(phone)
await client.disconnect()  # ← phone_code_hash становится невалидным!
await client.connect()     # ← reconnect не восстанавливает валидность
await client.sign_in(...)  # ← PHONE_CODE_EXPIRED
```

### 2. Двухфакторная аутентификация (2FA) - особый случай

При 2FA Pyrogram выбрасывает исключение `SessionPasswordNeeded` после `sign_in()`.
**Проблема:** клиент может отключиться после этого исключения.

**Решение:** Reconnect разрешён **только для 2FA**, потому что:
- Клиент уже прошёл авторизацию кодом на сервере Telegram
- Сессия уже частично аутентифицирована
- `check_password()` работает с уже установленной сессией

```python
try:
    user = await client.sign_in(phone, phone_code_hash, code)
except SessionPasswordNeeded:
    # На этом этапе клиент может отключиться
    if not client.is_connected:
        await client.connect()  # ✅ Reconnect безопасен для 2FA!
    user = await client.check_password(password)
```

## 📝 Реализация в проекте

### Файл: backend/src/services/telegram_auth.py

#### Метод send_code()

```python
async def send_code(self, phone: str):
    # 1. Создаём клиента с no_updates=True
    client = Client(
        name=session_name,
        api_id=self.api_id,
        api_hash=self.api_hash,
        in_memory=True,
        no_updates=True  # Предотвращает отключение из-за inactivity
    )
    
    # 2. Подключаемся и отправляем код
    await client.connect()
    sent_code = await client.send_code(phone)
    phone_code_hash = sent_code.phone_code_hash
    
    # 3. Сохраняем клиента в памяти
    _pending_clients[phone] = (client, phone_code_hash)
    
    # 4. Сохраняем hash в Redis с TTL 10 минут
    await redis.set(f"auth:{phone}:hash", phone_code_hash, ex=600)
    
    # ⚠️ НЕ отключаем клиента! Он должен остаться подключенным
```

#### Метод sign_in() - Без 2FA

```python
async def sign_in(self, phone: str, code: str, password: str = None):
    # 1. Получаем сохранённого клиента
    client, phone_code_hash = _pending_clients[phone]
    
    # 2. КРИТИЧНО: Проверяем, что клиент всё ещё подключен
    if not client.is_connected:
        # ❌ НЕ делаем reconnect! phone_code_hash стал невалидным
        del _pending_clients[phone]
        raise ValueError("Код истёк. Клиент отключился.")
    
    # 3. Авторизуемся по коду
    try:
        user = await client.sign_in(phone, phone_code_hash, code)
        # Успех - экспортируем сессию
        session_string = await client.export_session_string()
        return session_string
    except PhoneCodeExpired:
        # Код действительно истёк
        raise ValueError("Код истёк. Запросите новый код.")
```

#### Метод sign_in() - С 2FA

```python
async def sign_in(self, phone: str, code: str, password: str = None):
    client, phone_code_hash = _pending_clients[phone]
    
    try:
        user = await client.sign_in(phone, phone_code_hash, code)
    except SessionPasswordNeeded:
        # Запрошен 2FA пароль
        if not password:
            # Продлеваем TTL для ввода пароля
            await redis.set(f"auth:{phone}:hash", phone_code_hash, ex=600)
            return {"status": "2fa_required"}
        
        # Пароль предоставлен - проверяем подключение
        if not client.is_connected:
            # ✅ Reconnect РАЗРЕШЁН для 2FA!
            await client.connect()
        
        # Проверяем 2FA пароль
        user = await client.check_password(password)
        session_string = await client.export_session_string()
        return session_string
```

## 🔍 Диагностика проблем

### Логи при успешной авторизации (без 2FA):

```
[send_code] Connecting to Telegram...
[send_code] Connected! Sending code...
[send_code] Code sent! type=SentCodeType.APP
[send_code] Client connection status: is_connected=True
[sign_in] Starting for phone: +380...
[sign_in] Found client, is_connected=True
[sign_in] Calling sign_in...
[sign_in] Success! user_id=123456789, is_connected=True
[sign_in] Exporting session...
```

### Логи при успешной авторизации (с 2FA):

```
[send_code] is_connected=True
[sign_in] is_connected=True
[sign_in] 2FA required
[sign_in] Extended client TTL (600s)
→ Frontend показывает поле ввода пароля

[sign_in] Before check_password: is_connected=False
[sign_in] WARNING: Client disconnected, reconnecting...
[sign_in] Reconnected! is_connected=True
[sign_in] 2FA passed! user_id=123456789
```

### Логи при ошибке (Client disconnected):

```
[send_code] is_connected=True
[sign_in] is_connected=False  ← Проблема!
[sign_in] ERROR: Client disconnected! phone_code_hash стал невалидным
ERROR: Код истёк. Клиент отключился.
```

## 🐛 Исправленные проблемы

### Проблема #1: Код истекает сразу после ввода
**Причина:** Клиент отключался между send_code и sign_in  
**Решение:** Добавлен `no_updates=True`, увеличен TTL до 600s

### Проблема #2: 2FA не работает
**Причина:** Клиент отключался после SessionPasswordNeeded  
**Решение:** Добавлен reconnect workaround для 2FA + продление TTL

## 📚 Документация

- [docs/bugfixes/TELEGRAM_2FA_FIX.md](../docs/bugfixes/TELEGRAM_2FA_FIX.md) - подробное описание проблемы
- [docs/bugfixes/TELEGRAM_AUTH_FIX_SUMMARY.md](../docs/bugfixes/TELEGRAM_AUTH_FIX_SUMMARY.md) - сводка всех исправлений

## 🧪 Тестирование

```bash
# Мониторинг логов авторизации
chmod +x scripts/monitor-telegram-auth.sh
./scripts/monitor-telegram-auth.sh

# Автоматический тест
chmod +x scripts/test-telegram-2fa.sh
./scripts/test-telegram-2fa.sh
```

## ⚠️ Важные замечания

1. **НЕ отключайте клиента между send_code и sign_in**
2. **НЕ делайте reconnect для обычного кода** (только для 2FA!)
3. **Используйте no_updates=True** при создании Client
4. **Продлевайте TTL в Redis** при возврате 2fa_required
5. **Логируйте is_connected** в критических точках для диагностики

## 🔄 История изменений

| Дата | Изменение |
|------|-----------|
| 2025-12-13 | Добавлен no_updates=True |
| 2025-12-13 | Увеличен TTL: 300s → 600s |
| 2025-12-13 | Запрещён reconnect для обычного кода |
| 2025-12-13 | Добавлен reconnect workaround для 2FA |
| 2025-12-13 | Добавлено продление TTL при 2fa_required |
