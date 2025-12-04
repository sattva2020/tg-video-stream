# Feature Specification: Role-Based UI/UX Fixes

**Feature Branch**: `018-role-ui-fixes`  
**Created**: 2025-12-02  
**Status**: Draft  
**Input**: User description: "Fix role-based UI/UX issues: MODERATOR dashboard access, SUPERADMIN navigation, /admin routing, OPERATOR role definition"

---

## Контекст

Данная спецификация основана на результатах UI/UX аудита панелей администрирования (`docs/UI_UX_AUDIT_ROLES.md`). Выявлены критические баги в логике определения ролей пользователей, влияющие на:
- Доступ модераторов к административным функциям
- Навигацию суперадминов
- Маршрутизацию /admin
- Полное отсутствие функционала для роли OPERATOR

### Текущая матрица ролей (проблемы):

| Роль | Ожидаемое поведение | Фактическое поведение | Статус |
|------|---------------------|----------------------|--------|
| **SUPERADMIN** | AdminDashboardV2 + полная навигация | Навигация показывает меню только для ADMIN | ��� Баг |
| **ADMIN** | AdminDashboardV2 + админ-навигация | Работает корректно | ✅ OK |
| **MODERATOR** | AdminDashboardV2 (ограниченно) | Видит UserDashboard | ��� Баг |
| **OPERATOR** | Управление стримами | Нет UI совсем | ��� Не реализовано |
| **USER** | UserDashboard | Работает корректно | ✅ OK |

---

## User Scenarios & Testing

### User Story 1 — Модератор получает доступ к административной панели (Priority: P0)

Модератор должен видеть AdminDashboardV2 при входе в систему, а не базовую панель пользователя. Это критический баг, блокирующий работу модераторов.

**Why this priority**: Модераторы не могут выполнять свои рабочие обязанности — просматривать статистику, мониторить стримы, управлять плейлистом. Это полностью блокирует роль.

**Independent Test**: Войти в систему с аккаунтом модератора и проверить, что отображается AdminDashboardV2 с соответствующими правами (без раздела Users).

**Acceptance Scenarios**:

1. **Given** пользователь с ролью MODERATOR авторизован, **When** он переходит на /dashboard, **Then** отображается AdminDashboardV2
2. **Given** модератор на AdminDashboardV2, **When** он просматривает вкладки, **Then** вкладка "Users" отсутствует или неактивна
3. **Given** модератор на AdminDashboardV2, **When** он нажимает "QuickActions", **Then** недоступны действия управления пользователями

#### Implementation Notes

- MODERATOR видит только две вкладки: `overview` (статистика + ActivityTimelineLive) и `stream` (StreamStatusCard + управление трансляцией). Вкладка `users` и компонент `UserManagementPanel` исключаются из дерева React.
- Быстрые действия для модератора ограничены контролем стрима (`stream-toggle`, `restart`) и управлением плейлистом (`playlist`). Кнопки `users` и `settings` скрываются, чтобы исключить управление доступом и системные настройки.
- При попытке вызвать запрещённое действие (например, прямой переход на `/admin/pending` или вызов `onOpenUsers`) отображается toast `admin.restrictedAction` (i18n RU/EN/UK/ES) с текстом «Недостаточно прав для выполнения действия».
- Компонент использует существующие skeleton-состояния StatCard/QuickActions, поэтому во время загрузки данных у модератора отображаются те же placeholders, что и у администратора.

---

### User Story 2 — Суперадмин видит полную навигацию (Priority: P0)

Суперадмин должен видеть все пункты админ-меню в навигации. Сейчас проверяется только роль ADMIN, игнорируя SUPERADMIN.

**Why this priority**: SUPERADMIN — высшая роль в системе, но имеет ограниченный доступ к навигации. Критический баг безопасности и функциональности.

**Independent Test**: Войти как SUPERADMIN и проверить, что все админ-пункты меню (Dashboard, Pending Users, Monitoring, Settings) видны и кликабельны.

**Acceptance Scenarios**:

1. **Given** пользователь с ролью SUPERADMIN авторизован, **When** он видит DesktopNav, **Then** все пункты с `adminOnly: true` отображаются
2. **Given** SUPERADMIN в мобильной версии, **When** он открывает MobileNav, **Then** все админ-пункты доступны
3. **Given** SUPERADMIN авторизован, **When** он переходит по админ-ссылкам, **Then** все страницы открываются без ошибок

#### Navigation Definition

| Path | Ключ локализации | Иконка (lucide-react) | adminOnly | moderatorAllowed | Видимость |
|------|------------------|-----------------------|-----------|------------------|-----------|
| `/dashboard` | `nav.dashboard` | `Home` | ❌ | N/A | Все роли |
| `/channels` | `nav.channels` | `Tv` | ❌ | N/A | Все роли |
| `/playlist` | `nav.playlist` | `ListMusic` | ❌ | N/A | Все роли |
| `/schedule` | `nav.schedule` | `CalendarDays` | ❌ | N/A | Все роли |
| `/admin` | `nav.admin` | `Settings` | ✅ | ❌ | ADMIN, SUPERADMIN |
| `/admin/pending` | `nav.pendingUsers` | `Users` | ✅ | ❌ | ADMIN, SUPERADMIN |
| `/admin/monitoring` | `nav.monitoring` | `Activity` | ✅ | ✅ | ADMIN, SUPERADMIN, MODERATOR |
| `/settings` | `nav.settings` | `Settings` | ❌ | N/A | Все роли |

- DesktopNav и MobileNav используют общий helper `filterNavItems()` из `utils/navigationHelpers.ts`, что гарантирует идентичную фильтрацию на любых устройствах.
- Активные элементы используют стиль `bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]`, неактивные — muted фон. SUPERADMIN и ADMIN получают один и тот же визуальный язык.
- Каждый `Link` должен сохранять видимый focus state (`focus-visible:ring-2 ring-offset-2`) и работать по клавиатурным клавишам Enter/Space. Это покрывает требования доступности и гарантирует, что навигация работоспособна без мыши.

---

### User Story 3 — Корректная маршрутизация /admin (Priority: P1)

Путь /admin должен вести на современный AdminDashboardV2, а не на устаревший Dashboard.tsx. Старый компонент должен быть удалён.

**Why this priority**: Дублирование кода создаёт путаницу и технический долг. Пользователи могут случайно попасть на старый интерфейс.

**Independent Test**: Открыть /admin напрямую по URL и убедиться, что отображается AdminDashboardV2.

**Acceptance Scenarios**:

1. **Given** админ переходит по URL /admin, **When** страница загружается, **Then** отображается AdminDashboardV2
2. **Given** существует файл `pages/admin/Dashboard.tsx`, **When** выполняется код ревью, **Then** файл отсутствует (удалён)
3. **Given** в App.tsx есть роут /admin, **When** проверяется код, **Then** он указывает на AdminDashboardV2

#### Routing Notes

- `<Route path="/admin" element={<Navigate replace to="/dashboard" />} />` имитирует временный HTTP 302. Компонент `Navigate` обязательно вызывается с `replace`, чтобы история браузера не накапливала устаревший путь.
- Редирект применяется только к точному `/admin`. Все подмаршруты (`/admin/pending`, `/admin/monitoring`) остаются рабочими и не перебиваются.
- Неавторизованные пользователи проходят стандартный цикл `ProtectedRoute`: редирект на `/login`, далее после успешной аутентификации — на `/dashboard` согласно `returnUrl`.
- Старый компонент `pages/admin/Dashboard.tsx` удаляется из репозитория, чтобы исключить случайное использование или бандлинг.

---

### User Story 4 — Оператор видит панель управления стримами (Priority: P2)

Роль OPERATOR определена в системе, но не имеет UI. Оператор должен видеть упрощённый дашборд с контролем стримов.

**Why this priority**: Роль не критична для текущего функционирования, но её доработка завершит систему ролей. Бизнес может начать использовать операторов.

**Independent Test**: Войти как OPERATOR и увидеть панель с кнопками запуска/остановки стрима и информацией о текущем состоянии.

**Acceptance Scenarios**:

1. **Given** пользователь с ролью OPERATOR авторизован, **When** он переходит на /dashboard, **Then** отображается панель с контролом стрима
2. **Given** оператор на дашборде, **When** он видит интерфейс, **Then** доступны кнопки ▶️ Запуск, ⏹️ Стоп, ��� Перезапуск
3. **Given** оператор на дашборде, **When** он пытается перейти к управлению пользователями, **Then** доступ запрещён

#### OperatorDashboard Layout

- Верхняя область повторяет StreamStatusCard с живым индикатором, uptime и состоянием соединения. Компонент обновляется каждые 5 секунд и слушает WebSocket `stream.status`.
- Ниже располагается карточка управления трансляцией с тремя кнопками. Каждая кнопка использует те же градиенты, что и QuickActions в AdminDashboardV2, что закрывает требование консистентности (CHK042).
- Правая колонка (≥1024px) показывает компактный ActivityTimeline (5 последних событий) и карточку очереди. На мобильных блоки отображаются вертикально.
- В случае ошибки API (`startStream`, `stopStream`, `restartStream`) оператор видит toast `admin.stream*Error` и кнопку «Повторить». Журнал фиксирует ошибки с таймстампом.
- Попытка открыть `/admin/pending`/`/admin` показывает компонент HeroUI Alert «Нет доступа». Оператор перенаправляется обратно на `/dashboard` через 3 секунды.

---

### User Story 5 — UserDashboard показывает полезный контент (Priority: P3)

Пустой Welcome Card и минимум действий делают UserDashboard неинформативным. Добавить полезный контент.

**Why this priority**: Улучшение UX, но не критично для функционирования системы. Повышает вовлечённость пользователей.

**Independent Test**: Войти как обычный пользователь и увидеть приветственный контент, советы, историю прослушивания.

**Acceptance Scenarios**:

1. **Given** обычный пользователь на /dashboard, **When** он видит Welcome Card, **Then** отображается полезный контент (статус аккаунта, советы)
2. **Given** пользователь просматривает дашборд, **When** он ищет быстрые действия, **Then** доступно более одной ссылки (Каналы, Настройки, Помощь)
3. **Given** пользователь просматривает дашборд, **When** он видит Welcome Card, **Then** отображаются советы по использованию системы

#### UserDashboard Enhancements

- Welcome Card показывает блок статуса (верификация email, привязка Telegram, роль пользователя) и дату последнего входа. Ниже список «Советы по использованию», минимум три строки: подключить Telegram, проверять расписание, управлять каналами.
- Быстрые действия включают минимум три кнопки: `Manage Channels (/channels)`, `Account Settings (/settings)`, `Help Center (/docs/help)` с иконками `Tv`, `Settings`, `HelpCircle`.
- Макет: на десктопе Welcome Card занимает всю ширину, за ним следует сетка 3×1 быстрых действий и блок истории/советов. На мобильных элементы идут вертикально.
- Все строки добавляются в локали ru/en/uk/es (ключи `user.welcome.status`, `user.tips.*`, `user.quickActions.*`).

---

### Edge Cases

- Что происходит при смене роли пользователя во время активной сессии?
- Как система ведёт себя при неизвестной роли (fallback)?
- Что видит пользователь с ролью NULL (возможно при ошибке в БД)?
- Как ведёт себя навигация при одновременном наличии нескольких ролей (если такое возможно)?

---

## Requirements

### Functional Requirements

- **FR-001**: Система ДОЛЖНА показывать AdminDashboardV2 пользователям с ролями ADMIN, SUPERADMIN, MODERATOR
- **FR-002**: Система ДОЛЖНА фильтровать навигацию для ролей ADMIN и SUPERADMIN одинаково (оба видят все админ-пункты)
- **FR-003**: Система ДОЛЖНА ограничивать доступ MODERATOR к функциям управления пользователями в AdminDashboardV2
- **FR-004**: Роут /admin ДОЛЖЕН перенаправлять на /dashboard, где пользователь увидит соответствующий дашборд по роли
- **FR-005**: Система ДОЛЖНА предоставить OPERATOR панель с контролом стримов (запуск/стоп/перезапуск)
- **FR-006**: Навигация ДОЛЖНА поддерживать атрибут `moderatorAllowed` для гранулярного контроля доступа
- **FR-007**: UserDashboard ДОЛЖЕН показывать полезный контент в Welcome Card
- **FR-008**: Устаревший компонент `pages/admin/Dashboard.tsx` ДОЛЖЕН быть удалён из кодовой базы
- **FR-009**: Система ДОЛЖНА корректно обрабатывать fallback для неизвестных ролей (показывать UserDashboard)

### Consistency Requirements

- Все проверки ролей выполняются через `utils/roleHelpers.ts` (isAdminLike, getDashboardComponent, canControlStream). Прямые сравнения `user?.role === ...` запрещены.
- Навигация (DesktopNav, MobileNav) использует `filterNavItems()` и общую структуру данных `navItems`, чтобы не появлялись рассинхронизации.
- Управление стримом в AdminDashboardV2 и OperatorDashboard использует одинаковые стили (градиентные кнопки, анимации), что сохраняет визуальное восприятие.

### Key Entities

- **User Role**: Определяет уровень доступа (SUPERADMIN, ADMIN, MODERATOR, OPERATOR, USER)
- **Dashboard**: Главная панель, варьируется по роли пользователя
- **Navigation Item**: Пункт меню с атрибутами `adminOnly`, `moderatorAllowed`
- **Permission Set**: Набор разрешённых действий для каждой роли

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Пользователи с ролями MODERATOR, ADMIN, SUPERADMIN видят AdminDashboardV2 при входе в 100% случаев
- **SC-002**: SUPERADMIN видит все админ-пункты навигации (минимум 4 пункта: Dashboard, Pending, Monitoring, Settings)
- **SC-003**: OPERATOR может запустить/остановить стрим через свою панель (время выполнения действия < 3 секунды)
- **SC-004**: Количество дублирующих Dashboard-компонентов сокращается с 2 до 1
- **SC-005**: UserDashboard содержит минимум 3 быстрых действия (Каналы, Настройки, ещё одно)
- **SC-006**: Все 5 ролей системы имеют определённое UI-поведение (0 ролей без функционала)

---

## Assumptions

- Роли пользователей хранятся в поле `user.role` и определены enum `UserRole`
- AdminDashboardV2 — актуальный компонент, старый Dashboard.tsx — устаревший
- sqladmin (/admin бэкенд) остаётся отдельной системой и не затрагивается в этой фиче
- Изменение роли пользователя требует перелогина для применения (текущее поведение)
- Hero UI, Framer Motion и Tailwind — основной стек компонентов
- При подтверждённой смене роли backend возвращает признак `role_changed`, а frontend показывает toast «Роль обновлена, выполните повторный вход» и завершает сессию (Given CHK050).

### UI States & Error Handling

- `AdminDashboardV2`, `OperatorDashboard` и `UserDashboard` показывают skeleton-состояния до загрузки данных и graceful error cards с кнопкой «Повторить» при сбоях API.
- Отсутствие `user` или `user.role` приводит к временной загрузочной заставке и fallback к `UserRole.USER` после истечения тайм-аута 1s. Событие логируется в Sentry (tag `role=fallback`).
- Все ошибки API управления стримом транслируются в toast с i18n строками `admin.stream*Error`; повторный вызов разблокирован сразу после ответа.
- Потеря WebSocket соединения (StreamStatusCard/SystemHealthLive) отображает баннер «Подключение потеряно» с кнопкой `Повторить подключение`.
- Неавторизованный доступ к административным роутам возвращает компонент `ForbiddenView` (HTTP 403) и редиректит на `/dashboard` через 3 секунды.
- Истечение JWT (401) приводит к автоматическому `logout()` и всплывающему сообщению «Сессия истекла, войдите снова». После входа пользователь возвращается на изначальный маршрут.
- Если обнаружены одновременные сессии с разными ролями (разные устройства), backend присылает `role_changed`, а frontend принудительно обновляет токен и просит перелогин.

### Navigation & Role Flows

| Роль | Дашборд | Разрешённые вкладки | adminOnly навигация | Быстрые действия |
|------|---------|---------------------|---------------------|------------------|
| SUPERADMIN | AdminDashboardV2 | overview, users, stream | /admin, /admin/pending, /admin/monitoring | Все 5 действий |
| ADMIN | AdminDashboardV2 | overview, users, stream | /admin, /admin/pending, /admin/monitoring | Все 5 действий |
| MODERATOR | AdminDashboardV2 | overview, stream | /admin/monitoring | Stream toggle, Restart, Playlist |
| OPERATOR | OperatorDashboard | stream, queue | Нет | Stream toggle, Restart |
| USER | UserDashboard | welcome, history | Нет | Channels, Settings, Help |

### Non-Functional Requirements

- **i18n**: новые строки обязательны в 4 локалях (ru/en/uk/es). PR блокируется без обновления `frontend/src/i18n/locales/*`.
- **Темы**: все блоки используют CSS-переменные `--color-*`, тестируются в светлой и тёмной теме.
- **Accessibility**: focus states и aria-метки обязательны для навигации, кнопок стрима и быстрых действий. MobileNav Drawer должен быть полностью управляем с клавиатуры.
- **Responsive**: OperatorDashboard и UserDashboard тестируются на брейкпоинтах <768px / 768-1024px / >1024px. Макеты описаны выше и фиксируют расположение карточек.
- **Performance**: WebSocket переподключается с экспоненциальной задержкой (5s, 10s, 20s) чтобы избежать спама.

### Scenario Coverage

- **Happy path**: для каждой роли описан сценарий `login → /dashboard → соответствующий дашборд`, Quickstart содержит чеклист.
- **Navigation flow**: DesktopNav и MobileNav используют общий helper, поэтому сценарий SUPERADMIN → MobileNav равен DesktopNav.
- **Theme & device switching**: QA проверяет переключатель темы и навигацию на мобильном/десктопе в рамках smoke-теста.
