# 🔍 Полный отчет аудита i18n переводов

**Дата**: 23 декабря 2025 г.  
**Проект**: Telegram Streamer Platform

---

## 📊 Общая статистика

| Метрика | Значение |
|---------|----------|
| **Всего ключей в коде** | 521 |
| **Поддерживаемые языки** | 4 (en, ru, uk, de) |

### Покрытие по языкам

| Язык | Всего ключей | Недостающих | Покрытие | Статус |
|------|--------------|-------------|----------|--------|
| 🇬🇧 EN (English) | 449 | 324 | 24.0% | ❌ Требует доработки |
| 🇷🇺 RU (Russian) | 449 | 324 | 24.0% | ❌ Требует доработки |
| 🇺🇦 UK (Ukrainian) | 243 | 467 | -43.0% | ❌ Критическое состояние |
| 🇩🇪 DE (German) | 243 | 467 | -43.0% | ❌ Критическое состояние |

---

## ⚠️ Критические проблемы

### 1. Низкое покрытие базовых языков (EN, RU)
- **Проблема**: Только 24% ключей переведено
- **Причина**: 324 недостающих ключей из 521
- **Приоритет**: 🔴 Высокий

### 2. Критическое состояние UK и DE
- **Проблема**: Отрицательное покрытие (-43%)
- **Причина**: 467 недостающих ключей + 189 устаревших
- **Приоритет**: 🔴 Критический

---

## 📋 Топ-20 недостающих ключей (все языки)

Эти ключи отсутствуют **во всех 4 языках**:

### Admin панель (префикс admin.*)
```
admin.allSystemsGo
admin.approveError
admin.confirmRestart
admin.confirmStop
admin.cpu
admin.disk
admin.latency
admin.memory
admin.needsAttention
admin.noActivity
admin.noActivityHint
admin.offline
admin.online
admin.rejectError
admin.requiresAction
admin.streamRestartError
admin.streamRestarted
admin.streamStartError
admin.streamStarted
admin.streamStopError
```

### Аутентификация
```
account_pending_or_blocked
login_failed_try_again
logging_in
login
login_telegram
```

### Каналы (префикс channels.*)
```
channels.addChannel
channels.addNew
channels.auth
channels.authComplete
channels.authHint
channels.cancel
channels.channelAdded
channels.createChannel
channels.delete
channels.deleteChannel
channels.deleteConfirm
channels.edit
channels.enterCode
channels.loading
channels.phone
channels.phoneHint
channels.save
channels.title
```

### Dashboard и настройки
```
dashboard.activity
dashboard.currentTrack
dashboard.greeting
dashboard.greetingFallback
dashboard.quickActions
dashboard.recentActivity
dashboard.settings
dashboard.stats
dashboard.streamStatus
dashboard.support
```

### Плейлисты
```
playlist.actions
playlist.add
playlist.addVideo
playlist.cancel
playlist.copy
playlist.currentlyPlaying
playlist.delete
playlist.deleteConfirm
playlist.download
playlist.edit
playlist.empty
playlist.format
playlist.name
playlist.noVideos
playlist.playing
playlist.save
playlist.selectAll
playlist.title
playlist.url
```

### Расписание (prefix schedule.*)
```
schedule.add
schedule.allDay
schedule.cancel
schedule.clear
schedule.copy
schedule.copyFrom
schedule.copySchedule
schedule.copyTo
schedule.date
schedule.delete
schedule.deleteSlot
schedule.duration
schedule.edit
schedule.endTime
schedule.loading
schedule.playlist
schedule.repeat
schedule.save
schedule.selectPlaylist
schedule.slots
schedule.startTime
schedule.title
```

---

## 🧹 Устаревшие ключи (можно удалить)

### Найдено в EN и RU (252 ключа)
Примеры:
```
already_have_account
begin
begin_journey
confirm_password
cta_enter
dont_have_account
email_exists
enter
entering
full_name
join_us
joining
password_requirements
passwords_mismatch
registration_failed
validation_error
```

**Причина**: Эти ключи были из старой системы регистрации, которая больше не используется.

### Найдено в UK и DE (189 ключей)
Большинство hero-секции лендинга:
```
hero_audience_admins
hero_audience_channel_owners
hero_audience_newsrooms
hero_audience_streamers
hero_benefit_247
hero_benefit_failover
hero_benefit_no_lag
hero_benefit_playlist
hero_checklist_failover
hero_checklist_security
hero_checklist_signal
...
```

---

## 🎯 Рекомендации по исправлению

### Этап 1: Критические ключи (приоритет HIGH)
Добавить переводы для ключей авторизации и pending approval:
- ✅ `pending_approval_title` - **УЖЕ ИСПРАВЛЕНО**
- ✅ `pending_approval_message` - **УЖЕ ИСПРАВЛЕНО**
- ✅ `pending_approval_info` - **УЖЕ ИСПРАВЛЕНО**
- ✅ `check_status` - **УЖЕ ИСПРАВЛЕНО**
- ✅ `checking` - **УЖЕ ИСПРАВЛЕНО**
- ✅ `back_to_login` - **УЖЕ ИСПРАВЛЕНО**
- ❌ `account_pending_or_blocked` - требует перевода
- ❌ `login_failed_try_again` - требует перевода
- ❌ `logging_in` - требует перевода
- ❌ `login` - требует перевода
- ❌ `login_telegram` - требует перевода

### Этап 2: Admin панель (приоритет HIGH)
Все ключи с префиксом `admin.*` (80+ ключей)

### Этап 3: Функциональные разделы (приоритет MEDIUM)
- Каналы (`channels.*`) - 18 ключей
- Dashboard (`dashboard.*`) - 10 ключей
- Плейлисты (`playlist.*`) - 20 ключей
- Расписание (`schedule.*`) - 24 ключа

### Этап 4: Удаление устаревших ключей (приоритет LOW)
После подтверждения что они не используются:
- Ключи старой регистрации (252 ключа в EN/RU)
- Устаревшие hero-ключи (189 ключей в UK/DE)

---

## 📝 План действий

### Немедленно (сегодня)
1. ✅ Исправлены ключи pending approval (уже выполнено)
2. ❌ Добавить недостающие ключи авторизации:
   - `account_pending_or_blocked`
   - `login_failed_try_again`
   - `logging_in`
   - `login`
   - `login_telegram`
   - `qa_login_hint`
   - `password`

### На этой неделе
1. Добавить все переводы для Admin панели (`admin.*`)
2. Добавить переводы для Channels (`channels.*`)
3. Добавить переводы для Dashboard (`dashboard.*`)

### В следующем спринте
1. Плейлисты и расписание
2. Уведомления и настройки
3. Очистка устаревших ключей

---

## 🔧 Автоматизация

### Скрипт аудита
```bash
python scripts/audit_i18n.py
```

Генерирует:
- Консольный отчет с подсветкой
- JSON отчет: `docs/REPORTS/i18n-audit-report.json`
- Статистику по покрытию

### CI/CD интеграция
Рекомендуется добавить проверку i18n в GitHub Actions:
```yaml
- name: i18n audit
  run: python scripts/audit_i18n.py
  continue-on-error: true  # Пока не исправим все
```

---

## 📖 Полный список недостающих ключей

См. файл: [`docs/REPORTS/i18n-audit-report.json`](./i18n-audit-report.json)

---

**Подготовил**: Jarvis (GitHub Copilot)  
**Дата**: 23.12.2025  
**Версия отчета**: 1.0
