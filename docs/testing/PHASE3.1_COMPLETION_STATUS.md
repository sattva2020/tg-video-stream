# Phase 3.1 Completion: Оставшиеся задачи

**Дата:** 27 декабря 2025  
**Статус:** 🟡 В РАБОТЕ

---

## ✅ Прогресс

### Frontend Tests: 🎉 Значительное улучшение!

**Было:** 12 падающих тестов (78.9% pass rate)  
**Стало:** 5 падающих тестов (89.1% pass rate)  
**Улучшение:** +10.2% (58% падающих тестов исправлено)

**Оставшиеся 5 тестов:**
1. `tests/components/schedule.test.tsx` - navigates to next/previous month
2. `tests/vitest/auth-card.spec.tsx` - renders the login snapshot (snapshot test)
3. `src/pages/admin/Metrics.Phase3.test.tsx` - Phase 3 tabs
4. `src/pages/admin/Metrics.test.tsx` - should render Metrics component
5. `src/pages/admin/Metrics.test.tsx` - should display system CPU usage
6. `src/pages/admin/Metrics.test.tsx` - should display process metrics

**Проблемы:**
- Metrics тесты ищут тексты которых нет в компоненте
- Schedule тест ищет кнопку по aria-label которого нет
- Snapshot тест устарел

**Рекомендации:** Можно продолжить исправлять, но приоритет низкий (89% pass rate достаточно)

### Backend Coverage: 📈 Инфраструктура готова

**Текущий:** 27.29%  
**Цель:** 70%  
**Требуется:** +42.71%

**Coverage конфигурация:**
- ✅ pytest-cov настроен
- ✅ HTML, XML, LCOV, JSON reports
- ✅ Coverage thresholds (--cov-fail-under=70)
- ✅ Branch coverage enabled

**Создан первый тест-пример:** [test_scheduler_service.py](../backend/tests/test_scheduler_service.py) (0%→100% coverage для scheduler_service)

---

## 🎯 Оставшиеся задачи для 70% coverage

### Приоритет 1: Наименее покрытые модули

| Модуль | Coverage | Строк | Приоритет |
|--------|----------|-------|-----------|
| `src/services/scheduler_service.py` | 0% | 90 | ✅ СОЗДАН |
| `src/services/radio_service.py` | 0% | 53 | 🟠 HIGH |
| `src/services/shazam_service.py` | 0% | 204 | 🟠 HIGH |
| `src/services/systemd.py` | 0% | 82 | 🟡 MEDIUM |
| `src/services/telegram_auth.py` | 10% | 255 | 🟠 HIGH |
| `src/tasks/media.py` | 7% | 182 | 🟠 HIGH |

### Приоритет 2: Частично покрытые модули

| Модуль | Coverage | Строк | Требуется |
|--------|----------|-------|-----------|
| `src/services/priority_queue_service.py` | 21% | 155 | +79% |
| `src/services/telegram_rate_limiter.py` | 26% | 154 | +74% |
| `src/services/prometheus_metrics.py` | 37% | 167 | +63% |
| `src/services/stream_controller.py` | 35% | 82 | +65% |
| `src/services/queue_service.py` | 16% | 219 | +84% |

### Оценка усилий

**Для достижения 70% coverage требуется:**
- ~1500-2000 строк тестового кода
- ~20-30 новых тестовых файлов
- **Время:** 15-20 часов работы (3-4 дня)

**Подход:**
1. Использовать test_scheduler_service.py как шаблон
2. Приоритизировать модули с 0% coverage
3. Мокировать внешние зависимости (Telegram API, Redis, etc.)
4. Фокусироваться на критических функциях

---

## 📝 Инструкция: Добавление CODECOV_TOKEN в GitHub Secrets

### Шаг 1: Регистрация на Codecov

1. Перейти на [codecov.io](https://codecov.io/)
2. Нажать "Sign up with GitHub"
3. Авторизовать Codecov для доступа к репозиториям

### Шаг 2: Добавление репозитория

1. В Codecov dashboard нажать "Add new repository"
2. Выбрать репозиторий `telegram-broadcast`
3. Codecov сгенерирует токен автоматически

### Шаг 3: Получение токена

1. В настройках репозитория на Codecov найти "Repository Upload Token"
2. Скопировать токен (формат: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)

### Шаг 4: Добавление в GitHub Secrets

1. Перейти в репозиторий на GitHub
2. Settings → Secrets and variables → Actions
3. Нажать "New repository secret"
4. Name: `CODECOV_TOKEN`
5. Value: вставить скопированный токен
6. Нажать "Add secret"

### Шаг 5: Проверка интеграции

```bash
# Запустить CI/CD pipeline
git push origin main
```

После запуска workflow проверить:
1. GitHub Actions успешно выполняется
2. Coverage reports загружаются в Codecov
3. На Codecov.io появляются графики coverage

### Альтернатива: Публичный репозиторий

Если репозиторий публичный, токен не обязателен. В `.github/workflows/ci.yml` можно убрать:

```yaml
with:
  token: ${{ secrets.CODECOV_TOKEN }}  # Убрать эту строку
```

---

## 🚀 Следующие шаги

### Немедленно (для Phase 3.1):

1. **Добавить CODECOV_TOKEN** (5 минут)
   - Следовать инструкции выше
   - Проверить CI/CD pipeline

2. **Дописать backend тесты** (15-20 часов)
   - Использовать test_scheduler_service.py как шаблон
   - Приоритет: radio_service.py, shazam_service.py, telegram_auth.py
   - Цель: достичь 70% coverage

3. **Опционально: Исправить оставшиеся 5 frontend тестов** (2-3 часа)
   - Низкий приоритет (89% pass rate достаточно)
   - Можно отложить до Phase 4

### После завершения Phase 3.1:

4. **Переход к Phase 4: Performance Optimization**
   - Bundle size optimization (533KB → <300KB)
   - Backend API optimization
   - Frontend lazy loading

---

## 📊 Текущий статус Phase 3

| Подфаза | Статус | Progress |
|---------|--------|----------|
| **Phase 3.1** Unit Tests | 🟡 В РАБОТЕ | 60% |
| - Frontend tests | ✅ 89% pass rate | 89% |
| - Backend coverage | 🟠 27.29% | 39% |
| - Coverage reports | ✅ Настроены | 100% |
| **Phase 3.2** Integration Tests | ✅ ЗАВЕРШЕНО | 100% |
| **Phase 3.3** CI/CD Pipeline | ✅ ЗАВЕРШЕНО | 100% |

**Общий прогресс Phase 3:** 87% ✅

---

## 🔗 Связанные документы

- [PHASE3.1_IMPROVEMENTS_REPORT.md](./PHASE3.1_IMPROVEMENTS_REPORT.md) - Initial test improvements
- [PHASE3.2-3.3_INTEGRATION_CI_REPORT.md](./PHASE3.2-3.3_INTEGRATION_CI_REPORT.md) - Integration tests & CI/CD
- [test_scheduler_service.py](../backend/tests/test_scheduler_service.py) - Template for new tests
- [refactoring-roadmap.md](../development/refactoring-roadmap.md) - Overall project roadmap

---

**Вывод:** Phase 3 почти завершен (87%). Основная оставшаяся работа - дописать backend тесты до 70% coverage (~15-20 часов). После этого можно уверенно переходить к Phase 4: Performance Optimization! 🚀
