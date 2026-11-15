#!/usr/bin/env bash
# Nightly backup of an Athena deployment to S3: the database (accounts,
# profiles, jobs, answers, tokens) and the uploaded resume files.
# Run on the server from cron — see DEPLOYMENT.md, "Backups".
#
#   BACKUP_BUCKET=my-bucket bash scripts/backup.sh
#
# Needs the AWS CLI on the host and permission to write to the bucket
# (an IAM role on the instance; no keys are stored here).
set -euo pipefail

: "${BACKUP_BUCKET:?Set BACKUP_BUCKET to the S3 bucket name}"
DB_CONTAINER="${DB_CONTAINER:-athena-db-1}"
RESUMES_VOLUME="${RESUMES_VOLUME:-athena_resumes}"
PREFIX="${BACKUP_PREFIX:-athena}"

stamp="$(date -u +%Y-%m-%dT%H%MZ)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Dump to a file first, so a failed dump is never uploaded as if it were
# a good one. Only the two schemas that hold Athena's data: `public` (the
# app) and `auth` (accounts). The rest of the database is the image's own
# scaffolding, recreated on a fresh start.
docker exec "$DB_CONTAINER" pg_dump -U supabase_admin -d postgres \
  --format=custom --schema=public --schema=auth > "$tmp/db.dump"

docker run --rm -v "$RESUMES_VOLUME":/data:ro alpine \
  tar -czf - -C /data . > "$tmp/resumes.tar.gz"

aws s3 cp --only-show-errors "$tmp/db.dump" "s3://$BACKUP_BUCKET/$PREFIX/$stamp/db.dump"
aws s3 cp --only-show-errors "$tmp/resumes.tar.gz" "s3://$BACKUP_BUCKET/$PREFIX/$stamp/resumes.tar.gz"

echo "$(date -u +%FT%TZ) backup ok: s3://$BACKUP_BUCKET/$PREFIX/$stamp/ ($(du -h "$tmp/db.dump" | cut -f1) db, $(du -h "$tmp/resumes.tar.gz" | cut -f1) resumes)"
