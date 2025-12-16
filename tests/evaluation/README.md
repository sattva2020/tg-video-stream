# Audio API Evaluation Framework

Полная система evaluation для audio processing API с использованием Azure AI Evaluation SDK.

## Структура

```
tests/evaluation/
├── audio_test_queries.json          # Тестовые запросы (10 сценариев)
├── audio_test_responses.json        # Собранные ответы от VPS
├── audio_evaluation_dataset.jsonl   # JSONL dataset для Azure AI SDK
├── collect_responses.py             # Скрипт сбора ответов от API
├── get_test_token.py                # Получение JWT токена для тестов
├── prepare_dataset.py               # Преобразование в JSONL формат
├── run_evaluation.py                # Основной evaluation runner
├── requirements.txt                 # Зависимости (azure-ai-evaluation)
├── .env.test                        # Конфигурация тестов (не коммитить!)
└── evaluation_results              # Результаты evaluation (JSON)
```

## Метрики Evaluation

### 1. Audio Processing Quality (3.80/5.0)
**Тип:** Custom Code-based Evaluator

**Оценивает:**
- Корректность применения speed настроек (0.5x - 2.0x)
- Применение equalizer (preset или custom)
- Применение pitch correction
- Применение volume adjustment
- Наличие session_id в ответе
- HTTP статус код

**Результаты:**
- Средний балл: 3.80/5.0 (76%)
- Все запросы успешно обработаны
- Session ID сгенерирован для всех транскодингов

### 2. API Response Time (5.00/5.0)
**Тип:** Custom Code-based Evaluator

**Оценивает:**
- HTTP статус код (200 OK = отлично)
- Время отклика endpoints
- Соответствие ожидаемым лимитам времени

**Результаты:**
- Средний балл: 5.00/5.0 (100%)
- Все endpoints вернули HTTP 200
- Производительность соответствует стандартам

### 3. User Settings Integration (4.75/5.0)
**Тип:** Custom Code-based Evaluator

**Оценивает:**
- Корректность сохранения настроек (PUT /settings)
- Корректность получения настроек (GET /settings)
- Применение настроек в transcode запросах
- Наличие всех обязательных полей

**Результаты:**
- Средний балл: 4.75/5.0 (95%)
- Settings CRUD операции работают корректно
- Настройки успешно применяются в транскодинге

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Получение JWT токена

```bash
# Отредактировать .env.test с правильным BACKEND_BASE_URL
python get_test_token.py
```

### 3. Сбор ответов от API

```bash
python collect_responses.py
```

### 4. Подготовка dataset

```bash
python prepare_dataset.py
```

### 5. Запуск evaluation

```bash
python run_evaluation.py
```

## Результаты

После выполнения evaluation результаты сохраняются в `evaluation_results` (JSON файл):

```json
{
  "metrics": {
    "audio_quality.audio_processing_quality_score": 3.80,
    "api_performance.api_response_time_score": 5.00,
    "settings_integration.user_settings_integration_score": 4.75
  },
  "rows": [
    {
      "inputs": {...},
      "outputs": {
        "audio_quality": {...},
        "api_performance": {...},
        "settings_integration": {...}
      }
    }
  ]
}
```

## Тестовые сценарии

1. **transcode_01** - Speed adjustment (1.5x)
2. **transcode_02** - Equalizer preset (bass_boost)
3. **transcode_03** - Custom equalizer (3 bands)
4. **transcode_04** - Volume + Speed (0.5 volume, 2.0x speed)
5. **settings_get_01** - GET user settings
6. **settings_update_01** - Update speed setting
7. **settings_update_02** - Update equalizer preset
8. **settings_update_03** - Enable pitch correction
9. **health_check_01** - Check rust-transcoder health
10. **stream_01** - Stream processed audio

## Конфигурация

`.env.test`:
```env
BACKEND_BASE_URL=https://sattva-streamer.top
TEST_JWT_TOKEN=<your_token>
```

## Архитектура Evaluators

### AudioProcessingQualityEvaluator
```python
class AudioProcessingQualityEvaluator:
    def __call__(self, *, request_payload, response_body, status_code, **kwargs):
        # Проверка HTTP статуса, session_id, параметров обработки
        return {
            "audio_processing_quality_score": 0-5,
            "audio_processing_quality_reason": "..."
        }
```

### APIResponseTimeEvaluator
```python
class APIResponseTimeEvaluator:
    def __call__(self, *, endpoint, status_code, execution_time_ms=None, **kwargs):
        # Оценка производительности по типу endpoint
        return {
            "api_response_time_score": 0-5,
            "api_response_time_reason": "..."
        }
```

### UserSettingsIntegrationEvaluator
```python
class UserSettingsIntegrationEvaluator:
    def __call__(self, *, endpoint, method, request_payload, 
                 response_body, status_code, **kwargs):
        # Проверка CRUD операций и применения настроек
        return {
            "user_settings_integration_score": 0-5,
            "user_settings_integration_reason": "..."
        }
```

## Интеграция с CI/CD

Evaluation можно интегрировать в CI/CD pipeline:

```yaml
# .github/workflows/evaluation.yml
- name: Run Audio API Evaluation
  run: |
    cd tests/evaluation
    python run_evaluation.py
    
- name: Check Metrics Threshold
  run: |
    python -c "
    import json
    with open('tests/evaluation/evaluation_results', 'r') as f:
        results = json.load(f)
    
    # Минимальные пороги качества
    assert results['metrics']['audio_quality.audio_processing_quality_score'] >= 3.5
    assert results['metrics']['api_performance.api_response_time_score'] >= 4.0
    assert results['metrics']['settings_integration.user_settings_integration_score'] >= 4.0
    "
```

## Troubleshooting

### Ошибка: Missing inputs for line
**Решение:** Убедитесь, что все поля в `column_mapping` присутствуют в dataset JSONL.

### Ошибка: Authentication failed
**Решение:** Получите новый JWT токен через `get_test_token.py`.

### Ошибка: Connection refused
**Решение:** Проверьте `BACKEND_BASE_URL` в `.env.test`.

## Следующие шаги

1. ✅ Evaluation framework настроен
2. ⏳ Настроить OpenTelemetry tracing
3. ⏳ Создать unit тесты для audio API
4. ⏳ Добавить performance benchmarks
5. ⏳ Интегрировать в CI/CD pipeline
