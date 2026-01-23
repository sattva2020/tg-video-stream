#!/usr/bin/env python3
"""
Verify Load Test Results

Анализирует результаты нагрузочного тестирования и проверяет соответствие критериям.

Usage:
    python scripts/verify_load_test_results.py load_test_recovery_report.json
"""

import argparse
import json
import sys
from pathlib import Path


def verify_uptime_threshold(uptime_percentage: float, threshold: float = 99.0) -> dict:
    """Проверка процента доступности."""
    passed = uptime_percentage >= threshold
    return {
        'metric': 'uptime_percentage',
        'value': uptime_percentage,
        'threshold': threshold,
        'passed': passed,
        'message': f"Uptime {uptime_percentage:.2f}% {'✅' if passed else '❌'} (требование: >={threshold}%)"
    }


def verify_recovery_logging(total_failures: int, recovery_logs_count: int) -> dict:
    """Проверка логирования событий восстановления."""
    passed = recovery_logs_count >= total_failures
    return {
        'metric': 'recovery_logging',
        'value': recovery_logs_count,
        'expected': total_failures,
        'passed': passed,
        'message': f"Логов восстановления: {recovery_logs_count}/{total_failures} {'✅' if passed else '❌'}"
    }


def verify_recovery_success_rate(successful: int, failed: int) -> dict:
    """Проверка成功率 восстановления."""
    total = successful + failed
    if total == 0:
        return {
            'metric': 'recovery_success_rate',
            'value': 100.0,
            'passed': True,
            'message': "Нет отказов для проверки ✅"
        }

    success_rate = (successful / total) * 100
    passed = success_rate >= 90.0  # Требуем 90%+ success rate
    return {
        'metric': 'recovery_success_rate',
        'value': success_rate,
        'passed': passed,
        'message': f"Success rate: {success_rate:.2f}% {'✅' if passed else '❌'} (требование: >=90%)"
    }


def verify_circuit_breaker_effectiveness(trips: int, total_failures: int) -> dict:
    """Проверка эффективности circuit breaker."""
    if total_failures == 0:
        return {
            'metric': 'circuit_breaker_effectiveness',
            'value': 0,
            'passed': True,
            'message': "Нет отказов для проверки ✅"
        }

    # Circuit breaker should trip on < 20% of failures
    trip_rate = (trips / total_failures) * 100
    passed = trip_rate < 20.0
    return {
        'metric': 'circuit_breaker_effectiveness',
        'value': trip_rate,
        'passed': passed,
        'message': f"Circuit breaker trips: {trip_rate:.2f}% {'✅' if passed else '❌'} (требование: <20%)"
    }


def verify_no_unexpected_errors(report: dict) -> dict:
    """Проверка отсутствия неожиданных ошибок."""
    # Check for signs of crashes or unexpected behavior
    issues = []

    # Check if any stream has 0% uptime (complete failure)
    for sr in report.get('stream_reports', []):
        if sr['uptime_percentage'] < 50.0:
            issues.append(f"Stream {sr['stream_id']} has very low uptime: {sr['uptime_percentage']:.2f}%")

    # Check for excessive failed recoveries
    if report.get('total_failed_recoveries', 0) > report.get('total_successful_recoveries', 0):
        issues.append("More failed recoveries than successful ones")

    passed = len(issues) == 0
    return {
        'metric': 'no_unexpected_errors',
        'passed': passed,
        'issues': issues,
        'message': f"Неожиданные ошибки: {len(issues)} {'✅' if passed else '❌'}"
    }


def verify_per_stream_uptime(stream_reports: list, threshold: float = 95.0) -> dict:
    """Проверка uptime на каждый поток."""
    below_threshold = [
        sr['stream_id'] for sr in stream_reports
        if sr['uptime_percentage'] < threshold
    ]

    passed = len(below_threshold) == 0
    return {
        'metric': 'per_stream_uptime',
        'value': len(stream_reports) - len(below_threshold),
        'total': len(stream_reports),
        'passed': passed,
        'below_threshold_streams': below_threshold,
        'message': f"Потоков с uptime >={threshold}%: {len(stream_reports) - len(below_threshold)}/{len(stream_reports)} {'✅' if passed else '❌'}"
    }


def analyze_report(report_path: str) -> dict:
    """Анализ отчета о нагрузочном тестировании."""
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    verifications = []

    # 1. Verify uptime threshold (main criterion)
    verifications.append(
        verify_uptime_threshold(report.get('overall_uptime_percentage', 0))
    )

    # 2. Verify all recovery events are logged
    total_failures = report.get('total_failures', 0)
    recovery_logs_count = len(report.get('recovery_logs', []))
    verifications.append(
        verify_recovery_logging(total_failures, recovery_logs_count)
    )

    # 3. Verify recovery success rate
    verifications.append(
        verify_recovery_success_rate(
            report.get('total_successful_recoveries', 0),
            report.get('total_failed_recoveries', 0)
        )
    )

    # 4. Verify circuit breaker effectiveness
    verifications.append(
        verify_circuit_breaker_effectiveness(
            report.get('circuit_breaker_trips', 0),
            total_failures
        )
    )

    # 5. Verify no unexpected errors
    verifications.append(
        verify_no_unexpected_errors(report)
    )

    # 6. Verify per-stream uptime
    verifications.append(
        verify_per_stream_uptime(report.get('stream_reports', []))
    )

    # Overall result
    all_passed = all(v['passed'] for v in verifications)

    return {
        'report_path': report_path,
        'overall_passed': all_passed,
        'verifications': verifications,
        'summary': {
            'total': len(verifications),
            'passed': sum(1 for v in verifications if v['passed']),
            'failed': sum(1 for v in verifications if not v['passed'])
        }
    }


def print_verification_results(analysis: dict):
    """Вывод результатов верификации."""
    print("="*80)
    print("РЕЗУЛЬТАТЫ ВЕРИФИКАЦИИ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    print("="*80)
    print(f"Файл отчета: {analysis['report_path']}")
    print()

    for i, verification in enumerate(analysis['verifications'], 1):
        print(f"{i}. {verification['message']}")

        # Add details if failed
        if not verification['passed']:
            if verification.get('issues'):
                for issue in verification['issues']:
                    print(f"   ⚠️  {issue}")
            if verification.get('below_threshold_streams'):
                print(f"   Потоки с низким uptime: {verification['below_threshold_streams']}")

        print()

    print("="*80)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("="*80)
    print(f"Проверок пройдено: {analysis['summary']['passed']}/{analysis['summary']['total']}")

    if analysis['overall_passed']:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
        print("Система соответствует требованиям к надежности")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        print("Требуется анализ и доработка")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Верификация результатов нагрузочного тестирования')
    parser.add_argument(
        'report_file',
        help='Путь к JSON файлу отчета'
    )

    args = parser.parse_args()

    # Check if report file exists
    report_path = Path(args.report_file)
    if not report_path.exists():
        print(f"❌ Файл отчета не найден: {args.report_file}")
        return 1

    # Analyze report
    try:
        analysis = analyze_report(args.report_file)
        return print_verification_results(analysis)

    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
