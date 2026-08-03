# bbsengine6.blurb Specification

> **STATUS (2026-07-22): PARTIALLY STALE.** This spec describes a
> Python-side blurb entity model with `bigserial` PKs and JSONB
> attributes, but the actual implementation (`py/src/bbsengine6/blurb.py`
> + `sql/blurb.sql`) uses `text` PKs and a hybrid approach where the
> body is stored on the filesystem (matching the PHP-side
> `BLURB_SPEC.md`). The spec is preserved for the schema
> relationships (`map_blurb_sig`, `blurb_flag`, etc.) which are still
> accurate, but the `__blurb` table definition here is out of date.
> See `BLURB_SPEC.md` for the live PHP handler spec.

## Summary

A **blurb** is a content node in the BBS engine that represents a post, page, or article. Blurbs can be nested (parent/child relationships), categorized by sigpath (forum/section location), and tagged. They serve as the core content entity for the bulletin board system.

## Brief Description

Blurbs are stored in PostgreSQL with metadata for creation, modification, and approval. Each blurb belongs to one or more SIGs (Special Interest Groups) via a mapping table, and can have multiple tags. Blurbs support hierarchical content through parent/child relationships, enabling threaded discussions and nested pages.

## Database Schema

### Table: `engine.__blurb`

Base table storing blurb content and metadata.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigserial | Primary key |
| `parentid` | bigint | FK to `__blurb.id` (self-referencing, for nesting) |
| `kind` | text | Blurb type (e.g., `folder`, `post`, `empyre.player`) |
| `attributes` | jsonb | Flexible key-value metadata |
| `datecreated` | timestamptz | Creation timestamp |
| `createdbymoniker` | citext | Author's member moniker |
| `dateupdated` | timestamptz | Last modification timestamp |
| `updatedbymoniker` | citext | Last editor's member moniker |
| `dateapproved` | timestamptz | Approval timestamp (nullable) |
| `approvedbymoniker` | citext | Approver's member moniker (nullable) |

### Table: `engine.blurb_flag`

Blurb-specific flags (e.g., `sticky`, `frozen`). Separate from member flags.

| Column | Type | Description |
|--------|------|-------------|
| `name` | citext | Primary key - flag name |
| `description` | text | Human-readable description |

### Table: `engine.map_blurb_flag`

Maps blurbs to flags.

| Column | Type | Description |
|--------|------|-------------|
| `blurbid` | bigint | FK to `__blurb.id` |
| `name` | citext | FK to `blurb_flag.name` |
| `value` | text | Flag value (nullable) |

Unique constraint on `(blurbid, name)`.

### Table: `engine.map_member_blurb_read`

Tracks which members have read which blurbs. Used for "unread" indicators and "mark all as read" functionality.

| Column | Type | Description |
|--------|------|-------------|
| `moniker` | citext | FK to `__member.moniker` |
| `blurbid` | bigint | FK to `__blurb.id` |
| `dateread` | timestamptz | Timestamp when the member read the blurb |

**Indexes:**
- Primary key on `(moniker, blurbid)` - fast "has member read this blurb?"
- Index on `moniker` - fast "what has this member read?"
- Index on `blurbid` - fast "who has read this blurb?"

Unique constraint on `(blurbid, name)`.

### Table: `engine.map_blurb_sig`

Maps blurbs to SIGs (forum sections).

| Column | Type | Description |
|--------|------|-------------|
| `blurbid` | bigint | FK to `__blurb.id` |
| `sigpath` | ltree | SIG path (e.g., `top.software.python`) |

Unique constraint on `(blurbid, sigpath)`.

### Table: `engine.map_blurb_tag`

Maps blurbs to tags.

| Column | Type | Description |
|--------|------|-------------|
| `blurbid` | bigint | FK to `__blurb.id` |
| `tag` | text | Tag name |

Unique constraint on `(blurbid, tag)`.

### View: `engine.blurb`

Public-facing view combining blurb data with computed fields.

| Column | Type | Description |
|--------|------|-------------|
| `*` | - | All columns from `__blurb` |
| `datecreatedepoch` | bigint | Unix timestamp of creation |
| `dateupdatedepoch` | bigint | Unix timestamp of last update |
| `dateapprovedepoch` | bigint | Unix timestamp of approval |
| `sigs` | text[] | Array of SIG paths |
| `tags` | text[] | Array of tag names |
| `subblurbcount` | integer | Count of child blurbs |

## PHP API

### `\bbsengine6\blurb\buildbreadcrumbs($sigpath, $skiptop=true, $hidepath=null)`

Returns a list of dictionaries with keys `title`, `path`, `uri` for each part of the SIG path hierarchy.

**Parameters:**
- `$sigpath` (string) - ltree path (e.g., `top.software.python`) or URI path (e.g., `software/python`). The input is normalized using `\bbsengine6\util\pathToLtree()` which replaces `/` with `.` and `-` with `_`.
- `$skiptop` (bool) - Skip the `top` node in the path
- `$hidepath` (string|null) - Optional path to exclude from results

**Returns:** `array` of sig records in hierarchical order

### `\bbsengine6\blurb\buildbreadcrumblist($blurbid)`

Returns breadcrumbs for all SIGs a blurb is posted to. Flattens the `sigs` array, calls `buildbreadcrumbs()` for each, and returns a nested list.

**Parameters:**
- `$blurbid` (int) - Blurb ID

**Returns:** `array` of breadcrumb arrays (one per SIG)

## Content Storage

### Attributes (JSONB)

The `attributes` column stores flexible metadata as JSON. Common keys:

```json
{
  "title": "Post Title",
  "body": "Post content...",
  "format": "markdown",
  "mature": false,
  "sticky": false
}
```

### Hierarchy

Blurbs can be nested via `parentid`:
- Parent blurb deleted → children become orphaned (parentid set to null)
- Parent blurb moved → children follow automatically

## Thread Safety

- **Safe**: Database queries via PDO prepared statements are thread-safe.
- The blurb functions read from the database and return arrays; no shared mutable state.

## Relationships

| Relationship | Via |
|--------------|-----|
| Member (author) | `createdbymoniker` → `__member.moniker` |
| SIGs | `map_blurb_sig` → `__sig.path` |
| Tags | `map_blurb_tag` → `__tag.name` |
| Children | `parentid` → `__blurb.id` |
| Parent | `parentid` (self-reference) |

## Use Cases

1. **Forum Posts** - Blurbs posted to SIGs via `map_blurb_sig`
2. **Pages** - Standalone blurbs (no SIG) for static content
3. **Threads** - Parent blurb + child blurbs for replies
4. **Articles** - Blurbs with tags for categorization

## Known Issues / TODOs

1. The `prg` column is reserved but not yet implemented.
2. No built-in content versioning/audit trail.
3. No soft-delete (currently hard delete cascades to children).
4. The `attributes` JSONB schema is not enforced; callers must agree on keys.
5. No access control at the blurb level (relies on SIG permissions).