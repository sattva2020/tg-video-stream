#!/usr/bin/env python3
"""
Backend Coverage Parser
Парсит coverage.json и выводит красивую таблицу
"""

import json
import sys
from pathlib import Path

SERVICES = {
    'src\\services\\playback_service.py': 'playback_service',
    'src\\services\\auth_service.py': 'auth_service',
    'src\\services\\session_service.py': 'session_service',
    'src\\services\\activity_service.py': 'activity_service',
    'src\\services\\telegram_rate_limiter.py': 'telegram_rate_limiter',
    'src\\services\\queue_service.py': 'queue_service',
    'src\\services\\priority_queue_service.py': 'priority_queue_service',
    'src\\services\\channel_service.py': 'channel_service'
}

def get_status_emoji(percent: float) -> str:
    """Возвращает эмодзи в зависимости от процента покрытия"""
    if percent >= 99:
        return '🟢'
    elif percent >= 95:
        return '🟡'
    else:
        return '🔴'

def parse_coverage():
    """Парсит coverage.json и выводит отчёт"""
    coverage_file = Path('coverage.json')
    
    if not coverage_file.exists():
        print('\033[0;31mError: coverage.json not found\033[0m')
        sys.exit(1)
    
    try:
        with open(coverage_file, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'\033[0;31mError reading coverage.json: {e}\033[0m')
        sys.exit(1)
    
    # Заголовок таблицы
    print('\n┌─────────────────────────────┬──────────┬────────┐')
    print('│ Service                     │ Coverage │ Status │')
    print('├─────────────────────────────┼──────────┼────────┤')
    
    total_percent = 0
    count = 0
    
    # Данные по каждому сервису
    for file_path, name in SERVICES.items():
        if file_path in data['files']:
            file_data = data['files'][file_path]
            percent = file_data['summary']['percent_covered']
            status = get_status_emoji(percent)
            
            print(f'│ {name:27} │ {percent:6.1f}% │   {status}   │')
            
            total_percent += percent
            count += 1
        else:
            print(f'│ {name:27} │    N/A │   ❓   │')
    
    # Средний процент
    if count > 0:
        avg = total_percent / count
        
        if avg >= 98:
            status = '🎉'
        elif avg >= 95:
            status = '✅'
        else:
            status = '⚠️'
        
        print('├─────────────────────────────┼──────────┼────────┤')
        print(f'│ AVERAGE                     │ {avg:6.2f}% │   {status}   │')
        print('└─────────────────────────────┴──────────┴────────┘\n')
        
        # Итоговое сообщение
        if avg >= 98:
            print('\033[0;32m🎉 Excellent coverage! Target achieved!\033[0m')
        elif avg >= 95:
            print('\033[1;33m⚠️  Good coverage, but can be improved\033[0m')
        else:
            print('\033[0;31m❌ Coverage below target (95%)\033[0m')
            sys.exit(1)
    else:
        print('└─────────────────────────────┴──────────┴────────┘\n')
        print('\033[0;31m❌ No coverage data found\033[0m')
        sys.exit(1)

if __name__ == '__main__':
    parse_coverage()
