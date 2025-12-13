# Инструкция по тестированию 2FA Fix V4

## Цель
Проверить, что исправление V4 решает проблему повторного использования кода при 2FA авторизации.

## Предварительные условия
1. ✅ Backend задеплоен на VPS с исправленным кодом
2. ✅ У вас есть Telegram аккаунт с включённой 2FA (облачный пароль)
3. ✅ SSH доступ к VPS: `ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144`

## Шаг 1: Запустить мониторинг логов

В отдельном терминале:
```bash
cd /e/My/Sattva/telegram
./tests/monitor_2fa_auth.sh
```

Или вручную:
```bash
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "docker logs -f sattva-streamer-backend-1 2>&1 | grep -E '(sign_in|2FA|Password|PhoneCode|check_password)'"
```

## Шаг 2: Открыть frontend

```bash
# Локально (если не задеплоен)
cd frontend
npm run dev

# Или через VPS
open https://sattva-streamer.top
```

## Шаг 3: Начать авторизацию

1. Перейти в раздел "Аккаунты" → "Добавить аккаунт"
2. Ввести номер телефона (с +, например: `+79001234567`)
3. Нажать "Отправить код"

### Ожидаемые логи (1):
```
[send_code] Отправка кода на +79001234567
[send_code] Код отправлен успешно
```

## Шаг 4: Ввести код из Telegram

1. Получить код в Telegram (5 цифр)
2. Ввести код в форму
3. Нажать "Войти"

### Ожидаемые логи (2):
```
[sign_in] Calling sign_in...                     ← Первый вызов с кодом
[sign_in] 2FA required                           ← SessionPasswordNeeded
[sign_in] Extended client TTL for 2FA input (600s)
```

### Ожидаемое UI:
- Появится поле ввода "Облачный пароль (2FA)"
- Код не должен показывать ошибку "Код истёк"

## Шаг 5: Ввести пароль 2FA

1. Ввести ваш облачный пароль Telegram
2. Нажать "Войти"

### Ожидаемые логи (3) - КРИТИЧНО:
```
[sign_in] Reconnected for 2FA! is_connected=True           ← Reconnect успешен
[sign_in] Password provided, skipping sign_in...           ← ✅ НОВОЕ: Пропуск sign_in
[sign_in] 2FA passed! user_id=123456789                    ← ✅ Успех!
```

### ❌ СТАРЫЕ логи (до V4) - НЕ ДОЛЖНО БЫТЬ:
```
[sign_in] Reconnected for 2FA! is_connected=True
[sign_in] Calling sign_in...                     ← ❌ Повторный вызов
[sign_in] PhoneCodeExpired error                 ← ❌ Код истёк
```

## Результаты

### ✅ Тест ПРОШЁЛ, если:
1. После ввода кода появилось поле пароля 2FA
2. Логи показывают: `Password provided, skipping sign_in...`
3. Логи показывают: `2FA passed! user_id=...`
4. UI показывает успешное добавление аккаунта
5. Аккаунт появился в списке

### ❌ Тест ПРОВАЛИЛСЯ, если:
1. Ошибка "Код истёк" при вводе пароля
2. Логи показывают: `Calling sign_in...` после reconnect
3. Логи показывают: `PhoneCodeExpired error`
4. UI показывает ошибку вместо успеха

## Дополнительное тестирование

### Тест 1: Аккаунт БЕЗ 2FA
1. Используйте аккаунт без включённой 2FA
2. После ввода кода должен сразу пройти вход
3. Логи: `[sign_in] Success! user_id=...`

### Тест 2: Неверный пароль 2FA
1. Введите неверный пароль 2FA
2. Должна появиться ошибка "Неверный пароль 2FA"
3. Логи: `[sign_in] ERROR: Invalid 2FA password`

### Тест 3: Истёкший код (реальное истечение)
1. Дождитесь истечения кода (~10 минут)
2. Попробуйте ввести код
3. Должна появиться ошибка "Код истёк"
4. Логи: `[sign_in] PhoneCodeExpired error - код действительно истёк`

## Очистка после тестирования

```bash
# Остановить мониторинг: Ctrl+C

# Проверить добавленные аккаунты
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "docker exec sattva-streamer-backend-1 python -c 'from src.database.models import TelegramAccount; from src.database.session import get_session_sync; print(list(get_session_sync().query(TelegramAccount).all()))'"
```

## Отчёт о результатах

После тестирования заполнить в [TELEGRAM_2FA_CODE_REUSE_FIX_V4.md](../docs/bugfixes/TELEGRAM_2FA_CODE_REUSE_FIX_V4.md):

- [ ] Тест с 2FA аккаунтом прошёл успешно
- [ ] Логи соответствуют ожидаемым
- [ ] UI показывает корректные сообщения
- [ ] Аккаунт добавлен в базу данных

**Дата тестирования:** _________________  
**Тестировщик:** _________________  
**Результат:** ✅ ПРОШЁЛ / ❌ ПРОВАЛИЛСЯ
