#!/bin/bash
set -e

if [ -d "/docker-entrypoint-replications" ]; then
    for f in /docker-entrypoint-replications/*; do
        case "$f" in
            *.sh)  echo "$0: running $f"; chmod +x "$f"; . "$f" ;;
            *.sql) echo "$0: running $f"; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f" ;;
            *)     echo "$0: ignoring $f" ;;
        esac
    done
fi