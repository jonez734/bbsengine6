#!/usr/bin/env bash
# run-migrations.sh -- apply bbsengine6's SQL migrations to an install database.
#
# Lists the migration files in sql/ (or the ones you name), then runs each one with psql,
# in its own transaction, in order. Stops at the first error. Dry run by default: nothing
# is applied unless you pass --apply.
#
# Usage:
#   scripts/run-migrations.sh --db zoid6 --user zoid6            # dry run (lists plan)
#   scripts/run-migrations.sh --db zoid6 --user zoid6 --apply    # apply all, in order
#   scripts/run-migrations.sh --db zoid6 --apply owner_zoid6_migration.sql
#   scripts/run-migrations.sh --list                              # just list the files
#
# Options:
#   --db NAME        target database (required unless --list)
#   --user NAME      role to connect as (default: $PGUSER, else the OS user)
#   --host HOST      server host (default: $PGHOST, else the local socket)
#   --port PORT      server port (default: $PGPORT, else 5432)
#   --apply          really run the files; without it, only print what would run
#   --list           print the migration files and exit
#   --sql-dir DIR    directory holding the .sql files (default: py/src/bbsengine6/sql)
#   -h, --help       show this help
#
# Notes:
#   * Migrations are idempotent (ALTER ... OWNER TO is a no-op when the owner matches; the
#     ADD COLUMN IF NOT EXISTS forms are safe to re-run). Re-running is allowed.
#   * Owner migrations (owner_zoid6*.sql) must run as a superuser or as the current owner.
#   * Only .sql files directly in --sql-dir are considered. Pass names to run a subset.
#   * Run order is set in ORDERED (content and schema first, owner transfers last). A new
#     migration file not listed there runs after them, in name order.
#   * Each file runs under psql --single-transaction. The two owner migrations also contain
#     their own begin/commit, so psql prints a harmless "transaction in progress" warning for
#     them; they still commit as one unit.
#   * Nothing is written to the database in dry-run mode, and no password is accepted on the
#     command line. Use PGPASSWORD, ~/.pgpass, or peer auth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SQL_DIR="${REPO_ROOT}/py/src/bbsengine6/sql"

DB=""
DBUSER="${PGUSER:-$(id -un)}"
DBHOST="${PGHOST:-}"
DBPORT="${PGPORT:-5432}"
APPLY=0
LIST_ONLY=0
FILES=()

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

die() {
    echo "run-migrations: $*" >&2
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db)      [[ $# -ge 2 ]] || die "--db needs a value"; DB="$2"; shift 2 ;;
        --user)    [[ $# -ge 2 ]] || die "--user needs a value"; DBUSER="$2"; shift 2 ;;
        --host)    [[ $# -ge 2 ]] || die "--host needs a value"; DBHOST="$2"; shift 2 ;;
        --port)    [[ $# -ge 2 ]] || die "--port needs a value"; DBPORT="$2"; shift 2 ;;
        --sql-dir) [[ $# -ge 2 ]] || die "--sql-dir needs a value"; SQL_DIR="$2"; shift 2 ;;
        --apply)   APPLY=1; shift ;;
        --list)    LIST_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        --)        shift; FILES+=("$@"); break ;;
        -*)        die "unknown option: $1 (see --help)" ;;
        *)         FILES+=("$1"); shift ;;
    esac
done

[[ -d "$SQL_DIR" ]] || die "sql directory not found: $SQL_DIR"

# Run order. Content and schema migrations come first. Owner transfers come last, because
# they change the owner of objects the earlier migrations create or insert into (for example
# the message tables that migrate_notify_to_message.sql fills). Any migration file not listed
# here is run after these, in name order, so a new file is never silently skipped.
ORDERED=(
    channel_access_migration.sql
    migrate_member_terminaltype.sql
    migrate_nologin.sql
    migrate_notify_to_message.sql
    pgrole_loginid_migration.sql
    owner_zoid6_message_migration.sql
    owner_zoid6_migration.sql
)

# Migration files: the migrate_*, *_migration*, and owner_* scripts in sql/. Other files in
# sql/ (schema definitions, functions) are not migrations and are left alone.
mapfile -t FOUND < <(cd "$SQL_DIR" && ls -1 *.sql 2>/dev/null | grep -E '(migrat|^owner_)' | sort)
ALL=()
for f in "${ORDERED[@]}"; do
    for g in "${FOUND[@]}"; do [[ "$g" == "$f" ]] && ALL+=("$f"); done
done
for g in "${FOUND[@]}"; do
    known=0
    for f in "${ORDERED[@]}"; do [[ "$g" == "$f" ]] && known=1; done
    [[ $known -eq 0 ]] && ALL+=("$g")
done

if [[ ${#FILES[@]} -eq 0 ]]; then
    SELECTED=("${ALL[@]}")
else
    SELECTED=()
    for f in "${FILES[@]}"; do
        f="$(basename "$f")"
        [[ -f "$SQL_DIR/$f" ]] || die "no such migration file in $SQL_DIR: $f"
        SELECTED+=("$f")
    done
fi

if [[ $LIST_ONLY -eq 1 ]]; then
    printf '%s\n' "${ALL[@]}"
    exit 0
fi

[[ -n "$DB" ]] || die "--db is required (see --help)"
[[ ${#SELECTED[@]} -gt 0 ]] || die "no migration files found in $SQL_DIR"

command -v psql >/dev/null 2>&1 || die "psql not found on PATH"

PSQL_ARGS=(--dbname "$DB" --username "$DBUSER" --port "$DBPORT" -X -v ON_ERROR_STOP=1 --quiet)
[[ -n "$DBHOST" ]] && PSQL_ARGS+=(--host "$DBHOST")

echo "database : $DB (user $DBUSER${DBHOST:+, host $DBHOST}, port $DBPORT)"
echo "sql dir  : $SQL_DIR"
if [[ $APPLY -eq 1 ]]; then
    echo "mode     : APPLY"
else
    echo "mode     : dry run (pass --apply to run the files)"
fi
echo "plan     :"
for f in "${SELECTED[@]}"; do
    echo "  - $f"
done

if [[ $APPLY -eq 0 ]]; then
    echo "dry run: nothing was applied."
    exit 0
fi

# Test the connection before running anything, so a bad password fails here, not midway.
psql "${PSQL_ARGS[@]}" -c 'select 1' >/dev/null || die "cannot connect to $DB as $DBUSER"

for f in "${SELECTED[@]}"; do
    echo "--- applying $f"
    # Each file runs in its own transaction (the files begin/commit themselves where needed,
    # and --single-transaction wraps the rest, so a failure leaves the file unapplied).
    if ! psql "${PSQL_ARGS[@]}" --single-transaction -f "$SQL_DIR/$f"; then
        echo "run-migrations: FAILED on $f. Earlier files were applied; this one was rolled back." >&2
        exit 1
    fi
    echo "--- ok: $f"
done

echo "all ${#SELECTED[@]} migration(s) applied to $DB."
