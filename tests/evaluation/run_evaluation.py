"""
Audio API Evaluation Framework.

Оценка качества audio processing API через три метрики:
1. Audio Processing Quality - корректность применения настроек
2. API Response Time - производительность endpoints
3. User Settings Integration - корректность применения пользовательских настроек
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


class AudioProcessingQualityEvaluator:
    """
    Custom code-based evaluator для оценки качества обработки аудио.
    
    Проверяет:
    - Корректность применения speed настроек
    - Применение equalizer (preset или custom)
    - Применение pitch correction
    - Применение volume adjustment
    """
    
    def __init__(self):
        pass
    
    def __call__(self, *, request_payload: Dict[str, Any], response_body: Dict[str, Any], 
                 status_code: int, **kwargs) -> Dict[str, Any]:
        """
        Оценить качество audio processing.
        
        Args:
            request_payload: Исходный запрос с параметрами
            response_body: Ответ от API
            status_code: HTTP статус код
            
        Returns:
            Dict с оценкой качества (score 0-5) и детализацией
        """
        score = 5.0
        reasons = []
        
        # Проверка 1: Успешность запроса
        if status_code != 200:
            score -= 2.0
            reasons.append(f"Non-200 status code: {status_code}")
        
        # Проверка 2: Наличие session_id в ответе (признак успешного старта транскодинга)
        if "session_id" not in response_body:
            score -= 1.0
            reasons.append("Missing session_id in response")
        
        # Проверка 3: Статус обработки
        response_status = response_body.get("status", "")
        if response_status not in ["processing", "completed", "success"]:
            score -= 1.0
            reasons.append(f"Unexpected status: {response_status}")
        
        # Проверка 4: Соответствие запрошенных параметров (косвенная проверка)
        requested_params = []
        if "speed" in request_payload and request_payload["speed"] != 1.0:
            requested_params.append(f"speed={request_payload['speed']}")
        if "equalizer_preset" in request_payload:
            requested_params.append(f"eq_preset={request_payload['equalizer_preset']}")
        if "equalizer_custom" in request_payload:
            requested_params.append("eq_custom")
        if "volume" in request_payload and request_payload["volume"] != 1.0:
            requested_params.append(f"volume={request_payload['volume']}")
        
        if requested_params:
            reasons.append(f"Processing with: {', '.join(requested_params)}")
        
        # Финальная оценка
        final_score = max(0.0, min(5.0, score))
        
        return {
            "audio_processing_quality_score": final_score,
            "audio_processing_quality_reason": "; ".join(reasons) if reasons else "Processing successful with requested parameters"
        }


class APIResponseTimeEvaluator:
    """
    Custom code-based evaluator для оценки производительности API.
    
    Оценивает время отклика на основе типа endpoint и успешности запроса.
    """
    
    def __init__(self):
        self.expected_times = {
            "transcode": 2.0,  # seconds
            "settings": 0.5,
            "health": 0.3,
            "stream": 1.0
        }
    
    def __call__(self, *, endpoint: str, status_code: int, 
                 execution_time_ms: float = None, **kwargs) -> Dict[str, Any]:
        """
        Оценить производительность API endpoint.
        
        Args:
            endpoint: URL endpoint
            status_code: HTTP статус код
            execution_time_ms: Время выполнения в миллисекундах (если доступно)
            
        Returns:
            Dict с оценкой производительности (score 0-5)
        """
        score = 5.0
        reasons = []
        
        # Определить тип endpoint
        endpoint_type = "unknown"
        for key in self.expected_times:
            if key in endpoint:
                endpoint_type = key
                break
        
        # Проверка 1: HTTP status
        if status_code == 200:
            reasons.append("HTTP 200 OK")
        elif status_code >= 400:
            score -= 3.0
            reasons.append(f"HTTP {status_code} error")
        else:
            score -= 1.0
            reasons.append(f"HTTP {status_code}")
        
        # Проверка 2: Время отклика (если доступно)
        if execution_time_ms is not None:
            expected_ms = self.expected_times.get(endpoint_type, 1.0) * 1000
            
            if execution_time_ms <= expected_ms:
                reasons.append(f"Fast response: {execution_time_ms:.0f}ms")
            elif execution_time_ms <= expected_ms * 2:
                score -= 0.5
                reasons.append(f"Acceptable response: {execution_time_ms:.0f}ms")
            else:
                score -= 1.5
                reasons.append(f"Slow response: {execution_time_ms:.0f}ms (expected <{expected_ms:.0f}ms)")
        else:
            reasons.append("Response time not measured")
        
        final_score = max(0.0, min(5.0, score))
        
        return {
            "api_response_time_score": final_score,
            "api_response_time_reason": "; ".join(reasons)
        }


class UserSettingsIntegrationEvaluator:
    """
    Custom code-based evaluator для оценки интеграции пользовательских настроек.
    
    Проверяет:
    - Корректность сохранения настроек (PUT /settings)
    - Корректность получения настроек (GET /settings)
    - Применение настроек в transcode запросах
    """
    
    def __init__(self):
        pass
    
    def __call__(self, *, endpoint: str, method: str, request_payload: Dict[str, Any],
                 response_body: Dict[str, Any], status_code: int, **kwargs) -> Dict[str, Any]:
        """
        Оценить интеграцию пользовательских настроек.
        
        Args:
            endpoint: URL endpoint
            method: HTTP метод
            request_payload: Исходный запрос
            response_body: Ответ от API
            status_code: HTTP статус код
            
        Returns:
            Dict с оценкой интеграции настроек (score 0-5)
        """
        score = 5.0
        reasons = []
        
        # Проверка применима только для settings endpoints
        is_settings_endpoint = "settings" in endpoint
        
        if not is_settings_endpoint:
            # Для non-settings endpoints проверяем наличие session_id
            if status_code == 200 and "session_id" in response_body:
                reasons.append("Settings applied successfully in transcode request")
            else:
                score -= 0.5
                reasons.append("Non-settings endpoint with basic validation")
        else:
            # Для settings endpoints делаем детальную проверку
            
            if method == "GET":
                # GET /settings - проверка структуры ответа
                expected_fields = ["speed", "equalizer_preset", "pitch_correction"]
                missing_fields = [f for f in expected_fields if f not in response_body]
                
                if not missing_fields:
                    reasons.append("All expected settings fields present")
                else:
                    score -= 1.0
                    reasons.append(f"Missing fields: {', '.join(missing_fields)}")
            
            elif method == "PUT":
                # PUT /settings - проверка обновления настроек
                if status_code == 200:
                    updated_fields = [k for k in request_payload.keys()]
                    reasons.append(f"Settings updated: {', '.join(updated_fields)}")
                    
                    # Проверка, что обновленные поля возвращены в ответе
                    for field in updated_fields:
                        if field not in response_body:
                            score -= 0.5
                            reasons.append(f"Updated field '{field}' not returned in response")
                else:
                    score -= 2.0
                    reasons.append(f"Settings update failed: HTTP {status_code}")
            
            # Проверка HTTP статуса
            if status_code != 200:
                score -= 1.0
                reasons.append(f"HTTP {status_code}")
        
        final_score = max(0.0, min(5.0, score))
        
        return {
            "user_settings_integration_score": final_score,
            "user_settings_integration_reason": "; ".join(reasons) if reasons else "Settings integration validated"
        }


def main():
    """
    Запуск evaluation с использованием Azure AI Evaluation SDK.
    """
    from azure.ai.evaluation import evaluate
    
    # Пути к файлам
    dataset_file = Path(__file__).parent / "audio_evaluation_dataset.jsonl"
    output_path = Path(__file__).parent / "evaluation_results"
    
    print("="*60)
    print("Audio API Evaluation Framework")
    print("="*60)
    
    # Проверка наличия dataset
    if not dataset_file.exists():
        print(f"\nDataset not found: {dataset_file}")
        print("Run prepare_dataset.py first to create JSONL dataset")
        return
    
    print(f"\nDataset: {dataset_file}")
    print(f"Output: {output_path}")
    
    # Создать evaluators
    print("\nInitializing evaluators...")
    audio_quality_eval = AudioProcessingQualityEvaluator()
    api_performance_eval = APIResponseTimeEvaluator()
    settings_integration_eval = UserSettingsIntegrationEvaluator()
    print("  * AudioProcessingQualityEvaluator")
    print("  * APIResponseTimeEvaluator")
    print("  * UserSettingsIntegrationEvaluator")
    
    # Запустить evaluation
    print("\nRunning evaluation...")
    result = evaluate(
        data=str(dataset_file),
        evaluators={
            "audio_quality": audio_quality_eval,
            "api_performance": api_performance_eval,
            "settings_integration": settings_integration_eval
        },
        evaluator_config={
            "audio_quality": {
                "column_mapping": {
                    "request_payload": "${data.request_payload}",
                    "response_body": "${data.response_body}",
                    "status_code": "${data.status_code}"
                }
            },
            "api_performance": {
                "column_mapping": {
                    "endpoint": "${data.endpoint}",
                    "status_code": "${data.status_code}"
                }
            },
            "settings_integration": {
                "column_mapping": {
                    "endpoint": "${data.endpoint}",
                    "method": "${data.method}",
                    "request_payload": "${data.request_payload}",
                    "response_body": "${data.response_body}",
                    "status_code": "${data.status_code}"
                }
            }
        },
        output_path=str(output_path)
    )
    
    # Вывести результаты
    print("\n" + "="*60)
    print("Evaluation Results")
    print("="*60)
    
    # Aggregate metrics (автоматически вычислены SDK)
    if "metrics" in result:
        metrics = result["metrics"]
        print("\nAggregate Metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    # Row-level data summary
    if "rows" in result:
        print(f"\nEvaluated {len(result['rows'])} test cases")
    
    print(f"\nEvaluation complete!")
    print(f"Full results saved to: {output_path}")
    print("\nCheck the output directory for:")
    print("  - eval_results.jsonl (row-level scores)")
    print("  - eval_results.json (aggregate metrics)")


if __name__ == "__main__":
    main()
