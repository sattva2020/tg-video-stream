# Telegram 2FA Code Reuse Fix V4

**Дата**: 2025-01-XX  
**Компонент**: `backend/src/services/telegram_auth.py`  
**Тип**: Критическая ошибка  
**Приоритет**: 🔴 CRITICAL

## Проблема

### Описание
После успешного решения проблемы отключения клиента (V2) и добавления раннего reconnect, появилась новая проблема: **код повторно использовался после переподключения**, что приводило к ошибке `PhoneCodeExpired`.

### Воспроизведение
1. Пользователь запрашивает код Telegram
2. Вводит код — получает ответ `"2fa_required"`
3. Клиент отключается (timeout)
4. Пользователь вводит пароль 2FA
5. Бэкенд успешно переподключается
6. **НО**: Бэкенд снова вызывает `client.sign_in(phone, phone_code_hash, code)` с тем же кодом
7. Telegram API возвращает `PhoneCodeExpired` — код уже был использован в п.2

### Логи ошибки
```
[sign_in] 2FA required                         # Код потреблён здесь
[sign_in] Extended client TTL (600s)
→ Пользователь вводит пароль
[sign_in] Reconnected for 2FA! is_connected=True
[sign_in] Calling sign_in...                   # ❌ Попытка повторного использования
[sign_in] PhoneCodeExpired error               # ❌ Ожидаемый результат
```

## Причина

### Архитектура Telegram API
1. `phone_code_hash` валиден **только для одного вызова** `client.sign_in()`
2. После вызова `sign_in()`, даже если он выбросил `SessionPasswordNeeded`, код считается **потреблённым**
3. **КРИТИЧНО**: Reconnect создаёт **новый auth_key**, но `phone_code_hash` привязан к **старому auth_key**
4. Поэтому после reconnect `check_password()` падает с `AUTH_KEY_UNREGISTERED`
5. **РЕШЕНИЕ**: Клиент **НЕ ДОЛЖЕН отключаться** между вызовами!

### Логика кода (до исправления)
```python
# Reconnect для 2FA - это ПРАВИЛЬНО ✅
if password and not client.is_connected:
    await client.connect()

# НО потом код идёт в try блок и снова вызывает sign_in ❌
try:
    user = await client.sign_in(phone, phone_code_hash, code)  # Код уже использован!
except SessionPasswordNeeded:
    # Этот блок никогда не сработает при втором вызове
    user = await client.check_password(password)
```

## Решение

### Ключевая идея
1. **Использовать `workdir` вместо `in_memory=True`** для корректного сохранения сессии
2. **Запретить отключение клиента** — если клиент отключился, возвращаем ошибку
3. **Разделить пути обработки**: первый вызов (код) и второй вызов (пароль)

### Реализация

#### 1. Использование workdir для сохранения сессии
```python
temp_workdir = tempfile.mkdtemp(prefix="pyrogram_auth_")
client = Client(
    name=session_name, 
    api_id=self.api_id, 
    api_hash=self.api_hash, 
    workdir=temp_workdir,  # Временная директория для сессии
    no_updates=True
)
```

#### 2. Запрет reconnect — клиент ДОЛЖЕН оставаться подключенным
```python
# Если клиент отключился — ошибка, reconnect НЕ работает
if not client.is_connected:
    print(f"[sign_in] ERROR: Client disconnected!")
    print("[sign_in] Reconnect does NOT work - auth_key invalidated")
    raise ValueError("Сессия истекла. Клиент отключился. Пожалуйста, запросите новый код.")
```

#### 3. Условная логика с ранним выходом
```python
# Проверяем, что клиент подключен — если нет, ОШИБКА (reconnect не помогает!)
if not client.is_connected:
    print(f"[sign_in] ERROR: Client disconnected!")
    print("[sign_in] Reconnect does NOT work - auth_key invalidated")
    del _pending_clients[phone]
    raise ValueError("Сессия истекла. Клиент отключился. Пожалуйста, запросите новый код.")

# КРИТИЧНО: Если password предоставлен, код УЖЕ использован - пропускаем sign_in
if password:
    print("[sign_in] Password provided, skipping sign_in, calling check_password directly...")
    try:
        user = await client.check_password(password)
        print(f"[sign_in] 2FA passed! user_id={user.id}")
    except PasswordHashInvalid:
        raise ValueError("Неверный пароль 2FA")
else:
    # Первый вызов - с кодом, без пароля
    try:
        user = await client.sign_in(phone, phone_code_hash, code)
    except PhoneCodeExpired:
        # Cleanup expired client
        del _pending_clients[phone]
        await client.disconnect()
        raise ValueError("Код истёк. Пожалуйста, запросите новый код.")
    except SessionPasswordNeeded:
        print("[sign_in] 2FA required")
        # Продлеваем TTL клиента в Redis на ещё 10 минут для ввода 2FA пароля
        r = await self._get_redis()
        await r.set(f"auth:{phone}:hash", phone_code_hash, ex=600)
        await r.close()
        return {"status": "2fa_required"}

# Cleanup temp workdir after success
if hasattr(client, 'workdir') and client.workdir:
    import shutil
    shutil.rmtree(client.workdir, ignore_errors=True)
```

#### 4. Изменённые файлы
- `backend/src/services/telegram_auth.py`:
  - Добавлены импорты: `tempfile`, `os`, `shutil`
  - Изменено создание клиента: `workdir=tempfile.mkdtemp()` вместо `in_memory=True`
  - Убран reconnect для 2FA — теперь ошибка если клиент отключился
  - Метод `sign_in()` (строки 140-210)
  - Метод `sign_in_public()` (строки 270-330)
  - Очистка временной директории после завершения

### Ключевые изменения
1. **Использование `workdir` для корректного сохранения сессии между вызовами**
2. **Запрет reconnect — если клиент отключился, возвращаем ошибку**
3. **Проверка наличия пароля ДО вызова sign_in()**
4. **Если пароль предоставлен → напрямую вызываем `check_password()`**
5. **Если пароль НЕ предоставлен → нормальный flow с `sign_in()`**
6. **КРИТИЧНО (V6): Флаг `keep_client_connected` для предотвращения отключения при 2FA**
7. **Очистка временной директории только при финальном disconnect**

## Результаты

### Ожидаемое поведение (после исправления V6 - final)
```
[send_code] Created client with temp workdir: /tmp/pyrogram_auth_abc123
[send_code] Code sent! is_connected=True
[sign_in] Calling sign_in...                           # Первый вызов с кодом
[sign_in] 2FA required                                 # SessionPasswordNeeded → код потреблён
[sign_in] Extended client TTL for 2FA input (600s)
[sign_in] Keeping client connected for 2FA password input  # ✅ V6: Флаг установлен
→ Пользователь вводит пароль (клиент ОСТАЁТСЯ подключенным!)
[sign_in] Found client, is_connected=True              # ✅ Клиент всё ещё подключен
[sign_in] Password provided, skipping sign_in...       # ✅ Пропускаем sign_in
[sign_in] 2FA passed! user_id=123456789                # ✅ Успех!
[sign_in] Cleaned up temp workdir: /tmp/pyrogram_auth_abc123
```

### Преимущества
✅ Код используется только один раз (в первом вызове)  
✅ Второй вызов напрямую вызывает `check_password()` без повторного `sign_in()`  
✅ **Клиент остаётся подключенным** — `workdir` сохраняет сессию  
✅ **Запрет reconnect** — если клиент отключился, значит сессия невалидна  
✅ Чёткое разделение логики: код → пароль  
✅ Автоматическая очистка временных файлов

## Связанные исправления
- **V1**: [`TELEGRAM_2FA_FIX.md`](TELEGRAM_2FA_FIX.md) — `no_updates=True`, увеличение TTL
- **V2**: [`TELEGRAM_2FA_RECONNECT_FIX_V2.md`](TELEGRAM_2FA_RECONNECT_FIX_V2.md) — ранний reconnect pattern
- **V3**: [`TELEGRAM_2FA_AUTOCOMPLETE_FIX_V3.md`](TELEGRAM_2FA_AUTOCOMPLETE_FIX_V3.md) — защита от автозаполнения пароля

## Уроки
1. **Telegram API имеет одноразовые токены** — `phone_code_hash` валиден только для одного вызова
2. **Reconnect НЕ восстанавливает токены** — создаётся новый auth_key, но старый hash невалиден
3. **`in_memory=True` не сохраняет сессию правильно** — нужно использовать `workdir`
4. **Клиент ДОЛЖЕН оставаться подключенным** между всеми вызовами — иначе auth_key теряется
5. **Обработка исключений должна учитывать состояние** — `SessionPasswordNeeded` только для первого вызова
6. **Раннее разделение логики** — `if password:` перед `try:` вместо внутри `except:`
7. **Очистка ресурсов** — не забывать удалять временные директории

## Дополнительные ссылки
- Pyrogram документация: https://docs.pyrogram.org/api/methods/sign_in
- Pyrogram документация: https://docs.pyrogram.org/api/methods/check_password
- Telegram API: https://core.telegram.org/api/auth

---

**Статус**: ✅ Исправлено и задеплоено на VPS (V6 - final)
**Дата деплоя**: 13 декабря 2025
**Проверено**: Ожидает тестирования с реальным 2FA аккаунтом

**Важное обновление (V5)**: После обнаружения `AUTH_KEY_UNREGISTERED` при reconnect, изменена стратегия:
- Убран reconnect полностью
- Используется `workdir` вместо `in_memory=True`
- Клиент ДОЛЖЕН оставаться подключенным между вызовами

**Критическое обновление (V6)**: Обнаружено, что клиент отключался в `finally` блоке даже при `2fa_required`:
- Добавлен флаг `keep_client_connected` для предотвращения отключения
- Клиент остаётся подключенным между первым вызовом (код) и вторым (пароль)
- `finally` блок проверяет флаг перед отключением
