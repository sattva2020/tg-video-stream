# Testing Documentation

**Phase 3: Testing Infrastructure**

## 📚 Документация

### Основные документы

1. **[PHASE3_QUICK_SUMMARY.md](./PHASE3_QUICK_SUMMARY.md)** ⭐
   - Краткий обзор Phase 3
   - Ключевые метрики
   - Быстрый старт

2. **[PHASE3_TESTING_COMPLETE_REPORT.md](./PHASE3_TESTING_COMPLETE_REPORT.md)**
   - Полный отчет о Phase 3
   - Детальные метрики
   - Проблемы и решения
   - Рекомендации

3. **[TESTING_GUIDE.md](./TESTING_GUIDE.md)**
   - Как запускать тесты
   - Команды и примеры
   - Troubleshooting

4. **[TEST_COVERAGE_REPORT.md](./TEST_COVERAGE_REPORT.md)**
   - Шаблон для coverage отчетов
   - Цели покрытия
   - Структура тестов

---

## 🎯 Быстрый старт

### Backend Tests

```bash
cd backend
source ../venv/Scripts/activate

# Все тесты
pytest -v

# С coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Только unit
pytest -m unit

# Только integration
pytest -m integration
```

### Frontend Tests

```bash
cd frontend

# Unit tests
npm run test:unit

# Coverage
npm run test:coverage

# E2E
npm run test:e2e
```

### Docker

```bash
# Все тесты в Docker
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 📊 Текущий статус

### Backend
- **Files**: 30+ test files
- **Tests**: 100+ unit tests, 40+ integration tests
- **Coverage**: ~65% (target: 70%)
- **Status**: ⚠️ Близко к цели, требует доработки

### Frontend
- **Files**: 21 test files (17 passing)
- **Tests**: 203/237 passing (85.6%)
- **Coverage**: ~60% (target: 60%)
- **Status**: ✅ Цель достигнута

### E2E
- **Specs**: 17+ Playwright specifications
- **Tests**: 50+ scenarios
- **Status**: ✅ Полностью работает

---

## 🔧 Инфраструктура

### Тестовое окружение

- ✅ `docker-compose.test.yml` - Изолированная среда с PostgreSQL + Redis
- ✅ GitHub Actions CI/CD - Автоматические тесты при push/PR
- ✅ Coverage reporting - HTML, XML, term-missing
- ✅ Codecov integration - Готово к подключению

### Типы тестов

1. **Unit Tests** - Изолированное тестирование функций/классов
2. **Integration Tests** - Тестирование взаимодействия компонентов
3. **E2E Tests** - End-to-end тестирование пользовательских сценариев
4. **Contract Tests** - Проверка API контрактов

---

## 📁 Структура

```
backend/tests/
├── conftest.py           # Fixtures
├── test_*.py            # Unit tests (30+ файлов)
├── integration/
│   └── test_api_contracts.py
└── api/
    └── ...              # API tests

frontend/tests/
├── unit/                # Unit tests
├── components/          # Component tests
├── hooks/               # Hook tests
├── vitest/              # Vitest specs
├── e2e/                 # Playwright E2E
│   ├── auth.spec.ts
│   ├── streaming-critical.spec.ts
│   └── ...
└── playwright/          # Playwright config
```

---

## 🚨 Известные проблемы

### Backend
1. ⚠️ 2 OAuth теста падают - требуют доработки моков
2. ⚠️ Coverage ~65% - нужно добавить 10-15 тестов

### Frontend
1. ⚠️ 14 тестов падают - проблемы с i18n mocking
2. ⚠️ 20 тестов skipped

**См. [PHASE3_TESTING_COMPLETE_REPORT.md](./PHASE3_TESTING_COMPLETE_REPORT.md)** для детальных решений

---

## 📋 TODO

### Высокий приоритет
- [ ] Исправить 14 падающих frontend тестов
- [ ] Исправить 2 OAuth backend теста
- [ ] Довести backend coverage до 70%

### Средний приоритет
- [ ] Добавить coverage badges
- [ ] Расширить integration tests
- [ ] Performance testing

### Низкий приоритет
- [ ] Security testing (OWASP ZAP)
- [ ] Accessibility testing (axe-core)

---

## 🎓 Ресурсы

### Testing Frameworks
- [pytest](https://docs.pytest.org/) - Backend testing
- [Vitest](https://vitest.dev/) - Frontend unit testing
- [Playwright](https://playwright.dev/) - E2E testing
- [Testing Library](https://testing-library.com/) - React testing

### Best Practices
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Contract Testing](https://martinfowler.com/bliki/ContractTest.html)
- [E2E Testing Best Practices](https://playwright.dev/docs/best-practices)

---

## 🤝 Contributing

При добавлении новых тестов:

1. ✅ Используйте правильные маркеры pytest (`@pytest.mark.unit`, `@pytest.mark.integration`)
2. ✅ Следуйте naming convention: `test_<feature>_<scenario>`
3. ✅ Добавляйте docstrings для сложных тестов
4. ✅ Используйте fixtures из `conftest.py`
5. ✅ Проверяйте coverage после добавления тестов

---

**Last Updated:** 2025-01-27  
**Phase:** 3 - Testing ✅ Complete
