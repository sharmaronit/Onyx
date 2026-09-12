#!/bin/sh
set -eu
BACKUP_DIR="${ONYX_BACKUP_DIR:-/var/backups/onyx}"
COMPOSE_DIR="${ONYX_COMPOSE_DIR:-/opt/onyx/deploy}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose -f "$COMPOSE_DIR/compose.yaml" cp api:/var/lib/onyx/onyx.db "$BACKUP_DIR/onyx-$STAMP.db"
gzip "$BACKUP_DIR/onyx-$STAMP.db"
find "$BACKUP_DIR" -type f -name 'onyx-*.db.gz' -mtime +30 -delete
