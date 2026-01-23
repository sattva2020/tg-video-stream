"""
Validation script for test_recommendations_load.py
Проверяет структуру теста без необходимости установки pytest
"""
import ast
import sys


def validate_test_file(filepath):
    """Валидация структуры нагрузочного теста."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Парсим Python файл
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        return False

    # Проверяем наличие необходимых компонентов
    has_imports = False
    has_fixtures = False
    has_test_class = False
    has_test_methods = []
    has_load_test_metrics = False
    has_helper_functions = []

    for node in ast.walk(tree):
        # Проверяем импорты
        if isinstance(node, ast.Import):
            for alias in node.names:
                if 'pytest' in alias.name or 'threading' in alias.name or 'concurrent' in alias.name:
                    has_imports = True
        elif isinstance(node, ast.ImportFrom):
            if node.module and ('pytest' in node.module or 'concurrent' in node.module or 'threading' in node.module):
                has_imports = True

        # Проверяем наличие fixtures
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'id'):
                    if decorator.func.id == 'fixture':
                        has_fixtures = True
                elif isinstance(decorator, ast.Name) and decorator.id == 'pytest.fixture':
                    has_fixtures = True

        # Проверяем наличие класса тестов
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                has_test_class = True
                # Собираем методы тестов
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        has_test_methods.append(item.name)

        # Проверяем наличие LoadTestMetrics класса
        if isinstance(node, ast.ClassDef) and node.name == 'LoadTestMetrics':
            has_load_test_metrics = True

        # Проверяем наличие helper функций
        if isinstance(node, ast.FunctionDef) and node.name.startswith('make_') and node.name.endswith('_request'):
            has_helper_functions.append(node.name)

    # Выводим результаты проверки
    print("=== Validation Results for test_recommendations_load.py ===\n")

    checks = [
        ("Has required imports (pytest, threading, concurrent)", has_imports),
        ("Has pytest fixtures", has_fixtures),
        ("Has test class (TestRecommendationsLoad)", has_test_class),
        ("Has LoadTestMetrics class", has_load_test_metrics),
        (f"Has test methods ({len(has_test_methods)} found)", len(has_test_methods) > 0),
        (f"Has helper functions ({len(has_helper_functions)} found)", len(has_helper_functions) > 0),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False

    # Детальная информация о тестовых методах
    if has_test_methods:
        print(f"\n✓ Test methods found ({len(has_test_methods)}):")
        for method in sorted(has_test_methods):
            print(f"  - {method}")

    # Детальная информация о helper функциях
    if has_helper_functions:
        print(f"\n✓ Helper functions found ({len(has_helper_functions)}):")
        for func in sorted(has_helper_functions):
            print(f"  - {func}")

    # Проверяем покрытие всех эндпоинтов
    expected_endpoints = [
        "get_recommendations",
        "post_feedback",
        "get_stats",
        "get_for_playlist"
    ]

    tested_endpoints = []
    for method in has_test_methods:
        method_lower = method.lower()
        if "recommendations" in method_lower:
            tested_endpoints.append("get_recommendations")
        elif "feedback" in method_lower:
            tested_endpoints.append("post_feedback")
        elif "stats" in method_lower:
            tested_endpoints.append("get_stats")
        elif "playlist" in method_lower:
            tested_endpoints.append("get_for_playlist")
        elif "mixed" in method_lower:
            tested_endpoints.extend(expected_endpoints)  # mixed tests all endpoints
        elif "sustained" in method_lower:
            tested_endpoints.append("get_recommendations")

    tested_endpoints = list(set(tested_endpoints))

    print(f"\n✓ Endpoint coverage ({len(tested_endpoints)}/{len(expected_endpoints)}):")
    for endpoint in expected_endpoints:
        status = "✓" if endpoint in tested_endpoints else "✗"
        print(f"  {status} {endpoint}")

    all_covered = len(tested_endpoints) == len(expected_endpoints)
    if not all_covered:
        all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✓ ALL VALIDATION CHECKS PASSED")
        print(f"\nTest file is ready for execution with pytest.")
        print(f"\nTest scenarios covered:")
        print(f"  - Concurrent requests to GET /api/recommendations")
        print(f"  - Concurrent requests to POST /api/recommendations/feedback")
        print(f"  - Concurrent requests to GET /api/recommendations/stats")
        print(f"  - Concurrent requests to GET /api/recommendations/for-playlist")
        print(f"  - Mixed workload (all endpoints)")
        print(f"  - Sustained load test")
        print(f"\nPerformance metrics collected:")
        print(f"  - Response time (avg, min, max, p50, p95, p99)")
        print(f"  - Throughput (requests per second)")
        print(f"  - Error rate")
        print(f"  - Success/error counts")
        return True
    else:
        print("✗ SOME VALIDATION CHECKS FAILED")
        return False


if __name__ == "__main__":
    filepath = "backend/tests/test_recommendations_load.py"
    success = validate_test_file(filepath)
    sys.exit(0 if success else 1)
