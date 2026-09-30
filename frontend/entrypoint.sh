#!/bin/sh
set -eu

AUTH_FILE="/etc/caddy/auth.caddy"

if [ -n "${BASIC_AUTH_USER:-}" ] && [ -n "${BASIC_AUTH_HASH:-}" ]; then
    echo "Enabling HTTP Basic Authentication for user '${BASIC_AUTH_USER}'"
    cat <<EOF > "$AUTH_FILE"
basic_auth {
	${BASIC_AUTH_USER} ${BASIC_AUTH_HASH}
}
EOF
else
    echo "HTTP Basic Authentication is disabled."
    cat <<EOF > "$AUTH_FILE"
# HTTP Basic Authentication disabled
EOF
fi

echo "Starting Caddy server..."
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
