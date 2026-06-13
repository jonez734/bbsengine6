# Folder Handler Specification

**Module**: `bbsengine6.folder`  
**Status**: Stable  
**Test Coverage**: 25 tests, 100% passing  
**Code Quality**: PHP syntax validated

## 1. Overview

The Folder module provides directory listing functionality for filesystem-based content. Folders are directories containing markdown files, with optional integration with the database sig hierarchy for metadata and breadcrumbs.

### 1.1 Problem Statement

Need a system to:
- List markdown files within a directory
- Generate directory indexes with titles from YAML frontmatter
- Optionally integrate with database sigs for hierarchical organization
- Render directory listings as HTML pages

### 1.2 Design Goals

1. **Filesystem First**: Directories determine structure, no database required for basic listings
2. **Optional DB Integration**: Can use `engine.sig` table for metadata and breadcrumbs
3. **Title from Frontmatter**: Use YAML frontmatter `title` field, fallback to filename
4. **Alphabetical Sorting**: Files always sorted A-Z
5. **No Title Case**: Never call ucfirst/ucase on titles (user's data is authoritative)

## 2. Architecture

### 2.1 Module Structure

```
bbsengine6/php/
├── folder.php           # Main folder handler (namespaced)
└── test_folder.php      # Test suite (25 tests)
```

### 2.2 Database Schema (Optional Integration)

```sql
-- Table: engine.__sig (internal)
CREATE TABLE engine.__sig (
    path        ltree PRIMARY KEY,
    uri         text UNIQUE,
    title       text,
    intro       text,
    attrs       jsonb,
    access      jsonb,
    datecreated timestamptz,
    createdbymoniker text REFERENCES engine.__member(moniker)
);

-- View: engine.sig (public)
CREATE VIEW engine.sig AS
SELECT s.*,
       m1.moniker as createdby,
       m2.moniker as updatedby
FROM engine.__sig s
LEFT JOIN engine.__member m1 ON m1.moniker = s.createdbymoniker
LEFT JOIN engine.__member m2 ON m2.moniker = s.updatedbymoniker;
```

### 2.3 File Structure

```
TEOSFILEPATH (default: /srv/www/zoid6/teos/)
├── ec/
│   ├── john-edward.md
│   └── susan-b.html
├── entertainment/
│   ├── movies/
│   │   └── ...
│   ├── music/
│   │   └── ...
│   └── index.md
└── python/
    └── intro.md
```

## 3. API

### 3.1 Filesystem Functions

```php
namespace bbsengine6\folder;

/**
 * Get the base teos path for folder lookups
 * @return string The filesystem path to teos content
 */
function getteospath(): string;

/**
 * Check if a URI corresponds to an existing directory
 * @param string $uri The request URI (e.g., "ec/john-edward")
 * @return bool True if directory exists, false otherwise
 */
function isFolder(string $uri): bool;

/**
 * Get directory listing items for a folder
 * @param string $dirpath Full filesystem path to directory
 * @param string $uri The request URI
 * @return array Array of items with title, uri, filename
 */
function getDirectoryItems(string $dirpath, string $uri): array;

/**
 * Parse YAML frontmatter string into associative array
 * @param string $yaml The YAML content
 * @return array Parsed key-value pairs
 */
function parseYamlFrontmatter(string $yaml): array;

/**
 * Get the title for a directory from its URI
 * @param string $uri The request URI
 * @return string The directory title (htmlspecialchars escaped, no ucfirst)
 */
function getDirectoryTitle(string $uri): string;

/**
 * Render a directory listing
 * @param string $uri The request URI
 * @return string|null Rendered HTML or null if directory doesn't exist
 */
function display(string $uri): ?string;
```

### 3.2 Database Functions (Optional)

```php
/**
 * Root sig path prefix.
 * Set to empty string "" to disable 'top.' prefix.
 * Set to "top" to use 'top.' prefix (legacy behavior).
 * Available in both PHP (bbsengine6\folder\ROOT_SIG_PREFIX) and Python (bbsengine6.folder.ROOT_SIG_PREFIX).
 */
const ROOT_SIG_PREFIX = '';

/**
 * Get folder metadata from database
 * @param string $uri The folder URI path (e.g., "entertainment")
 * @return array|null Folder metadata or null if not found
 */
function getFolderMeta(string $uri): ?array;

/**
 * Get folder sigs from database (folders that are sigs)
 * @param string $uri The folder URI path
 * @return array Array of sig records
 */
function getFolderSigs(string $uri): array;

/**
 * Get folder breadcrumb trail from database
 * @param string $uri The folder URI path (e.g., "top.entertainment")
 * @return array Array of breadcrumb sig records
 */
function getFolderBreadcrumbs(string $uri): array;

/**
 * List all top-level folders from database (sigs with 1 level)
 * @return array Array of top-level sigs
 */
function getTopLevelFolders(): array;
```

### 3.3 Configuration

| Constant | Default | Description |
|----------|---------|-------------|
| `TEOSFILEPATH` | `/srv/www/zoid6/teos/` | Base directory for teos content |
| `BBSENGINE6_BLURB_CONTENT_DIR` | `/var/bbsengine6/blurb_content` | Alternative blurb content dir |

## 4. Usage

### 4.1 Router Integration

The router checks for folders after blurbs:

```php
if (\bbsengine6\folder\isFolder($uri)) {
    return \bbsengine6\folder\display($uri);
}
```

### 4.2 Directory Structure

```
TEOSFILEPATH/
├── ec/
│   ├── john-edward.md      # → /teos/ec/john-edward
│   └── susan-b.md
├── entertainment/
│   ├── movies/
│   │   ├── index.md
│   │   └── matrix.md
│   └── music/
│       └── beatles.md
└── python/
    └── intro.md
```

### 4.3 Markdown File Format

```markdown
---
title: John Edward Channeling
author: Various Contributors
category: mediumship
---

# John Edward

Content starts here...
```

### 4.4 Title Resolution

1. Check for YAML frontmatter `title` field
2. Fall back to filename (without .md extension)
3. Never apply any case transformation (no ucfirst, ucase)

## 5. Testing

Run tests:
```bash
php test_folder.php        # Mock tests (10)
php test_folder.php --db   # Integration tests (20 total)
```

### 5.1 Test Coverage

**Mock Tests (10):**
- getteospath returns default path
- getteospath handles custom constant
- getDirectoryTitle generates correct title
- getDirectoryTitle handles root level
- getDirectoryTitle escapes HTML
- parseYamlFrontmatter (4 tests)
- URI construction

**Integration Tests (10):**
- isFolder detection
- Empty directory handling
- Alphabetical sorting
- Frontmatter title parsing
- Filename fallback
- URI construction
- display() null for non-existent
- display() HTML output for existing

**Database Tests (5):**
- getFolderMeta returns data
- getFolderMeta returns null for non-existent
- getFolderBreadcrumbs returns breadcrumbs
- getTopLevelFolders returns root sigs
- getFolderSigs returns child sigs

## 6. Ltree Patterns

When querying database for sig paths:

```sql
-- Get breadcrumbs (paths contained within)
WHERE path @> 'top.entertainment'

-- Get child sigs (paths starting with)
WHERE path ~ 'top.entertainment.*'

-- Get top-level (exactly 1 level)
WHERE nlevel(path) = 1
```

## 7. Error Handling

- **Directory not found**: `display()` returns null
- **Database error**: Silently returns null/empty arrays
- **Missing frontmatter**: Uses filename as title
- **Invalid YAML**: Returns empty array from parseYamlFrontmatter

## 8. Known Limitations

- No recursive directory scanning (one level only)
- No file type filtering (includes all *.md files)
- No pagination (returns all files)
- No sorting options (always alphabetical)
- No write API (files created manually)
