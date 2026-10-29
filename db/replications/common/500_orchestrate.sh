#!/bin/bash
set -e

if [ -d "/docker-entrypoint-replications" ]; then
    for f in /docker-entrypoint-replications/*.sql; do
        if [ -f "$f" ]; then
            echo "$0: running $f"
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
        fi
    done
fi