#!/usr/bin/env bash
set -euo pipefail

# Smoke: проверка cache headers для фронтенда.
# Цель: исключить ситуацию, когда браузер держит старый index.html и продолжает грузить старые asset-хэши.
#
# Использование:
#   BASE_URL=https://sattva-streamer.top ./tests/smoke/test_frontend_cache_headers.sh
#   BASE_URL=http://127.0.0.1         ./tests/smoke/test_frontend_cache_headers.sh

BASE_URL="${BASE_URL:-https://sattva-streamer.top}"

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

info() {
  echo "[INFO] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Не найдено в PATH: $1"
}

require_cmd curl
require_cmd grep
require_cmd sed

fetch_headers() {
  local url="$1"
  # -sS: тихо, но с ошибками; -D -: заголовки в stdout; -o /dev/null: тело не нужно
  curl -sS -D - -o /dev/null "$url" | sed $'s/\r$//'
}

get_header_value() {
  local headers="$1"
  local header_name="$2"
  # Берём первое вхождение заголовка.
  echo "$headers" | grep -i "^${header_name}:" | head -n 1 | sed -E "s/^${header_name}:[[:space:]]*//I"
}

assert_contains_ci() {
  local haystack="$1"
  local needle="$2"
  echo "$haystack" | grep -qi "$needle" || fail "Ожидали подстроку '$needle' (case-insensitive), но не нашли"
}

info "BASE_URL=$BASE_URL"

root_headers="$(fetch_headers "$BASE_URL/")"
index_headers="$(fetch_headers "$BASE_URL/index.html")"

root_cc="$(get_header_value "$root_headers" "Cache-Control")"
index_cc="$(get_header_value "$index_headers" "Cache-Control")"

info "Cache-Control /:        ${root_cc:-<missing>}"
info "Cache-Control /index.html: ${index_cc:-<missing>}"

# index.html должен быть максимально 'anti-cache'
[[ -n "${index_cc:-}" ]] || fail "Нет заголовка Cache-Control для /index.html"
assert_contains_ci "$index_cc" "no-store"
assert_contains_ci "$index_cc" "no-cache"

# Для '/' тоже ожидаем anti-cache (SPA shell)
[[ -n "${root_cc:-}" ]] || fail "Нет заголовка Cache-Control для /"
assert_contains_ci "$root_cc" "no-store"
assert_contains_ci "$root_cc" "no-cache"

# Ассеты: immutable
# Берём из HTML первый попавшийся asset index-*.js или index-*.css.
html="$(curl -sS "$BASE_URL/index.html")"
asset_path="$(echo "$html" | grep -Eo "/assets/index-[^\"']+\\.(js|css)" | head -n 1 || true)"

if [[ -n "$asset_path" ]]; then
  asset_url="$BASE_URL$asset_path"
  asset_headers="$(fetch_headers "$asset_url")"
  asset_cc="$(get_header_value "$asset_headers" "Cache-Control")"
  info "Asset URL: $asset_url"
  info "Cache-Control asset: ${asset_cc:-<missing>}"

  [[ -n "${asset_cc:-}" ]] || fail "Нет заголовка Cache-Control для asset ($asset_url)"
  assert_contains_ci "$asset_cc" "immutable"
else
  info "Не удалось извлечь asset путь из index.html (пропускаю проверку immutable для assets)"
fi

info "OK: cache headers выглядят корректно"
