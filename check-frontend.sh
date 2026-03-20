#!/usr/bin/env bash
# Frontend code quality checks
# Usage: ./check-frontend.sh [--fix]

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"

cd "$FRONTEND_DIR"

# Install deps if node_modules is missing
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

if [ "${1:-}" = "--fix" ]; then
  echo ">>> Formatting frontend files with Prettier..."
  npx prettier --write "**/*.{js,html,css}"
  echo "Done. All files formatted."
else
  echo ">>> Checking formatting with Prettier..."
  npx prettier --check "**/*.{js,html,css}"

  echo ">>> Linting JavaScript with ESLint..."
  npx eslint script.js

  echo "All frontend quality checks passed."
fi
