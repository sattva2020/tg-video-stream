#!/bin/bash
# Скрипт для проверки исправления i18n

echo "🔍 Проверка исправления i18n..."
echo ""

# 1. Проверка файловой структуры
echo "1️⃣ Проверка файловой структуры:"
if [ -f "frontend/src/i18n.backup.ts" ]; then
    echo "   ✅ Старый файл переименован: i18n.backup.ts существует"
else
    echo "   ❌ Проблема: i18n.backup.ts не найден"
fi

if [ -f "frontend/src/i18n/index.ts" ]; then
    echo "   ✅ Новый файл найден: i18n/index.ts существует"
else
    echo "   ❌ Проблема: i18n/index.ts не найден"
fi

if [ -f "frontend/src/components/debug/I18nDebugPanel.tsx" ]; then
    echo "   ✅ Компонент отладки создан: I18nDebugPanel.tsx"
else
    echo "   ❌ Проблема: I18nDebugPanel.tsx не найден"
fi

echo ""

# 2. Проверка импорта в main.tsx
echo "2️⃣ Проверка импорта в main.tsx:"
if grep -q "import './i18n/index'" frontend/src/main.tsx; then
    echo "   ✅ Импорт исправлен: import './i18n/index'"
elif grep -q "import './i18n'" frontend/src/main.tsx; then
    echo "   ⚠️  Найден старый импорт: import './i18n' (может быть проблема)"
else
    echo "   ❌ Импорт i18n не найден в main.tsx"
fi

echo ""

# 3. Проверка импорта I18nDebugPanel в App.tsx
echo "3️⃣ Проверка импорта I18nDebugPanel в App.tsx:"
if grep -q "I18nDebugPanel" frontend/src/App.tsx; then
    echo "   ✅ I18nDebugPanel импортирован в App.tsx"
else
    echo "   ❌ I18nDebugPanel не найден в App.tsx"
fi

echo ""

# 4. Проверка .gitignore
echo "4️⃣ Проверка .gitignore:"
if grep -q "i18n.backup.ts" frontend/.gitignore; then
    echo "   ✅ i18n.backup.ts добавлен в .gitignore"
else
    echo "   ⚠️  i18n.backup.ts не найден в .gitignore (рекомендуется добавить)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ Следующие шаги:"
echo ""
echo "1. Перезапустите frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "2. Откройте браузер: http://localhost:3000"
echo ""
echo "3. В правом нижнем углу должна появиться панель отладки i18n"
echo ""
echo "4. Проверьте переводы на странице админ-панели"
echo ""
echo "5. Попробуйте переключить языки (RU/EN/UK/ES)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
