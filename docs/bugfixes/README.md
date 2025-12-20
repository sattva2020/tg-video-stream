# История исправлений багов

Эта директория содержит документацию обо всех критических исправлениях багов в проекте.

## 📋 Список исправлений

### Telegram Authentication (декабрь 2025)

#### [TELEGRAM_2FA_FIX.md](TELEGRAM_2FA_FIX.md)
**Дата:** 13 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Проблема:** Telegram коды истекали сразу после ввода, особенно при включенной двухфакторной аутентификации (2FA)  
**Решение:** 

**Изменённые файлы:**


#### [TELEGRAM_AUTH_FIX_SUMMARY.md](TELEGRAM_AUTH_FIX_SUMMARY.md)
**Дата:** 13 декабря 2025  
**Тип:** Сводка исправлений  
**Описание:** Полная сводка всех исправлений Telegram авторизации, включая:


#### [TELEGRAM_2FA_RECONNECT_FIX_V2.md](TELEGRAM_2FA_RECONNECT_FIX_V2.md)
**Дата:** 13 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Приоритет:** КРИТИЧНЫЙ  
**Проблемы:**
1. Пароль 2FA сохранялся в кеше браузера → Нарушение безопасности
2. Клиент отключался при 2FA, предыдущее исправление не работало

**Решение:**

**Изменённые файлы:**


#### [TELEGRAM_2FA_AUTOCOMPLETE_FIX_V3.md](TELEGRAM_2FA_AUTOCOMPLETE_FIX_V3.md)
**Дата:** 13 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Приоритет:** КРИТИЧНЫЙ - БЕЗОПАСНОСТЬ  
**Проблема:** Пароль 2FA всё ещё сохранялся в кеше браузера, несмотря на `autocomplete="off"`

**Корневая причина:**
- `name="password"` → Браузеры игнорируют autocomplete для таких имён
- Недостаточно только `autocomplete="off"`
- Менеджеры паролей (LastPass, 1Password) игнорируют autocomplete

**Решение - Многоуровневая защита:**
1. Изменено `name="password"` → `name="tg-2fa-verification"` (нейтральное)
2. Изменено `id="password"` → `id="tg-2fa-code"` (нейтральное)
3. Добавлены атрибуты: `autoCapitalize`, `autoCorrect`, `spellCheck`
4. Добавлены data-атрибуты: `data-form-type="other"`, `data-lpignore="true"`
5. Отключено автозаполнение на уровне формы

**Изменённые файлы:**
- `frontend/src/components/auth/TelegramLogin.tsx` (8 атрибутов защиты)

---

#### [TELEGRAM_2FA_CODE_REUSE_FIX_V4.md](TELEGRAM_2FA_CODE_REUSE_FIX_V4.md)
**Дата:** 13 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Приоритет:** КРИТИЧНЫЙ  
**Проблема:** Код повторно использовался после reconnect, вызывая `PhoneCodeExpired`

**Корневая причина:**
- `phone_code_hash` валиден только для одного вызова `sign_in()`
- После первого вызова (даже если выбросил `SessionPasswordNeeded`) код потреблён
- Reconnect восстанавливает соединение, но НЕ валидность кода
- Второй вызов `sign_in()` с тем же кодом → `PhoneCodeExpired`

**Решение - Разделение путей:**
1. **Первый вызов (без пароля)**: `sign_in()` → обработка `SessionPasswordNeeded` → return `2fa_required`
2. **Второй вызов (с паролем)**: **ПРОПУСТИТЬ** `sign_in()` → напрямую вызвать `check_password()`
3. Реализация через условный оператор: `if password:` перед try-блоком

**Изменённые файлы:**
- `backend/src/services/telegram_auth.py` (методы `sign_in()` и `sign_in_public()`)

---

### Database (декабрь 2025)

#### [DATABASE-PASSWORD-MISMATCH-FIX.md](DATABASE-PASSWORD-MISMATCH-FIX.md)
**Дата:** 12 декабря 2025  
**Статус:** ✅ Исправлено  
**Проблема:** Несоответствие паролей БД между конфигурациями  

---

### Playlist Manager (декабрь 2025)

#### [PLAYLIST-MANAGER-CRASH-FIX.md](PLAYLIST-MANAGER-CRASH-FIX.md)
**Дата:** 12 декабря 2025  
**Статус:** ✅ Исправлено  
**Проблема:** Краш менеджера плейлистов  

---

### Frontend (декабрь 2025)

#### [FRONTEND_STREAM_STATUS_CARD_OUTLINE_FIX.md](FRONTEND_STREAM_STATUS_CARD_OUTLINE_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Проблема:** В тёмной теме блок «Статус трансляции» не имел выраженного контура/обводки как у других карточек.  

---

#### [FRONTEND_STREAM_QUALITY_CARD_OUTLINE_FIX.md](FRONTEND_STREAM_QUALITY_CARD_OUTLINE_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Проблема:** В тёмной теме блок «Качество текущего трека» имел менее выраженный контур/обводку по сравнению с другими карточками.  

---

#### [FRONTEND_SCHEDULE_DASHBOARD_STYLE_FIX.md](FRONTEND_SCHEDULE_DASHBOARD_STYLE_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Проблема:** Страница `/schedule` визуально не соответствовала тёмному референсу `/dashboard` (проявлялись «светлые/синие» поверхности).  

---

#### [FRONTEND_SCHEDULE_DARK_THEME_CONTROLS_COLOR_FIX.md](FRONTEND_SCHEDULE_DARK_THEME_CONTROLS_COLOR_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено  
**Проблема:** На `/schedule` в тёмной теме часть элементов управления (стрелки, «Сегодня», `Канал:`/селект, кнопки действий) имели слишком низкий контраст.  

---

#### [FRONTEND_SCHEDULE_DASHBOARD_V2_COLORED_CARDS_PARITY_FIX.md](FRONTEND_SCHEDULE_DASHBOARD_V2_COLORED_CARDS_PARITY_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено  
**Проблема:** `/schedule` визуально не соответствовал Dashboard V2 по «цветной» стилистике карточек (градиентные бейджи/акцент).  

---

#### [FRONTEND_SCHEDULE_PILLS_AND_FLAT_CONTROLS_CONTRAST_FIX.md](FRONTEND_SCHEDULE_PILLS_AND_FLAT_CONTROLS_CONTRAST_FIX.md)
**Дата:** 20 декабря 2025  
**Статус:** ✅ Исправлено и задеплоено  
**Проблема:** На `/schedule` в тёмной теме часть flat-кнопок/стрелок и кнопок в модалках оставалась низкоконтрастной; вкладки не соответствовали «пиллам» Dashboard V2.  

---

## 📊 Статистика

| Компонент | Исправлений | Последнее обновление |
|-----------|-------------|----------------------|
| Telegram Auth | 5 | 13.12.2025 |
| Database | 1 | 12.12.2025 |
| Playlist Manager | 1 | 12.12.2025 |
| Frontend | 8 | 20.12.2025 |
| **Всего** | **15** | **20.12.2025** |

### Критичность исправлений:

| Приоритет | Количество | Компоненты |
|-----------|------------|------------|
| 🔴 КРИТИЧНЫЙ | 3 | Telegram Auth (2FA Security, Reconnect, Code Reuse) |
| 🟡 ВЫСОКИЙ | 2 | Telegram Auth (Code Expiration x2) |
| 🟢 СРЕДНИЙ | 3 | Database, Playlist Manager, Frontend |

## 🔍 Поиск исправления

### По компоненту
- **Telegram** → `TELEGRAM_*.md`
- **Database** → `DATABASE_*.md`
- **Redis** → `REDIS_*.md`
- **API** → `API_*.md`

### По статусу
- ✅ Исправлено и задеплоено
- 🔄 В процессе
- ⏳ Ожидает тестирования

## 📝 Правила добавления новых исправлений

См. [ai-instructions/BUGFIX_DOCUMENTATION_RULES.md](../../ai-instructions/BUGFIX_DOCUMENTATION_RULES.md)

**Краткая памятка:**
1. Файл в формате `COMPONENT_BUG_DESCRIPTION.md`
2. Обязательные разделы: Проблема, Причина, Решение, Тестирование, Статус
3. Относительные ссылки на файлы (`../../`)
4. Обновить этот README.md
5. Обновить ai-instructions/README.md

## 🔗 Связанные документы

- [ai-instructions/TELEGRAM_AUTH_TECHNICAL.md](../../ai-instructions/TELEGRAM_AUTH_TECHNICAL.md) - техническая документация Telegram авторизации
- [README.md](../../README.md) - основной README проекта
