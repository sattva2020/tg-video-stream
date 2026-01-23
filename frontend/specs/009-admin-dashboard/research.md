# Research: Admin Dashboard Implementation

**Feature**: `009-admin-dashboard`
**Date**: 2025-11-24

## Decisions

### 1. Component Separation
**Decision**: Split the dashboard into `AdminDashboard` and `UserDashboard` components.
**Rationale**: 
- **Separation of Concerns**: Admin logic (user management, stream control) is distinct from user logic (profile view).
- **Security**: Easier to ensure admin-only components are not rendered for regular users.
- **Maintainability**: Smaller, focused components are easier to test and maintain.
**Alternatives Considered**: 
- *Single Dashboard with Conditionals*: Rejected due to growing complexity and "spaghetti code" risk as features are added.

### 2. UI Library
**Decision**: Use `HeroUI` (Tailwind-based components) for tabs, cards, and tables.
**Rationale**:
- **Consistency**: Matches the existing design language of the application.
- **Speed**: Pre-built components speed up development.
- **Theming**: Built-in support for light/dark modes via Tailwind classes.

### 3. State Management
**Decision**: Use local component state (`useState`) for dashboard data (users list, stats).
**Rationale**:
- **Simplicity**: No need for global state (Redux/Zustand) for data that is only used in one view.
- **Freshness**: Data is fetched on mount and refreshed on actions (approve/reject), ensuring up-to-date information.

## Unknowns & Clarifications

- **Stream Status API**: Currently simulated. Need to integrate with actual streamer service status in future iterations.
- **Pagination**: Current implementation fetches all users. Will need pagination for >1000 users (Future Work).
