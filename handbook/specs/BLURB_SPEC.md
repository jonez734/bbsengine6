# Blurb Handler Specification

**Module**: `bbsengine6.blurb`  
**Status**: Stable  
**Test Coverage**: 9 tests, 100% passing  
**Code Quality**: PHP syntax validated

> **NOTE:** This spec is the **PHP handler** spec (filesystem-based
> content with `text` PKs). There is a separate `blurb.md` in this
> directory that documents an older Python-side entity model with
> `bigserial` PKs; that model is **not the live implementation** and
> is preserved only for historical reference to the schema
> relationships. When in doubt, this spec (`BLURB_SPEC.md`) and the
> live SQL in `py/src/bbsengine6/sql/blurb.sql` are authoritative.

## 1. Overview

The Blurb module provides filesystem-based content pages with database metadata. Blurbs are markdown files stored in a directory structure that maps to URI paths, with metadata stored in the `engine.__blurb` table.

### 1.1 Problem Statement

Need a system to render static markdown content (teospages) with:
- Database-driven metadata (kind, attributes, timestamps)
- Breadcrumb navigation from sig hierarchy
- Consistent URI routing through router

### 1.2 Design Goals

1. **Filesystem First**: Content lives in flat files, database provides metadata
2. **URI-Based**: File path determines URI (`/srv/www/blurbs/teos/ec/file.md` → `/teos/ec/file`)
3. **Breadcrumbs**: Automatic breadcrumb generation from sig paths
4. **Backward Compatible**: Global function wrappers for router integration

## 2. Architecture

### 2.1 Module Structure

```
bbsengine6/php/
├── blurb.php           # Main blurb handler (namespaced)
└── test_blurb.php     # Test suite
```

### 2.2 Database Schema

```sql
-- Table: engine.__blurb (internal)
CREATE TABLE engine.__blurb (
    id          TEXT PRIMARY KEY,      -- e.g., "ec.john-edward"
    kind        TEXT NOT NULL,         -- e.g., "markdown"
    attributes  JSONB,                  -- e.g., {"title": "..."}
    contentfilename TEXT,               -- relative path to content file
    datecreated TIMESTAMPTZ,
    createdbymoniker TEXT REFERENCES engine.__member(moniker)
);

-- View: engine.blurb (public)
CREATE VIEW engine.blurb AS
SELECT b.*, 
       array_agg(s.path ORDER BY s.path) as sigs
FROM engine.__blurb b
LEFT JOIN engine.map_blurb_sig m ON m.blurbid = b.id
LEFT JOIN engine.sig s ON s.path = m.sigpath
GROUP BY b.id;
```

### 2.3 File Structure

```
BLURBDIR (default: /srv/www/blurbs/teos/)
├── ec/
│   └── john-edward.md
├── comp/
│   └── lang/
│       └── python.md
└── index.md
```

- **URI Mapping**: `ec/john-edward.md` → blurbid `ec.john-edward`
- **Content**: Markdown files with optional YAML frontmatter

## 3. API

### 3.1 Namespaced Functions (Primary)

```php
namespace bbsengine6\blurb;

/**
 * Check if a blurb exists in the database
 * @param string $uri The URI path (e.g., "ec/filename")
 * @return bool True if blurb exists in database
 */
function isBlurb(string $uri): bool;

/**
 * Render a blurb with database metadata and markdown content
 * @param string $uri The URI path
 * @param string|null $filepath Optional filepath (unused, for signature consistency)
 * @return void Outputs the rendered page
 *
 * Template data includes:
 *   - content: raw markdown
 *   - blurb: database record (or empty array)
 *   - breadcrumbs: ancestor sigs (may be empty)
 *   - uri: the blurb URI (used by template for parent folder link)
 *   - title: parsed from frontmatter or first <h1>
 *   - sections: array of {header, content, date, author}
 *   - choices: navigation choices
 */
function display(string $uri, ?string $filepath): void;

/**
 * Build breadcrumbs from a sig path
 * @param string $sigpath The sig path (e.g., "ec_john-edward")
 * @param bool $skiptop Skip the "top" sig in breadcrumbs
 * @param string|null $hidepath Optional path to hide
 * @return array Array of breadcrumb sig records
 */
function buildbreadcrumbs(string $sigpath, bool $skiptop = true, ?string $hidepath = null): array;

/**
 * Build breadcrumb list from a blurb ID
 * @param int $blurbid The blurb ID
 * @return array Array of breadcrumb arrays
 */
function buildbreadcrumblist(int $blurbid): array;

/**
 * Get the content directory for blurbs
 * @return string The content directory path
 */
function getcontentdir(): string;

/**
 * Get blurb content from file
 * @param int $blurbid The blurb ID
 * @return string|null The content or null if not found
 */
function getcontent(int $blurbid): ?string;

/**
 * Get list of blurbs with pagination
 * @param int $offset Offset for pagination
 * @param int $limit Number of results
 * @return array Array of blurb records
 */
function getlist(int $offset = 0, int $limit = 20): array;

/**
 * Get a blurb by ID
 * @param int $id The blurb ID
 * @return array|null The blurb record or null if not found
 */
function getbyid(int $id): ?array;

/**
 * Get count of blurbs
 * @return int Total number of blurbs
 */
function getcount(): int;
```

### 3.2 Configuration

| Constant | Default | Description |
|----------|---------|-------------|
| `BLURBDIR` | `/srv/www/blurbs/teos/` | Base directory for blurb markdown files |
| `BBSENGINE6_BLURB_CONTENT_DIR` | `/var/bbsengine6/blurb_content` | Alternative content directory |

## 4. Usage

### 4.1 Router Integration

The router checks for blurbs before other handlers:

```php
if (\bbsengine6\blurb\isBlurb($uri)) {
    return \bbsengine6\blurb\display($uri, null);
}
```

### 4.2 Creating a Blurb

1. Create markdown file: `BLURBDIR/ec/john-edward.md`
2. Insert database record:

```sql
INSERT INTO engine.__blurb (id, kind, attributes, datecreated, createdbymoniker)
VALUES ('ec.john-edward', 'markdown', '{"title": "John Edward"}', NOW(), 'jam');
```

### 4.3 Content File Format

```markdown
---
title: John Edward Channeling
author: Various
---

# John Edward

Content goes here...
```

## 5. Testing

Run tests:
```bash
php test_blurb.php        # Mock tests
php test_blurb.php --db   # Database integration tests
```

### 5.1 Test Coverage

- URI to blurbid conversion
- .md extension stripping
- Nested path handling
- Database isBlurb queries
- Display rendering

## 6. Error Handling

- **File not found**: Returns 404 via `\bbsengine6\page\error()`
- **Database error**: Silently returns null/empty, logs via `echo_traceback`
- **Missing breadcrumbs**: Returns empty array

## 7. Known Limitations

- No write API (blurbs are created manually in filesystem + database)
- No version history
- No draft/publish workflow
- Content must be markdown (no HTML or other formats)
