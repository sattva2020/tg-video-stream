# Исправление проблемы с 2FA в Telegram авторизации

## 📋 Проблема

При добавлении Telegram аккаунта с включенной двухфакторной аутентификацией (2FA / Cloud Password):

1. Пользователь вводит номер телефона → получает код
2. Вводит код из Telegram → backend запрашивает 2FA пароль ✅
3. Пользователь вводит 2FA пароль → **ERROR: "Код истёк. Клиент отключился"** ❌

## 🔍 Анализ логов

```
✅ [send_code] is_connected=True - клиент подключен
✅ [sign_in] первая попытка: is_connected=True - всё ещё подключен
✅ [sign_in] 2FA required - Pyrogram вызвал SessionPasswordNeeded
❌ [sign_in] вторая попытка: is_connected=False - клиент отключился!
```

## 🐛 Корневая причина

После того как Pyrogram вызывает исключение `SessionPasswordNeeded`:
- Клиент **отключается** (is_connected=False)
- При следующем вызове `check_password()` клиент уже не подключен
- Предыдущая логика считала это ошибкой и требовала новый код

## ✅ Решение

### 1. Продление TTL клиента в Redis

При возврате `{"status": "2fa_required"}` продлеваем время жизни клиента на **ещё 10 минут**:

```python
# Продлеваем TTL клиента в Redis на ещё 10 минут для ввода 2FA пароля
r = await self._get_redis()
await r.set(f"auth:{phone}:hash", phone_code_hash, ex=600)
await r.close()
```

### 2. Reconnect workaround для 2FA

Если клиент отключился после `SessionPasswordNeeded`, **переподключаем его**:

```python
# WORKAROUND: Pyrogram может отключиться после SessionPasswordNeeded exception
if not client.is_connected:
    print("[sign_in] WARNING: Client disconnected after 2FA request, reconnecting...")
    try:
        await client.connect()
        print(f"[sign_in] Reconnected! is_connected={client.is_connected}")
    except Exception as reconnect_err:
        print(f"[sign_in] ERROR: Failed to reconnect: {reconnect_err}")
        del _pending_clients[phone]
        raise ValueError("Не удалось переподключиться для 2FA. Пожалуйста, запросите новый код.")

user = await client.check_password(password)
```

### 3. Улучшенное логирование

Добавлено логирование состояния подключения в критических точках:

```python
print(f"[sign_in] Before check_password: is_connected={client.is_connected}")
print(f"[sign_in] Reconnected! is_connected={client.is_connected}")
```

## 📁 Изменённые файлы

- [backend/src/services/telegram_auth.py](../../backend/src/services/telegram_auth.py)
  - Метод `sign_in()` - строки 161-181
  - Метод `sign_in_public()` - строки 288-313

## 🧪 Тестирование

### Ожидаемое поведение после исправления:

```
[send_code] is_connected=True ✅
[sign_in] is_connected=True ✅
[sign_in] 2FA required ✅
[sign_in] Extended client TTL (600s) ✅
→ Frontend показывает поле ввода пароля ✅

[sign_in] Before check_password: is_connected=False
[sign_in] WARNING: Client disconnected, reconnecting... ✅
[sign_in] Reconnected! is_connected=True ✅
[sign_in] 2FA passed! user_id=123456789 ✅
```

### Команда для мониторинга:

```bash
chmod +x ../../scripts/monitor-telegram-auth.sh
../../scripts/monitor-telegram-auth.sh
```

## 📝 Технические детали

### Почему reconnect безопасен для 2FA?

В отличие от обычного кода (phone_code_hash), при 2FA:
- Клиент уже **прошёл авторизацию кодом** на сервере Telegram
- Сессия уже **частично аутентифицирована**
- `check_password()` работает с уже установленной сессией
- Reconnect восстанавливает соединение **с той же сессией**

### Почему reconnect НЕ безопасен для обычного кода?

- `phone_code_hash` валиден **только для текущего соединения**
- При reconnect хеш становится невалидным
- Поэтому для обычного кода мы НЕ делаем reconnect

## 🔄 История изменений

| Дата | Изменение |
|------|-----------|
| 2025-12-13 | Добавлен `no_updates=True` для предотвращения отключения |
| 2025-12-13 | Увеличен timeout в Redis: 300s → 600s |
| 2025-12-13 | Удалён reconnect для обычного кода (phone_code_hash) |
| 2025-12-13 | **Добавлен reconnect workaround для 2FA** |
| 2025-12-13 | Добавлено продление TTL при возврате 2fa_required |

## 🚀 Деплой

```bash
# 1. Копируем исправленный файл
scp -i ~/.ssh/id_rsa_n8n backend/src/services/telegram_auth.py \
  root@37.53.91.144:/opt/sattva-streamer/backend/src/services/

# 2. Перезапускаем backend
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 \
  "cd /opt/sattva-streamer && docker compose restart backend"

# 3. Проверяем статус
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 \
  "cd /opt/sattva-streamer && docker compose ps backend"
```

## ✅ Статус

- [x] Проблема идентифицирована
- [x] Решение реализовано
- [x] Код задеплоен на VPS
- [x] Backend перезапущен
- [ ] Тестирование с реальным 2FA аккаунтом

---

**Следующий шаг:** Протестировать добавление аккаунта с включенной 2FA через https://sattva-streamer.top
