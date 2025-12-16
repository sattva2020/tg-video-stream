"""
Преобразование собранных responses в JSONL формат для Azure AI Evaluation SDK.
Удаление timestamp полей для предотвращения ошибок SDK.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def transform_to_jsonl():
    """Преобразовать responses в JSONL формат без timestamps."""
    
    # Загрузить queries и responses
    queries_file = Path(__file__).parent / "audio_test_queries.json"
    responses_file = Path(__file__).parent / "audio_test_responses.json"
    output_file = Path(__file__).parent / "audio_evaluation_dataset.jsonl"
    
    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = {q['query_id']: q for q in json.load(f)}
    
    with open(responses_file, 'r', encoding='utf-8') as f:
        responses = json.load(f)
    
    # Создать JSONL dataset
    dataset = []
    
    for response_data in responses:
        query_id = response_data['query_id']
        query = queries.get(query_id, {})
        
        # Подготовить данные для evaluation
        # ВАЖНО: Удаляем timestamp поля - они вызывают ошибки SDK
        record = {
            "query_id": query_id,
            "endpoint": query.get("endpoint", ""),
            "method": query.get("method", ""),
            "description": query.get("description", ""),
            
            # Input data
            "request_payload": response_data.get("input", {}).get("payload", {}),
            "query_params": response_data.get("input", {}).get("query_params", {}),
            
            # Response data
            "status_code": response_data.get("response", {}).get("status_code"),
            "response_body": response_data.get("response", {}).get("body", {}),
            "success": response_data.get("success", False),
            
            # Expected behavior для reference
            "expected_behavior": query.get("expected_behavior", ""),
            
            # Поля для Azure AI Evaluation (стандартные имена)
            "query": f"{query.get('method', '')} {query.get('endpoint', '')} - {query.get('description', '')}",
            "response": json.dumps(response_data.get("response", {}).get("body", {})),
            "context": json.dumps({
                "request": response_data.get("input", {}).get("payload", {}),
                "expected": query.get("expected_behavior", "")
            })
        }
        
        # Добавить error если есть
        if "error" in response_data:
            record["error"] = response_data["error"]
        
        dataset.append(record)
    
    # Сохранить в JSONL
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in dataset:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✓ Dataset transformed to JSONL format")
    print(f"  Input: {responses_file}")
    print(f"  Output: {output_file}")
    print(f"  Records: {len(dataset)}")
    print(f"\nDataset ready for Azure AI Evaluation!")


if __name__ == "__main__":
    transform_to_jsonl()
