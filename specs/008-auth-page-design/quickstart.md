# Quickstart: Auth Page Design

## 1. Подготовка окружения

```bash
cd frontend
npm install
npm install aceternity-ui magic-ui hero-ui react-three-fiber @react-three/drei
```

- Скопируйте `template.env` → `.env` и убедитесь, что `VITE_API_URL` указывает на локальный backend.
- Для Lighthouse нужен Chrome 120+, убедитесь что `npx lighthouse` доступен (входит в devDependencies).

## 2. Запуск разработки

```bash
npm run dev
```

- Тогглер светлой/тёмной темы доступен в правом верхнем углу страницы авторизации.
- Для проверки fallback WebGL выключите аппаратное ускорение или добавьте `?forceStatic=1`.

## 3. Тесты и проверки

```bash
npm run test:unit        # Vitest снапшоты компонентов
npx playwright test      # Desktop + 320px сценарии авторизации и ошибок
npm run lighthouse:auth  # Lighthouse CI (desktop preset)
```

Logs от тестов складываем в `.internal/frontend-logs/` (в `.gitignore`). Перед PR запустите `npm run docs:validate && npm run docs:report`.
