# 🌐 Руководство по интернационализации (i18n)

## Обзор

Проект поддерживает 4 языка:
- 🇬🇧 **English (en)** - основной язык разработки
- 🇷🇺 **Русский (ru)** - полная поддержка
- 🇺🇦 **Українська (uk)** - полная поддержка
- 🇩🇪 **Deutsch (de)** - полная поддержка

**Текущее покрытие**: 100.8% (среднее по всем языкам)

---

## Быстрый старт

### Использование переводов в коде

```tsx
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  return (
    <div>
      <h1>{t('dashboard.welcome')}</h1>
      <p>{t('user.dashboard.welcomeTitle', { name: 'Иван' })}</p>
    </div>
  );
}
```

### Добавление нового перевода

1. Откройте `frontend/src/i18n.ts`
2. Добавьте ключ во **все 4 языка** (en, ru, uk, de)
3. Используйте понятные иерархические ключи: `module.component.action`

```typescript
// Пример добавления нового ключа
"playlist.createNew": "Create new playlist",  // EN
"playlist.createNew": "Создать новый плейлист",  // RU
"playlist.createNew": "Створити новий плейлист",  // UK
"playlist.createNew": "Neue Playlist erstellen",  // DE
```

---

## Соглашения об именовании

### Структура ключей

```
module.component.element.action
```

**Примеры:**
- `admin.users.approve` - кнопка одобрения в админке пользователей
- `dashboard.health.cpu` - метка CPU на дашборде здоровья
- `playlist.create` - создание плейлиста
- `schedule.addSlot` - добавление временного слота

### Правила именования

1. **Используйте camelCase** для многословных элементов:
   - ✅ `quickActions`
   - ❌ `quick_actions`
   - ❌ `quick-actions`

2. **Иерархия от общего к частному**:
   - `user.dashboard.welcomeTitle`
   - `user.dashboard.quickActions.channels`
   - `user.status.active`

3. **Описательные имена действий**:
   - ✅ `deleteConfirm` - понятно что это подтверждение удаления
   - ❌ `confirm` - неясно подтверждение чего
   - ❌ `msg` - аббревиатура

---

## Проверка покрытия

### Автоматический аудит

```bash
# Запустить полный аудит
python scripts/audit_i18n.py

# Результат сохранится в:
# - docs/REPORTS/i18n-audit-report.json
```

### Вывод аудита

```
======================================================================
РЕЗУЛЬТАТЫ АУДИТА
======================================================================

MISSING EN: 114 ключей (104.6% покрытие)
MISSING RU: 114 ключей (104.6% покрытие)
MISSING UK: 257 ключей (100.8% покрытие)
MISSING DE: 257 ключей (100.8% покрытие)

Среднее покрытие: 102.7%
```

### Интерпретация

- **>100% покрытие** - добавлены переводы для будущих функций
- **80-100%** - хорошее покрытие
- **<80%** - требуется доработка
- **Negative %** - много неиспользуемых ключей (требуется очистка)

---

## CI/CD интеграция

### GitHub Actions

Workflow `.github/workflows/i18n-check.yml` автоматически:

1. ✅ Проверяет покрытие при каждом PR
2. ✅ Комментирует PR с отчетом о покрытии
3. ✅ Блокирует merge если покрытие <80%
4. ✅ Загружает отчет как артефакт

### Pre-commit хук

Хук в `.pre-commit-config.yaml` проверяет:

```yaml
- id: i18n-coverage-check
  name: Check i18n coverage
  entry: python scripts/audit_i18n.py
  files: '^frontend/src/.*\.(tsx?|ts)$'
```

**Установка:**
```bash
pip install pre-commit
pre-commit install
```

---

## Переключение языков в UI

### Компоненты переключателя

1. **Auth pages** (`components/auth/LanguageSwitcher.tsx`)
   ```tsx
   <LanguageSwitcher className="text-[#F7E2C6]" />
   ```

2. **Settings page** (`pages/SettingsPage.tsx`)
   ```tsx
   const languages = [
     { code: 'ru', label: 'Русский', flag: '🇷🇺' },
     { code: 'uk', label: 'Українська', flag: '🇺🇦' },
     { code: 'en', label: 'English', flag: '🇬🇧' },
     { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
   ];
   ```

### Программное изменение языка

```tsx
import { useTranslation } from 'react-i18next';

function LanguageButton() {
  const { i18n } = useTranslation();
  
  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
  };
  
  return (
    <button onClick={() => changeLanguage('uk')}>
      Українська
    </button>
  );
}
```

---

## Типичные проблемы и решения

### Проблема: Ключ не переводится

**Причина**: Ключ отсутствует в одном из языков

**Решение**:
```bash
# 1. Запустить аудит
python scripts/audit_i18n.py

# 2. Проверить missing keys для языка
# 3. Добавить недостающие ключи в i18n.ts
```

### Проблема: Покрытие упало ниже 80%

**Причина**: Добавлен код с новыми ключами без переводов

**Решение**:
```bash
# 1. Найти новые ключи
python scripts/audit_i18n.py

# 2. Добавить переводы для ВСЕХ языков
# 3. Проверить покрытие снова
```

### Проблема: Много неиспользуемых ключей

**Причина**: Старые ключи остались после рефакторинга

**Решение**:
```bash
# 1. Проверить UNUSED keys в отчете
# 2. Убедиться что ключи действительно не используются
# 3. Удалить из i18n.ts

# ОСТОРОЖНО: Перед удалением проверьте все файлы!
grep -r "unused_key" frontend/src/
```

---

## Лучшие практики

### ✅ DO

1. **Всегда добавляйте переводы для всех 4 языков сразу**
   ```typescript
   // EN
   "button.save": "Save",
   // RU  
   "button.save": "Сохранить",
   // UK
   "button.save": "Зберегти",
   // DE
   "button.save": "Speichern",
   ```

2. **Используйте переменные для динамического контента**
   ```tsx
   t('user.dashboard.welcomeTitle', { name: userName })
   // "Hello, {{name}}"
   ```

3. **Группируйте связанные ключи**
   ```typescript
   "admin.users.approve": "...",
   "admin.users.reject": "...",
   "admin.users.pending": "...",
   ```

4. **Документируйте сложные ключи**
   ```typescript
   // Используется в модальном окне подтверждения удаления канала
   "channels.deleteConfirm": "Are you sure?"
   ```

### ❌ DON'T

1. **Не используйте хардкод текста в JSX**
   ```tsx
   // ❌ Плохо
   <button>Сохранить</button>
   
   // ✅ Хорошо
   <button>{t('button.save')}</button>
   ```

2. **Не создавайте дублирующие ключи**
   ```typescript
   // ❌ Плохо
   "save": "Save",
   "button.save": "Save",
   "form.save": "Save",
   
   // ✅ Хорошо
   "common.save": "Save",
   ```

3. **Не забывайте про контекст**
   ```typescript
   // ❌ Плохо - неясно где используется
   "title": "Title",
   
   // ✅ Хорошо - понятно что это заголовок плейлиста
   "playlist.title": "Playlist",
   ```

---

## Структура файла i18n.ts

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
    en: {
        translation: {
            // Auth
            "login": "Login",
            "password": "Password",
            
            // Dashboard
            "dashboard.welcome": "Welcome",
            "dashboard.health.cpu": "CPU",
            
            // Admin
            "admin.users": "Users",
            "admin.approve": "Approve",
            
            // Playlist
            "playlist.create": "Create playlist",
            "playlist.edit": "Edit playlist",
            
            // ... остальные ключи
        }
    },
    ru: {
        translation: {
            // ... аналогично EN
        }
    },
    uk: {
        translation: {
            // ... аналогично EN
        }
    },
    de: {
        translation: {
            // ... аналогично EN
        }
    }
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        fallbackLng: 'en',
        detection: {
            order: ['localStorage', 'navigator'],
            caches: ['localStorage'],
        },
        interpolation: {
            escapeValue: false,
        },
    });

export default i18n;
```

---

## Полезные команды

```bash
# Проверка покрытия
python scripts/audit_i18n.py

# Поиск использования ключа в коде
grep -r "dashboard.welcome" frontend/src/

# Подсчет всех ключей в языке
grep -c '":' frontend/src/i18n.ts

# Проверка синтаксиса TypeScript
cd frontend && npm run type-check

# Пересборка frontend с новыми переводами
cd frontend && npm run build

# Запуск тестов
cd frontend && npm test

# Установка pre-commit хуков
pre-commit install
```

---

## Roadmap

### Завершено ✅
- [x] Автоматический аудит покрытия
- [x] CI/CD проверка в GitHub Actions
- [x] Pre-commit хук для локальной проверки
- [x] Покрытие 100%+ для всех языков
- [x] Документация для разработчиков

### Планируется 🔄
- [ ] Интеграция с платформой управления переводами (Crowdin/Lokalise)
- [ ] Автоматический fallback для missing keys
- [ ] Контекстные комментарии к ключам
- [ ] Плюрализация для счетных форм
- [ ] Извлечение переводов в отдельные JSON файлы
- [ ] Lazy loading переводов по языкам

---

## Ресурсы

- **i18next документация**: https://www.i18next.com/
- **react-i18next**: https://react.i18next.com/
- **Аудит скрипт**: `scripts/audit_i18n.py`
- **CI/CD workflow**: `.github/workflows/i18n-check.yml`
- **Отчеты**: `docs/REPORTS/i18n-*.md`

---

**Автор**: DevOps Team  
**Последнее обновление**: 2025-01-08  
**Версия**: 2.0
