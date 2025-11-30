#!/usr/bin/env bash
# Prevent committing .env by rejecting commits that stage it
# To use: make the script executable and add a pre-commit hook that runs it

staged=$(git diff --cached --name-only --diff-filter=ACMR)
for f in $staged; do
  if [[ "$f" = ".env" || "$f" = "./.env" || "$f" =~ ".env" ]]; then
    echo "ERROR: Attempt to commit '.env' — secrets should not be committed." >&2
    echo "Use .env.template and scripts/generate_env.sh. Add .env to .gitignore." >&2
    exit 1
  fi
done
exit 0
