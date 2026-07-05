#!/bin/sh
set -e

# next.config's rewrites() are evaluated at BUILD time and frozen into the
# build manifests (routes-manifest.json) as well as the JS bundles, so the
# backend URLs are baked in as placeholders and swapped for the real runtime
# values here at container startup.

# Browser-facing API URL (client bundles): the public placeholder, replaced
# with the public NEXT_PUBLIC_API_URL the browser can reach.
PUBLIC_PLACEHOLDER="http://PRINTFORHELP_API_URL_PLACEHOLDER"
PUBLIC_ACTUAL="${NEXT_PUBLIC_API_URL:-http://localhost:8100/api/v1}"

# In-network origin the /media proxy targets. This proxy runs server-side
# (inside this container), so it must hit the backend's in-network origin,
# not the browser URL. Replace the internal placeholder with API_URL_INTERNAL
# stripped of its /api/v1 suffix (e.g. http://backend:8000).
INTERNAL_PLACEHOLDER="http://PRINTFORHELP_INTERNAL_ORIGIN_PLACEHOLDER"
INTERNAL_ACTUAL=$(printf '%s' "${API_URL_INTERNAL:-http://backend:8000/api/v1}" \
  | sed 's|/api/v1/*$||')

# Patch both JS bundles and JSON manifests (the media rewrite lives in
# routes-manifest.json, which the previous *.js-only pass never touched).
find /app/.next -type f \( -name "*.js" -o -name "*.json" \) \
  -exec sed -i \
    -e "s|${PUBLIC_PLACEHOLDER}|${PUBLIC_ACTUAL}|g" \
    -e "s|${INTERNAL_PLACEHOLDER}|${INTERNAL_ACTUAL}|g" {} \;

exec "$@"
