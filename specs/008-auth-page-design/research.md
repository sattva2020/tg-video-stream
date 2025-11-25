# Research: Auth Page Design

## Decision: Использовать сочетание Aceternity UI, Magic UI и Hero UI

- **Rationale**: библиотеки дают готовые стеклянные карточки, stat-blocks, Command Palette и Toast, визуально поддерживают космическую тему и работают поверх Tailwind, сохраняя локализацию.
- **Alternatives considered**: `shadcn/ui` (нет нужных 3D/neo-brutalist компонентов), Radix + кастомные стили (дольше и требует дизайн-ресурсов).

## Decision: Ленивый рендер 3D-сцены + статический fallback ZenScene

- **Rationale**: форма авторизации остаётся интерактивной при TTI < 2 сек, выполняя SC-003 и EC-001/002; WebGL можно отключить и показать SVG.
- **Alternatives considered**: единственный WebGL фон (блокирует загрузку), полностью статичный фон (не отражает «современный» UI).

## Decision: Ввести дизайн-токены (ink/parchment + LandingSans/Serif) через CSS custom properties и Tailwind theme

- **Rationale**: FR-001..FR-003 требуют единообразной палитры; токены переиспользуются компонентами UI-библиотек и 3D-сценой.
- **Alternatives considered**: локальные inline-стили (дублирование значений), только Tailwind config без CSS переменных (невозможно переиспользовать в ThreeJS).

## Decision: Тестировать responsive и ошибки через Playwright + Vitest + Lighthouse

- **Rationale**: Playwright сценарии (desktop + 320px) подтверждают US2/SC-004, Vitest снапшоты покрывают стили ошибок (US3), Lighthouse CLI проверяет доступность >90.
- **Alternatives considered**: ручное тестирование (неповторяемо), Storybook визуальные тесты (сложнее пайплайн, избыточно для одной страницы).

## Decision: Реализовать две темы (светлая/тёмная) через CSS custom properties + prefers-color-scheme + toggle

- **Rationale**: новая директива требует явного переключателя; custom properties позволяют переиспользовать переменные в React Three Fiber и UI библиотеках, а `prefers-color-scheme` автоматически подстраивает тему по умолчанию.
- **Alternatives considered**: единственная светлая тема (не выполняет требование), независимые SCSS-файлы (дублирование и усложнение поддержки).
