# bbsengine6.blurb — content entity

> **Status:** canonical. The filesystem-based blurb handler
> described here is the live implementation. The older
> `handbook/specs/blurb.md` (with `bigserial` PKs and JSONB-only
> content) describes a superseded Python-side entity model and is
> retained only for the schema relationship map; it is **not** the
> live spec.

A **blurb** is a content node (post, page, article) in the BBS
engine. Blurbs live on the filesystem (markdown files with optional
YAML frontmatter) with metadata stored in `engine.__blurb`. URI
paths map directly to file paths.

## Contents

- [Schema](#schema)
- [File layout](#file-layout)
- [Python module](#python-module)
- [PHP counterpart](#php-counterpart)
- [SQL files](#sql-files)
- [Content format](#content-format)
- [Public API](#public-api)

## Schema

```sql
CREATE TABLE engine.__blurb (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    attributes      JSONB,
    contentfilename TEXT,
    datecreated     TIMESTAMPTZ,
    createdbymoniker TEXT REFERENCES engine.__member(moniker)
);

CREATE VIEW engine.blurb AS
SELECT b.*,
       array_agg(s.path ORDER BY s.path) AS sigs
FROM engine.__blurb b
LEFT JOIN engine.map_blurb_sig m ON m.blurbid = b.id
LEFT JOIN engine.sig s ON s.path = m.sigpath
GROUP BY b.id;
```

The primary key is **text**, not `bigserial`. A typical id is
`"ec.john-edward"` — derived from the URI path with `.` as the
separator. This is the live schema; see `py/src/bbsengine6/sql/blurb.sql`.

Related tables:

| Table                          | Purpose                                                                                  |
|--------------------------------|------------------------------------------------------------------------------------------|
| `engine.map_blurb_sig`         | `(blurbid, sigpath)` — many-to-many between blurbs and sig paths                          |
| `engine.map_member_blurb_read` | `(moniker, blurbid, dateread)` — read-tracking for unread indicators                      |
| `engine.map_blurb_tag`         | `(blurbid, tag)` — free-form tags                                                        |
| `engine.map_blurb_flag`        | `(blurbid, name, value)` — blurb flags (sticky, frozen, approved, …)                       |
| `engine.blurb_flag`            | `(name, description)` — flag definitions                                                  |

## File layout

```
BLURBDIR (default: /srv/www/blurbs/teos/)
├── ec/
│   ├── index.md
│   └── john-edward.md
├── comp/
│   └── lang/
│       └── python.md
└── index.md
```

The URI mapping is `ec/john-edward.md` → blurbid `ec.john-edward`
(slashes become dots; `.md` is stripped). The path is checked
against the configured `BLURBDIR` to prevent traversal.

## Python module

`py/src/bbsengine6/blurb.py` exposes:

| Function              | Signature                                                                              | Notes                                                                                |
|-----------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `get_content_dir`     | `(args) -> pathlib.Path`                                                               | Honors `args.blurb_content_dir` and `$BBSENGINE6_BLURB_CONTENT_DIR` (default `/var/bbsengine6/blurb_content`) |
| `_safe_content_path`  | `(args, contentpath) -> pathlib.Path | None`                                            | Resolves `contentpath`, confirms it stays under `get_content_dir(args)`; returns `None` on traversal or unreadable path |
| `insert`              | `(args, blurb, prg, table="engine.__blurb", returnid=True, primarykey="id", mogrify=False)` | Wraps `database.insert`; stamps `prg`, `datecreated`, `createdbymoniker`               |
| `save_content`        | `(args, blurbid, content, mogrify=False) -> str`                                       | Writes `content_dir/<blurbid>.txt`; returns the absolute filepath                     |
| `insert_with_content` | `(args, blurb, prg, content=None, **kwargs) -> int`                                    | `insert` + `save_content` + `updateattributes({contentpath: ...})`                     |
| `load_content`        | `(args, blurbid) -> str | None`                                                        | Reads `content_dir/<blurbid>.txt`; returns `None` if missing                          |
| `delete_content`      | `(args, blurbid) -> bool`                                                              | Unlinks `content_dir/<blurbid>.txt`; returns True on success                          |
| `update_with_content` | `(args, id, blurb, content=None, **kwargs) -> int`                                    | `update` + `save_content`; useful for content edits                                   |
| `updateattributes`    | `(args, blurbid, attributes, reset=False, table="engine.__blurb", mogrify=False)`     | `attributes || jsonb` merge (`reset=True` overwrites)                                  |
| `update`              | `(args, id, blurb, reset=False, mogrify=False) -> int`                                | Stamps `dateupdated`, `updatedbymoniker`; delegates to `database.update`              |
| `commit`              | `(args) -> Any`                                                                        | Pass-through to `database.commit`                                                     |
| `build`               | `(args, rec, cur=None) -> dict`                                                       | Hydrate a blurb dict with computed `flags` from `engine.map_blurb_flag`               |
| `_fetch_flags`        | `(cur, blurbid) -> dict`                                                               | Returns `{name: value}` for every flag joined to the blurb                            |
| `get`                 | `(args, id) -> dict | None`                                                            | `select * from engine.__blurb where id = <id>`                                       |
| `get_with_content`    | `(args, id) -> dict | None`                                                           | `get` + content read (preferring `attributes.contentpath` with `_safe_content_path`)  |
| `approve`             | `(args, id, value=True) -> bool`                                                       | Upsert `engine.map_blurb_flag` row with `name='approved'`, `value='true'/'false'`     |

`_safe_content_path` is the security boundary for filesystem access.
`contentpath` is member-controlled JSON; without the path containment
check, a crafted blurb could escape `BLURBDIR`. The function uses
`Path.resolve()` + `candidate.relative_to(base)` and returns `None`
on any failure (path doesn't exist, escapes the base, OSError,
ValueError).

## PHP counterpart

`php/blurb.php` is the namespaced PHP handler that the Apache
front-end renders. The `\bbsengine6\blurb` namespace exposes:

| PHP function                                | Purpose                                                                        |
|---------------------------------------------|--------------------------------------------------------------------------------|
| `isBlurb(string $uri): bool`                | Check if a URI corresponds to a blurb in `engine.__blurb`                       |
| `display(string $uri, ?string $filepath): void` | Render the blurb (Smarty template + markdown → HTML)                         |
| `buildbreadcrumbs(string $sigpath, bool $skiptop=true, ?string $hidepath=null): array` | Build breadcrumb trail from a sig path             |
| `buildbreadcrumblist(int $blurbid): array`  | Build breadcrumbs for every SIG a blurb is posted to                            |
| `getcontentdir(): string`                   | Returns the configured content dir                                               |
| `getcontent(int $blurbid): ?string`         | Read blurb content from file                                                     |
| `getlist(int $offset=0, int $limit=20): array` | Paginated blurb list                                                          |
| `getbyid(int $id): ?array`                  | Get a blurb by id (or null)                                                      |
| `getcount(): int`                           | Total blurb count                                                                |

Constants:

| Constant                       | Default                          |
|--------------------------------|----------------------------------|
| `BLURBDIR`                     | `/srv/www/blurbs/teos/`          |
| `BBSENGINE6_BLURB_CONTENT_DIR` | `/var/bbsengine6/blurb_content`  |

## SQL files

The canonical SQL lives under `py/src/bbsengine6/sql/`:

| File              | Purpose                                                                       |
|-------------------|-------------------------------------------------------------------------------|
| `blurb.sql`       | `engine.__blurb`, `engine.map_blurb_sig`, `engine.map_blurb_tag`              |
| `blurbview.sql`   | `engine.blurb` view                                                           |
| `blurb_flag.sql`  | `engine.blurb_flag` / `engine.map_blurb_flag`                                 |
| `blurb_read.sql`  | `engine.map_member_blurb_read`                                                |

Bootstrap is verified by `py/src/bbsengine6/backend/checkmessage.py`
or the equivalent blurb-specific backend check (called from
`backend.stage_one.main`).

## Content format

Markdown files with optional YAML frontmatter:

```markdown
---
title: John Edward Channeling
author: Various Contributors
category: mediumship
---

# John Edward

Content body goes here. Markdown is rendered through Parsedown /
Smarty on the PHP side and stored verbatim on the Python side
(the body lives on disk, not in the database).
```

The `title` field is the canonical blurb title; the PHP renderer
falls back to the filename if absent. There is no case
transformation — the user's data is authoritative.

## Public API

The router's directory-listing path filters backup / scratch
files (`.swp`, `.bak`, trailing `~`, `#name#`, etc.) before
listing. See `handbook/specs/folder.md` §"Backup and Junk
File Filtering" for the full list. The same filter is applied
to blurb listings rendered through the router.
