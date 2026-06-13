#!/bin/bash
#
# sync_teos_blurbs.sh
# 
# Syncs markdown files in a directory with the database.
# Filesystem wins - files on disk are added to database if they don't exist.
# 
# Usage: 
#   ./sync_teos_blurbs.sh <directory> [--dry-run]
#   ./sync_teos_blurbs.sh /srv/www/zoid6/teos/ --dry-run

usage() {
    echo "Usage: $0 <directory> [--dry-run]"
    echo ""
    echo "Arguments:"
    echo "  directory    Path to scan for markdown files (required)"
    echo "  --dry-run    Preview what would be created without making changes"
    exit 1
}

# Parse arguments
DRY_RUN=""
TEOSFILEPATH=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN="1"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [ -z "$TEOSFILEPATH" ]; then
                TEOSFILEPATH="$1"
            else
                echo "Error: Unexpected argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$TEOSFILEPATH" ]; then
    echo "Error: directory is required"
    usage
fi

if [ ! -d "$TEOSFILEPATH" ]; then
    echo "Error: Directory does not exist: $TEOSFILEPATH"
    exit 1
fi

DBNAME="zoid6"

# Get current user (default to 'jam' if not logged in)
CURRENT_USER=$(whoami)
if [ -z "$CURRENT_USER" ]; then
    CURRENT_USER="jam"
fi

echo "TEOS Blurb Sync"
echo "==============="
echo "Directory: $TEOSFILEPATH"
echo "User: $CURRENT_USER"
if [ -n "$DRY_RUN" ]; then
    echo "Mode: DRY RUN"
else
    echo "Mode: LIVE"
fi
echo ""

count=0
created=0
skipped=0

# Find all .md files recursively, excluding backup files
find "$TEOSFILEPATH" -type f -name "*.md" -print0 | while IFS= read -r -d '' filepath; do
    # Skip backup files (*.md~)
    if [[ "$filepath" =~ \.md~$ ]]; then
        echo "Skipping backup: $filepath"
        ((skipped++)) || true
        continue
    fi
    
    ((count++)) || true
    
    # Generate blurb ID from filepath
    # /srv/www/zoid6/teos/ec/john-edward.md → ec.john-edward
    relativepath="${filepath#$TEOSFILEPATH}"
    blurbid="${relativepath%.md}"
    blurbid="${blurbid//\//.}"
    
    echo "Processing: $blurbid"
    
    # Check if blurb exists in database
    exists=$(psql -t -A -d "$DBNAME" -c "SELECT 1 FROM engine.__blurb WHERE id = '$blurbid' LIMIT 1" 2>/dev/null || echo "")
    
    if [ -n "$exists" ]; then
        echo "  Already exists in DB: $blurbid"
        ((skipped++)) || true
        continue
    fi
    
    # Extract title from frontmatter or filename
    title=""
    if grep -q "^---" "$filepath" 2>/dev/null; then
        title=$(sed -n 's/^title: *//p' "$filepath" | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    fi
    
    if [ -z "$title" ]; then
        # Use filename without extension as title
        title=$(basename "$filepath" .md)
        title=$(echo "$title" | sed 's/-/ /g')
    fi
    
    # Escape single quotes in title for SQL
    title_escaped=$(echo "$title" | sed "s/'/''/g")
    
    # Create blurb in database
    if [ -n "$DRY_RUN" ]; then
        echo "  [DRY RUN] Would create: $blurbid (title: $title, contentfilename: $relativepath, user: $CURRENT_USER)"
    else
        psql -d "$DBNAME" -c "INSERT INTO engine.__blurb (id, kind, attributes, contentfilename, datecreated, createdbymoniker) VALUES ('$blurbid', 'markdown', '{\"title\": \"$title_escaped\"}', '$relativepath', NOW(), '$CURRENT_USER')" 2>/dev/null
        echo "  Created: $blurbid"
    fi
    
    ((created++)) || true
    
done

echo ""
echo "Summary"
echo "-------"
echo "Total files processed: $count"
echo "Created: $created"
echo "Skipped: $skipped"

if [ -n "$DRY_RUN" ]; then
    echo ""
    echo "This was a dry run. Run without --dry-run to apply changes."
fi
