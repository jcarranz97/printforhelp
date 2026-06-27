#!/bin/sh
set -e

# Replace the placeholder baked into the bundle at build time with the actual
# backend API URL supplied at container startup via NEXT_PUBLIC_API_URL.
PLACEHOLDER="http://PRINTFORHELP_API_URL_PLACEHOLDER"
ACTUAL="${NEXT_PUBLIC_API_URL:-http://localhost:8100/api/v1}"

find /app/.next -type f -name "*.js" \
  -exec sed -i "s|${PLACEHOLDER}|${ACTUAL}|g" {} \;

exec "$@"
