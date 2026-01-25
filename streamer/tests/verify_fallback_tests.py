"""
Verification script for PyTgCalls fallback tests.

Runs tests without pytest dependency by directly executing test functions.
Tests verify that the system falls back to PyTgCalls when AyuGram is unavailable.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add streamer directory to path
sys.path.insert(0, '.')


async def test_fallback_when_use_ayugram_unset():
    """Когда USE_AYUGRAM не установлен, должен использоваться PyTgCalls."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Удаляем USE_AYUGRAM из окружения
        if "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]

        # Проверяем что is_available() возвращает False
        from ayugram_adapter import is_available
        assert is_available() is False

        print("✅ test_fallback_when_use_ayugram_unset passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram


async def test_fallback_when_use_ayugram_zero():
    """Когда USE_AYUGRAM=0, должен использоваться PyTgCalls."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Устанавливаем USE_AYUGRAM=0
        os.environ["USE_AYUGRAM"] = "0"

        # Проверяем что is_available() возвращает False
        from ayugram_adapter import is_available
        assert is_available() is False

        print("✅ test_fallback_when_use_ayugram_zero passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        elif "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]


async def test_fallback_when_use_ayugram_pytg():
    """Когда USE_AYUGRAM=pytg, должен использоваться PyTgCalls."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Устанавливаем USE_AYUGRAM=pytg
        os.environ["USE_AYUGRAM"] = "pytg"

        # Проверяем что is_available() возвращает False
        from ayugram_adapter import is_available
        assert is_available() is False

        print("✅ test_fallback_when_use_ayugram_pytg passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        elif "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]


async def test_no_ayugram_import_errors():
    """AyuGram импорты не должны вызывать ошибки когда USE_AYUGRAM не установлен."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Удаляем USE_AYUGRAM из окружения
        if "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]

        # Перезагружаем модуль для правильной инициализации AYUGRAM_AVAILABLE
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']

        # Импортируем модуль - не должно быть ошибок
        from ayugram_adapter import AyuGramAdapter, AYUGRAM_AVAILABLE, is_available

        # AYUGRAM_AVAILABLE должен быть False (без env var)
        # но модуль должен быть импортируем
        assert AYUGRAM_AVAILABLE is False
        assert is_available() is False

        # Создание адаптера должно работать
        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)
        assert adapter is not None

        print("✅ test_no_ayugram_import_errors passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        # Перезагружаем модуль для восстановления состояния
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']


async def test_ayugram_available_flag_reflects_env():
    """AYUGRAM_AVAILABLE флаг должен отражать состояние USE_AYUGRAM."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Тест 1: Без USE_AYUGRAM -> False
        if "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']

        from ayugram_adapter import AYUGRAM_AVAILABLE
        assert AYUGRAM_AVAILABLE is False

        # Тест 2: USE_AYUGRAM=0 -> False
        os.environ["USE_AYUGRAM"] = "0"
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']
        from ayugram_adapter import AYUGRAM_AVAILABLE as FLAG2
        assert FLAG2 is False

        print("✅ test_ayugram_available_flag_reflects_env passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        elif "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]
        # Перезагружаем модуль для восстановления состояния
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']


async def test_adapter_works_without_env_var():
    """AyuGramAdapter должен работать даже без USE_AYUGRAM."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Удаляем USE_AYUGRAM из окружения
        if "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]

        # Создаём и запускаем адаптер
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Метод start() должен работать
        await adapter.start()
        assert adapter._is_running is True

        # Метод stop() должен работать
        await adapter.stop()
        assert adapter._is_running is False

        print("✅ test_adapter_works_without_env_var passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram


async def test_backend_detection():
    """Проверка логики определения backend."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Helper function to reload module and get is_available
        def check_is_available(env_value):
            if env_value is None:
                if "USE_AYUGRAM" in os.environ:
                    del os.environ["USE_AYUGRAM"]
            else:
                os.environ["USE_AYUGRAM"] = env_value

            # Перезагружаем модуль для нового env var
            if 'ayugram_adapter' in sys.modules:
                del sys.modules['ayugram_adapter']

            from ayugram_adapter import is_available
            return is_available()

        # Тест 1: USE_AYUGRAM не установлен -> PyTgCalls
        result = check_is_available(None)
        assert result is False, "Without USE_AYUGRAM, should return False"

        # Тест 2: USE_AYUGRAM=0 -> PyTgCalls
        result = check_is_available("0")
        assert result is False, "With USE_AYUGRAM=0, should return False"

        # Тест 3: USE_AYUGRAM=pytg -> PyTgCalls
        result = check_is_available("pytg")
        assert result is False, "With USE_AYUGRAM=pytg, should return False"

        # Тест 4: USE_AYUGRAM=1 -> AyuGram
        result = check_is_available("1")
        assert result is True, "With USE_AYUGRAM=1, should return True"

        # Тест 5: USE_AYUGRAM=ayugram -> AyuGram
        result = check_is_available("ayugram")
        assert result is True, "With USE_AYUGRAM=ayugram, should return True"

        print("✅ test_backend_detection passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        elif "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]
        # Перезагружаем модуль для восстановления состояния
        if 'ayugram_adapter' in sys.modules:
            del sys.modules['ayugram_adapter']


async def test_fallback_integration():
    """Интеграционный тест: fallback работает при стриминге."""
    # Сохраняем текущее значение
    old_use_ayugram = os.environ.get("USE_AYUGRAM")

    try:
        # Устанавливаем USE_AYUGRAM=0 (PyTgCalls режим)
        os.environ["USE_AYUGRAM"] = "0"

        # Проверяем что AyuGramAdapter не активен через is_available
        from ayugram_adapter import is_available
        assert is_available() is False

        # AyuGramAdapter может быть создан, но не должен использоваться
        # когда is_available() возвращает False
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Адаптер создаётся, но при проверке is_available
        # код должен понять что нужно использовать PyTgCalls
        assert is_available() is False

        print("✅ test_fallback_integration passed")

    finally:
        # Восстанавливаем значение
        if old_use_ayugram is not None:
            os.environ["USE_AYUGRAM"] = old_use_ayugram
        elif "USE_AYUGRAM" in os.environ:
            del os.environ["USE_AYUGRAM"]


async def main():
    """Run all fallback tests."""
    print("=" * 60)
    print("PyTgCalls Fallback Tests")
    print("=" * 60)
    print()

    tests = [
        test_fallback_when_use_ayugram_unset,
        test_fallback_when_use_ayugram_zero,
        test_fallback_when_use_ayugram_pytg,
        test_no_ayugram_import_errors,
        test_ayugram_available_flag_reflects_env,
        test_adapter_works_without_env_var,
        test_backend_detection,
        test_fallback_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
