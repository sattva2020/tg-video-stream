# NGINX_INDEX_HTML_NO_STORE_CACHE_FIX

**Дата:** 21.12.2025  
**Компонент:** Nginx / Frontend delivery (SPA)  
**Тип:** Infra / UX (устранение эффекта «старой версии» после релиза)

## 🔴 Проблема
Иногда после корректного релиза фронтенда пользователь визуально видит «старую» версию интерфейса. Типичный симптом: на сервере уже лежит новый `frontend/dist`, но браузер продолжает использовать ранее закэшированный `index.html` и, как следствие, тянет старые хэшированные ассеты.

## 🔄 Шаги воспроизведения
1. Задеплоить новый релиз фронтенда (Vite build с новыми хэшами в `/assets/`).
2. Открыть сайт в браузере, где ранее уже была открыта админка.
3. Фактическое поведение:
   - UI выглядит как «до релиза».
   - В DevTools → Network можно увидеть загрузку старых `index-*.js`/`index-*.css`.

## 🔍 Корневая причина
`Cache-Control: no-cache` для `/` и/или `/index.html` в некоторых сценариях всё ещё допускает хранение HTML в кэше (с последующей потенциальной выдачей из disk cache), что приводит к рассинхронизации: HTML старый → ссылки на ассеты старые.

## ✅ Решение
Усилены anti-cache заголовки для SPA shell:
- для `/index.html` выставлен строгий режим: `no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0` + `Pragma: no-cache` + `Expires: 0`;
- для `/` (proxy-вариант) добавлена перестраховка теми же заголовками.

Смысл: `index.html` должен **никогда** не сохраняться, а `/assets/` остаётся `immutable` (это безопасно, т.к. ассеты хэшированы).

Важно: чтобы `immutable` гарантированно доходил до клиента даже через внешние прокси/CDN, для `/assets/` используется **один** заголовок `Cache-Control` (без директивы `expires`, которая может создавать дублирующий `Cache-Control: max-age=...`).

## 📁 Изменённые файлы
- [config/nginx/sattva-streamer](../../config/nginx/sattva-streamer) — добавлен `location = /index.html` с `no-store`, убран слабый `no-cache` из SPA fallback.
- [config/nginx/sattva-streamer.conf](../../config/nginx/sattva-streamer.conf) — синхронизация правил для proxy-режима (точечный `location = /index.html` + перестраховка в `/`).
- [tests/smoke/test_frontend_cache_headers.sh](../../tests/smoke/test_frontend_cache_headers.sh) — smoke-проверка заголовков кэширования.

## 🧪 Тестирование
### Локально / на VPS
1. Проверить заголовки:
   - `BASE_URL=https://sattva-streamer.top ./tests/smoke/test_frontend_cache_headers.sh`
2. Ручная проверка:
   - DevTools → Network → убедиться, что `/index.html` отдаётся с `Cache-Control: ... no-store ...`.

## 🚀 Статус
- [x] Исправление реализовано в репозитории
- [x] Применено на VPS (`nginx -t && systemctl reload nginx`)
- [x] Протестировано на VPS (`BASE_URL=https://sattva-streamer.top ./tests/smoke/test_frontend_cache_headers.sh`)
