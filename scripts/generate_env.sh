#!/usr/bin/env bash
set -euo pipefail

TEMPLATE_FILE=".env.template"
ENV_FILE=".env"

# Use this script to create a .env from .env.template
# It will copy the template and optionally prompt for secrets

usage() {
  cat <<EOF
Usage: $0 [--non-interactive] [--random-secrets]

Options:
  --non-interactive   Copy template to .env without prompting
  --random-secrets     Replace JWT_SECRET with a securely generated value

The script will not overwrite an existing .env by default; use --force to replace.
EOF
}

NON_INTERACTIVE=false
RANDOM_SECRETS=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --non-interactive) NON_INTERACTIVE=true; shift ;;
    --random-secrets) RANDOM_SECRETS=true; shift ;;
    --force) FORCE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -f $TEMPLATE_FILE ]]; then
  echo "Template $TEMPLATE_FILE not found"
  exit 1
fi

if [[ -f $ENV_FILE && $FORCE = false ]]; then
  echo "$ENV_FILE already exists. Use --force to overwrite or delete it manually." >&2
  exit 1
fi

# Copy template
cp $TEMPLATE_FILE $ENV_FILE
chmod 600 $ENV_FILE || true

# Replace placeholders or prompt
if [[ $NON_INTERACTIVE = false ]]; then
  echo "--- Генерация .env из шаблона ---"
  while IFS= read -r line; do
    if [[ $line =~ ^[A-Z_]+=change_this_ ]]; then
      key=${line%%=*}
      current=${line#*=}
      if [[ $key = "JWT_SECRET" ]]; then
        read -r -p "Введите значение для $key (оставьте пустым для автогенерации): " val
        if [[ -z "$val" ]]; then
          val=$(openssl rand -base64 32)
          echo "Сгенерирован JWT_SECRET"
        fi
        # replace
        sed -i "s|^$key=.*|$key=$val|" $ENV_FILE
      elif [[ $key = "SESSION_STRING" ]]; then
        # skip, usually long and interactive
        echo "Пропускаем: $key — сгенерируйте с помощью generate_session.py и вставьте в .env" >&2
      fi
    fi
  done < <(grep -E "^[A-Z_]+=change_this_" $ENV_FILE || true)
fi

# optionally randomize secrets
if [[ $RANDOM_SECRETS = true ]]; then
  # generate secure JWT
  jwt=$(openssl rand -base64 32)
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$jwt|" $ENV_FILE
  echo "JWT_SECRET сгенерирован"
fi

echo "Готово: $ENV_FILE создан (права 600)"