# bbsengine6.folder — folder hierarchy

> **Status:** canonical. The ltree-backed folder hierarchy is the
> live implementation in `py/src/bbsengine6/folder.py`; the PHP
> counterpart is `php/folder.php` with the `\bbsengine6\folder`
> namespace; the public SQL view is `engine.folder`.

A **folder** is a hierarchical node in the BBS engine's content
tree. Folders are stored in `engine.__folder` with an `ltree`
primary key (`path`) and a corresponding `engine.folder` view that
joins author / approver monikers. The Python module handles path
manipulation, validation, and CRUD; the PHP module renders
directory listings and breadcrumbs.

## Contents

- [Schema](#schema)
- [Python module](#python-module)
- [PHP counterpart](#php-counterpart)
- [YAML frontmatter title resolution](#yaml-frontmatter-title-resolution)
- [Ltree patterns](#ltree-patterns)
- [Backup / junk file filtering](#backup--junk-file-filtering)
- [Public API](#public-api)

## Schema

```sql
CREATE TABLE engine.__folder (
    path            ltree PRIMARY KEY,
    uri             text UNIQUE,
    title           text,
    intro           text,
    attrs           jsonb,
    access          jsonb,
    datecreated     timestamptz,
    createdbymoniker text REFERENCES engine.__member(moniker)
);

CREATE VIEW engine.folder AS
SELECT s.*,
       m1.moniker AS createdby,
       m2.moniker AS updatedby
FROM engine.__folder s
LEFT JOIN engine.__member m1 ON m1.moniker = s.createdbymoniker
LEFT JOIN engine.__member m2 ON m2.moniker = s.updatedbymoniker;
```

`path` is `ltree` (e.g. `top.entertainment.movies`). `uri` is the
slash-separated human path (e.g. `entertainment/movies/`). The
`ROOT_SIG_PREFIX` constant (Python: `bbsengine6.folder.ROOT_SIG_PREFIX`,
PHP: `bbsengine6\folder\ROOT_SIG_PREFIX`) toggles between `""`
(no prefix) and `"top"` (legacy `top.` prefix).

## Python module

`py/src/bbsengine6/folder.py` exposes:

| Function / class                          | Signature                                                                                       | Notes                                                                          |
|-------------------------------------------|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `ROOT_SIG_PREFIX`                         | `str = ""`                                                                                       | Toggle for the `top.` ltree prefix                                              |
| `_prefix_path(path)`                      | `(str) -> str`                                                                                  | Apply `ROOT_SIG_PREFIX` if configured                                           |
| `_strip_prefix(path)`                     | `(str) -> str`                                                                                  | Remove `ROOT_SIG_PREFIX` from a path                                            |
| `_validate_path(path)`                    | `(str) -> bool`                                                                                 | Allow only `[a-zA-Z0-9._-]`, max length 256; rejects ReDoS / traversal payloads |
| `_validate_uri(uri)`                      | `(str) -> bool`                                                                                 | `[a-zA-Z0-9._/-]`, max length 256; URI forms may contain slashes                |
| `buildpath(args, path)`                   | `(str) -> str`                                                                                  | Convert hyphens to underscores                                                   |
| `builduri(args, path)`                    | `(str) -> str`                                                                                  | Strip prefix, replace `.` with `/`, ensure trailing `/`                         |
| `builddict(args, row)`                    | `(dict) -> dict`                                                                                | Map DB row → folder dict (`attrs` → `attributes`)                                |
| `buildrow(args, folder)`                  | `(dict) -> dict`                                                                                | Map folder dict → DB row (reverse column mapping)                                |
| `insert(args, folder, **kwargs)`          |                                                                                                  | INSERT into `engine.__folder`; stamps `datecreated`, `createdbymoniker`          |
| `create(args, folder, create_parents=False, **kwargs)` | `(dict) -> bool`                                                                  | INSERT if missing; `create_parents=True` recursively creates ancestors            |
| `get(args, path, **kwargs)`               | `(str) -> dict | None`                                                                         | SELECT with `path ~ <path>`; returns `None` on miss                              |
| `update(args, path, folder, **kwargs)`    | `(str, dict) -> bool`                                                                           | UPDATE; honors `primarykey="path"` default                                       |
| `delete(args, path, **kwargs)`            | `(str) -> bool`                                                                                 | DELETE; `commit=False` to participate in a caller transaction                    |
| `exists(args, buf, **kwargs)`             | `(str) -> bool`                                                                                 | ltree descendant query                                                           |
| `uriexists(args, buf, **kwargs)`          | `(str) -> bool`                                                                                 | Exact-match URI query                                                            |
| `noneexist(args, buf, **kwargs)`          | `(str) -> bool`                                                                                 | True when no entry in `buf` exists                                                |
| `allexist(args, buf, **kwargs)`           | `(str) -> bool`                                                                                 | True when every entry in `buf` exists                                              |
| `getchfoldercompleter(word, **kwargs)`    | generator                                                                                       | Tab-completion source                                                            |
| `input(prompt, oldvalue="", **kw)`         | `(str, str) -> str`                                                                             | Read a folder path from the terminal                                             |
| `striptop(folderpath, top=None)`          | `(str, str | None) -> str`                                                                      | Strip a top prefix; default to `ROOT_SIG_PREFIX`                                  |
| `foldercompleter`                         | `class`                                                                                          | Persistent completer with its own DB connection                                 |

The two validate functions are the security boundary for SQL
queries that interpolate user input into the `~` (ltree
descendant) operator. Path inputs are checked against
`_SAFE_PATH_PATTERN = ^[a-zA-Z0-9._-]+$` and length-capped at 256
to prevent ReDoS and path-traversal payloads.

## PHP counterpart

`php/folder.php` exposes the `\bbsengine6\folder` namespace:

| PHP function                                | Purpose                                                                       |
|---------------------------------------------|-------------------------------------------------------------------------------|
| `getteospath(): string`                     | Base filesystem path to teos content                                          |
| `isFolder(string $uri): bool`               | True iff the URI corresponds to an existing directory                          |
| `getDirectoryItems(string $dirpath, string $uri): array` | List items with title, uri, filename                                |
| `parseYamlFrontmatter(string $yaml): array` | Parse YAML frontmatter into assoc array                                       |
| `getDirectoryTitle(string $uri): string`    | Title for a directory (from YAML or filename; never uppercased)               |
| `display(string $uri): ?string`             | Render the directory listing HTML                                              |
| `getFolderMeta(string $uri): ?array`        | Optional: folder metadata from `engine.folder`                                 |
| `getFolderSigs(string $uri): array`         | Optional: child sigs of the folder                                              |
| `getFolderBreadcrumbs(string $uri): array`  | Optional: breadcrumb trail from `engine.sig`                                    |
| `getTopLevelFolders(): array`               | Optional: top-level sigs                                                       |

Configuration:

| Constant                       | Default                          |
|--------------------------------|----------------------------------|
| `TEOSFILEPATH`                 | `/srv/www/zoid6/teos/`           |
| `BBSENGINE6_BLURB_CONTENT_DIR` | `/var/bbsengine6/blurb_content`  |

Router integration (in `engine/router.php`):

```php
if (\bbsengine6\folder\isFolder($uri)) {
    return \bbsengine6\folder\display($uri);
}
```

## YAML frontmatter title resolution

Title precedence for both the Python and PHP sides:

1. YAML frontmatter `title:` field.
2. Filename (without `.md` extension).
3. URI segment (last path component).

No case transformation is ever applied. The user's data is
authoritative.

```markdown
---
title: John Edward Channeling
---

# John Edward

Content starts here...
```

## Ltree patterns

```sql
-- Get breadcrumbs (paths contained within)
WHERE path @> 'top.entertainment'

-- Get child sigs (paths starting with)
WHERE path ~ 'top.entertainment.*'

-- Top-level (exactly 1 level)
WHERE nlevel(path) = 1
```

`foldercompleter.getmatches(text)` builds the right pattern from
the typed prefix:

| Typed text           | ltree pattern                           |
|----------------------|-----------------------------------------|
| `""` (empty)         | `*{1}` (or `<prefix>.*{1}`)              |
| `"entertainment."`   | `entertainment.*{1}`                    |
| `"entertainment"`    | `entertainment*`                        |

## Backup / junk file filtering

The router (`engine/router.php::router_isIgnoredEntry`) filters
backup / scratch files before listing a directory:

| Pattern                       | Example              | Source                          |
|-------------------------------|----------------------|---------------------------------|
| `.`-prefixed                  | `.hidden`, `..`      | dotfiles                        |
| Trailing `~` (one or more)    | `foo.md~`            | emacs backup                    |
| `.swp`, `.swo`, `.swn`        | `foo.swp`            | vim swap                        |
| `.bak`, `.orig`, `.rej`       | `foo.bak`            | patch / backup tools            |
| `.tmp`, `.temp`, `.save`      | `foo.tmp`            | scratch files                   |
| `#name#`                      | `#foo.md#`           | emacs lockfile                  |

The filter is case-insensitive for the suffix patterns. Tests live
in `/home/opencode/data/work/teos/www/php/test_www_mash_no_duplicates.php`.

## Public API

The Python module is invoked directly from game packages (empyre,
bbsengine6.console, …). The PHP namespace is invoked from the
router during HTTP request handling. The `engine.folder` view is
the read-side entry point for both languages.
