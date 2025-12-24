#!/usr/bin/env python3
"""
Полный аудит i18n переводов.
Проверяет, что все используемые ключи присутствуют во всех языках.
"""
import re
import json
from pathlib import Path
from collections import defaultdict

# Путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
I18N_FILE = FRONTEND_SRC / "i18n.ts"

# Поддерживаемые языки
LANGUAGES = ["en", "ru", "uk", "de"]

def extract_translation_keys_from_code():
    """Извлекает все ключи переводов из tsx/ts файлов"""
    keys = set()
    pattern = r't\(["\']([a-zA-Z_][a-zA-Z0-9_.]*)["\']'
    
    for tsx_file in FRONTEND_SRC.rglob("*.tsx"):
        content = tsx_file.read_text(encoding='utf-8')
        matches = re.findall(pattern, content)
        keys.update(matches)
    
    for ts_file in FRONTEND_SRC.rglob("*.ts"):
        if ts_file.name == "i18n.ts":
            continue
        content = ts_file.read_text(encoding='utf-8')
        matches = re.findall(pattern, content)
        keys.update(matches)
    
    return sorted(keys)

def extract_translation_keys_from_i18n():
    """Извлекает все ключи из файла i18n.ts для каждого языка"""
    content = I18N_FILE.read_text(encoding='utf-8')
    
    lang_keys = {}
    
    for lang in LANGUAGES:
        # Найти начало секции языка
        lang_pattern = rf'\b{lang}:\s*\{{\s*translation:\s*\{{'
        match = re.search(lang_pattern, content)
        if not match:
            print(f"WARNING: Ne naydena sektsiya yazyka: {lang}")
            lang_keys[lang] = set()
            continue
        
        start_pos = match.end()
        
        # Найти конец секции (закрывающую скобку)
        brace_count = 2  # Уже внутри двух открытых скобок
        end_pos = start_pos
        
        for i in range(start_pos, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        
        section = content[start_pos:end_pos]
        
        # Извлечь ключи (строки вида "key": "value")
        key_pattern = r'"([a-zA-Z_][a-zA-Z0-9_.]*)":\s*["\']'
        keys = re.findall(key_pattern, section)
        lang_keys[lang] = set(keys)
        
        print(f"OK {lang.upper()}: naydeno {len(keys)} klyuchey")
    
    return lang_keys

def main():
    print("=" * 70)
    print("POLNYY AUDIT I18N PEREVODOV")
    print("=" * 70)
    print()
    
    # 1. Извлечь используемые ключи из кода
    print("Etap 1: Izvlechenie ispolzuemykh klyuchey iz koda...")
    used_keys = extract_translation_keys_from_code()
    print(f"Naydeno {len(used_keys)} unikalnykh klyuchey v kode\n")
    
    # 2. Извлечь ключи из i18n.ts
    print("Etap 2: Izvlechenie klyuchey iz i18n.ts...")
    lang_keys = extract_translation_keys_from_i18n()
    print()
    
    # 3. Проверить недостающие переводы
    print("=" * 70)
    print("REZULTATY AUDITA")
    print("=" * 70)
    print()
    
    all_missing = defaultdict(list)
    
    for lang in LANGUAGES:
        missing = sorted([key for key in used_keys if key not in lang_keys[lang]])
        all_missing[lang] = missing
        
        if missing:
            print(f"MISSING {lang.upper()}: Otsutstvuet {len(missing)} klyuchey")
            for key in missing[:10]:  # Показать первые 10
                print(f"   - {key}")
            if len(missing) > 10:
                print(f"   ... i esche {len(missing) - 10} klyuchey")
            print()
        else:
            print(f"OK {lang.upper()}: Vse klyuchi prisutstvuyut")
            print()
    
    # 4. Найти неиспользуемые ключи
    print("=" * 70)
    print("NEISPOLZUEMYE KLYUCHI (mogut byt udaleny)")
    print("=" * 70)
    print()
    
    for lang in LANGUAGES:
        unused = sorted([key for key in lang_keys[lang] if key not in used_keys])
        if unused:
            print(f"UNUSED {lang.upper()}: {len(unused)} neispolzuemykh klyuchey")
            for key in unused[:10]:
                print(f"   - {key}")
            if len(unused) > 10:
                print(f"   ... i esche {len(unused) - 10} klyuchey")
            print()
    
    # 5. Сводка
    print("=" * 70)
    print("SVODNAYA STATISTIKA")
    print("=" * 70)
    print()
    print(f"Vsego klyuchey ispolzuetsya v kode: {len(used_keys)}")
    print()
    
    for lang in LANGUAGES:
        total = len(lang_keys[lang])
        missing = len(all_missing[lang])
        coverage = ((total - missing) / len(used_keys) * 100) if used_keys else 100
        status = "OK" if missing == 0 else "MISSING"
        print(f"{status} {lang.upper()}: {total} klyuchey ({coverage:.1f}% pokrytie)")
    
    print()
    
    # 6. Вывод в JSON для автоматизации
    report_file = PROJECT_ROOT / "docs" / "REPORTS" / "i18n-audit-report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    report = {
        "languages": LANGUAGES,
        "total_used_keys": len(used_keys),
        "used_keys": list(used_keys),
        "coverage": {
            lang: {
                "total": len(lang_keys[lang]),
                "missing": len(all_missing[lang]),
                "missing_keys": all_missing[lang],
                "coverage_percent": round(
                    ((len(lang_keys[lang]) - len(all_missing[lang])) / len(used_keys) * 100) 
                    if used_keys else 100, 
                    2
                )
            }
            for lang in LANGUAGES
        }
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Polnyy otchet sokhranyen: {report_file.relative_to(PROJECT_ROOT)}")
    print()
    
    # Вернуть код ошибки если есть недостающие переводы
    has_missing = any(len(all_missing[lang]) > 0 for lang in LANGUAGES)
    return 1 if has_missing else 0

if __name__ == "__main__":
    exit(main())
