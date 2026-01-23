#!/usr/bin/env python3
"""
Валидация импортов i18n на наличие конфликтов.
Проверяет дубликаты ключей, отсутствующие переводы и конфликты в импорте.
"""
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple

# Путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
I18N_DIR = FRONTEND_SRC / "i18n"
I18N_INDEX = I18N_DIR / "index.ts"
LOCALES_DIR = I18N_DIR / "locales"

# Поддерживаемые языки
LANGUAGES = ["en", "ru", "uk", "de"]

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Валидация импортов i18n на наличие конфликтов и дубликатов"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывод результатов в формате JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Подробный вывод с listing всех проблем"
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Вернуть ненулевой код при наличии предупреждений"
    )
    return parser.parse_args()

def extract_i18n_resources():
    """Извлекает ресурсы из i18n/index.ts"""
    if not I18N_INDEX.exists():
        print(f"ERROR: Файл не найден: {I18N_INDEX}")
        return None

    content = I18N_INDEX.read_text(encoding='utf-8')

    # Найти объект I18N_RESOURCES
    pattern = r'export\s+const\s+I18N_RESOURCES\s*=\s*\{'
    match = re.search(pattern, content)

    if not match:
        print("ERROR: Не найден объект I18N_RESOURCES")
        return None

    # Найти весь объект (балансировка скобок)
    start_pos = match.end()
    brace_count = 1
    end_pos = start_pos

    for i in range(start_pos, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = i + 1
                break

    return content[match.start():end_pos]

def find_duplicate_keys_in_i18n_object(i18n_content: str) -> Dict[str, List[int]]:
    """
    Находит дубликаты ключей в объекте I18N_RESOURCES.
    Возвращает словарь {ключ: [список позиций]}
    """
    duplicates = defaultdict(list)

    # Найти все ключи в кавычках вида 'key.name': или "key.name":
    # Учитываем nested keys через поиск паттернов
    pattern = r'["\']([a-zA-Z_][a-zA-Z0-9_.]*)["\']\s*:'

    lines = i18n_content.split('\n')
    key_positions = defaultdict(list)

    for line_num, line in enumerate(lines, 1):
        matches = re.finditer(pattern, line)
        for match in matches:
            key = match.group(1)
            # Пропускаем служебные ключи i18next
            if key in ['translation', 'lng', 'fallbackLng']:
                continue
            key_positions[key].append((line_num, match.start()))

    # Найти дубликаты
    for key, positions in key_positions.items():
        if len(positions) > 1:
            duplicates[key] = [pos[0] for pos in positions]

    return duplicates

def load_locale_files() -> Dict[str, dict]:
    """Загружает все файлы локалей"""
    locales = {}

    for lang in LANGUAGES:
        locale_file = LOCALES_DIR / f"{lang}.json"
        if not locale_file.exists():
            print(f"WARNING: Файл локали не найден: {locale_file}")
            locales[lang] = {}
            continue

        try:
            content = locale_file.read_text(encoding='utf-8')
            locales[lang] = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"ERROR: Ошибка парсинга JSON в {locale_file}: {e}")
            locales[lang] = {}

    return locales

def extract_nested_keys(data: dict, prefix: str = "") -> Set[str]:
    """Рекурсивно извлекает все ключи из вложенного объекта"""
    keys = set()

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            keys.update(extract_nested_keys(value, full_key))
        else:
            keys.add(full_key)

    return keys

def find_missing_keys_across_languages(locales: Dict[str, dict]) -> Dict[str, Set[str]]:
    """
    Находит ключи, отсутствующие в некоторых языках.
    Возвращает {язык: {набор отсутствующих ключей}}
    """
    # Получить все ключи для каждого языка
    lang_keys = {}
    for lang, data in locales.items():
        lang_keys[lang] = extract_nested_keys(data)

    # Найти объединение всех ключей
    all_keys = set()
    for keys in lang_keys.values():
        all_keys.update(keys)

    # Найти отсутствующие ключи для каждого языка
    missing = {}
    for lang in LANGUAGES:
        missing[lang] = all_keys - lang_keys.get(lang, set())

    return missing

def find_inconsistent_nested_structure(locales: Dict[str, dict]) -> List[Tuple[str, str, str]]:
    """
    Находит несоответствия в структуре вложенных объектов.
    Возвращает список (ключ, язык, тип_проблемы)
    """
    issues = []

    def check_structure(path: str, data: dict, reference: dict, lang: str):
        """Рекурсивно проверяет структуру"""
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if key not in reference:
                continue

            ref_value = reference[key]

            # Проверяем типы
            if isinstance(value, dict) and not isinstance(ref_value, dict):
                issues.append((current_path, lang, "expected_object"))
            elif not isinstance(value, dict) and isinstance(ref_value, dict):
                issues.append((current_path, lang, "expected_value"))
            elif isinstance(value, dict) and isinstance(ref_value, dict):
                check_structure(current_path, value, ref_value, lang)

    # Используем английский как референс
    if 'en' not in locales:
        return issues

    reference = locales['en']

    for lang in LANGUAGES:
        if lang == 'en':
            continue

        if lang in locales:
            check_structure("", locales[lang], reference, lang)

    return issues

def find_unused_imports(i18n_content: str) -> List[str]:
    """Находит импорты, которые не используются в I18N_RESOURCES"""
    # Найти все импорты JSON файлов
    import_pattern = r"import\s+\w+\s+from\s+['\"]\.\/locales\/(\w+)\.json['\"]"
    imports = re.findall(import_pattern, i18n_content)

    # Найти какие языки реально используются
    used_locales = set()
    for lang in LANGUAGES:
        if f"{lang}:" in i18n_content and f"{lang}Audio" in i18n_content:
            used_locales.add(lang)

    unused = []
    for imp in imports:
        lang = imp.replace('Audio', '').lower()
        if lang not in used_locales:
            unused.append(imp)

    return unused

def main():
    args = parse_arguments()

    print("=" * 70)
    print("I18N IMPORT CONFLICT DETECTION")
    print("=" * 70)
    print()

    all_issues = []
    exit_code = 0

    # 1. Проверка дубликатов ключей в i18n/index.ts
    print("Step 1: Checking for duplicate keys in i18n/index.ts...")
    i18n_content = extract_i18n_resources()

    if i18n_content:
        duplicates = find_duplicate_keys_in_i18n_object(i18n_content)

        if duplicates:
            print(f"ERROR: Found {len(duplicates)} duplicate key(s)")
            all_issues.append({
                "type": "duplicate_keys",
                "severity": "error",
                "count": len(duplicates),
                "details": duplicates
            })
            exit_code = 1

            if args.verbose:
                for key, positions in sorted(duplicates.items()):
                    print(f"   - '{key}' at lines: {', '.join(map(str, positions))}")
            else:
                for key in sorted(duplicates.keys())[:5]:
                    print(f"   - '{key}'")
                if len(duplicates) > 5:
                    print(f"   ... and {len(duplicates) - 5} more")
        else:
            print("OK: No duplicate keys found")
        print()
    else:
        print("ERROR: Could not parse i18n/index.ts")
        print()
        exit_code = 1

    # 2. Проверка отсутствующих ключей в локалях
    print("Step 2: Checking for missing translation keys...")
    locales = load_locale_files()

    if any(locales.values()):
        missing_keys = find_missing_keys_across_languages(locales)

        has_missing = False
        for lang, keys in missing_keys.items():
            if keys:
                has_missing = True
                print(f"WARNING: {lang.upper()}: Missing {len(keys)} key(s)")
                all_issues.append({
                    "type": "missing_keys",
                    "severity": "warning",
                    "language": lang,
                    "count": len(keys),
                    "details": list(keys) if args.verbose else list(keys)[:10]
                })
                if args.verbose:
                    for key in sorted(keys):
                        print(f"   - {key}")
                else:
                    for key in sorted(keys)[:5]:
                        print(f"   - {key}")
                    if len(keys) > 5:
                        print(f"   ... and {len(keys) - 5} more")

        if not has_missing:
            print("OK: All keys present in all languages")
        elif args.fail_on_warning:
            exit_code = 1
        print()

    # 3. Проверка несоответствия структуры
    print("Step 3: Checking for inconsistent nested structure...")
    if locales.get('en'):
        structure_issues = find_inconsistent_nested_structure(locales)

        if structure_issues:
            print(f"WARNING: Found {len(structure_issues)} structure issue(s)")
            all_issues.append({
                "type": "structure_mismatch",
                "severity": "warning",
                "count": len(structure_issues),
                "details": structure_issues if args.verbose else structure_issues[:10]
            })

            if args.verbose:
                for key, lang, issue_type in structure_issues:
                    print(f"   - {key} in {lang.upper()}: {issue_type}")
            else:
                for key, lang, issue_type in structure_issues[:5]:
                    print(f"   - {key} in {lang.upper()}: {issue_type}")
                if len(structure_issues) > 5:
                    print(f"   ... and {len(structure_issues) - 5} more")

            if args.fail_on_warning:
                exit_code = 1
        else:
            print("OK: Structure consistent across languages")
        print()
    else:
        print("SKIP: English locale not available for reference")
        print()

    # 4. Неиспользуемые импорты
    print("Step 4: Checking for unused imports...")
    if i18n_content:
        unused_imports = find_unused_imports(i18n_content)

        if unused_imports:
            print(f"WARNING: Found {len(unused_imports)} unused import(s)")
            all_issues.append({
                "type": "unused_imports",
                "severity": "warning",
                "count": len(unused_imports),
                "details": unused_imports
            })

            for imp in unused_imports:
                print(f"   - {imp}")

            if args.fail_on_warning:
                exit_code = 1
        else:
            print("OK: All imports are used")
        print()

    # 5. Сводка
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    error_count = sum(1 for issue in all_issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in all_issues if issue["severity"] == "warning")

    print(f"Errors: {error_count}")
    print(f"Warnings: {warning_count}")
    print()

    # 6. JSON вывод
    if args.json:
        report = {
            "exit_code": exit_code,
            "total_issues": len(all_issues),
            "errors": error_count,
            "warnings": warning_count,
            "issues": all_issues
        }

        report_file = PROJECT_ROOT / "docs" / "REPORTS" / "i18n-import-validation.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"JSON report saved: {report_file.relative_to(PROJECT_ROOT)}")
        print()

    return exit_code

if __name__ == "__main__":
    exit(main())
