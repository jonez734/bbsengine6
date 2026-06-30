# Plan: Replies/Comments on Blurbs (DB-backed)

## Architecture

| Concern | Storage | Authoritative at… |
|---|---|---|
| Blurb body | `.md` file | edit time (human) |
| `title`, `date`, `folder-path` | frontmatter | edit time |
| `parent_blurb_id` | frontmatter `parent-blurb:` ↔ DB | one-way: md → DB on `make prod` |
| Other metadata (`tags`, `author`, `disclosure`, …) | frontmatter `attributes:` block ↔ DB `attributes` JSONB | one-way: md → DB on `make prod` |
| Replies | **DB only** | render time |
| Member identity | `engine.__member` | n/a (existing) |

## Files to create

1. **`bbsengine6/py/src/bbsengine6/sql/blurb.sql`** — replace/extend (existing file) with the schema below.
2. **`bbsengine6/php/blurb_reply.php`** — new handler: `add`, `edit`, `hide`, `list`, `access`.
3. **`bbsengine6/php/blurb_sync.php`** — new sync helper called by Makefile: reads a `.md`, parses frontmatter, upserts `engine.__blurb`.
4. **`bbsengine6/skin/tmpl/blurb_replies.tmpl`** — new partial, extends `blurb.tmpl` footer block.
5. **`blurbs/Makefile`** — add a `blurb-sync` target that invokes `blurb_sync.php` per `.md`, then chains into existing `prod` flow.

## Files to edit

6. **`bbsengine6/php/blurb.php`** — `display()` loads `replies` and assigns `$data["replies"]`; `parseMarkdownSections()` extracts `parent-blurb` and `attributes` from frontmatter and includes them on the returned data (so the template can show parent-blurb link in footer).
7. **`bbsengine6/skin/tmpl/page-markdown-sections.tmpl`** — include `blurb_replies.tmpl`; render parent-blurb link in the section footer.
8. **`bbsengine6/skin/tmpl/blurb.tmpl`** — extend `metadata` block to show reply count (mirroring `socrates_post.tmpl:60-65`); leave the existing `footer` block extension intact for the replies partial.

## SQL (new, in `blurb.sql`)

```sql
-- engine.__blurb: formalize/extend
CREATE TABLE engine.__blurb (
    id                TEXT PRIMARY KEY,                       -- "ec.edgar-cayce-sleeping-prophet"
    kind              TEXT NOT NULL DEFAULT 'markdown',
    parent_blurb_id   TEXT REFERENCES engine.__blurb(id),     -- many-to-one editorial parent
    attributes        JSONB NOT NULL DEFAULT '{}'::jsonb,     -- mirror of frontmatter attributes:
                                                              --   {tags:[...], author:"...", disclosure:"..."}
    contentfilename   TEXT,                                  -- "ec/edgar-cayce-sleeping-prophet.md"
    datecreated       TIMESTAMPTZ NOT NULL DEFAULT now(),
    createdbymoniker  TEXT REFERENCES engine.__member(moniker),
    datemodified      TIMESTAMPTZ,
    modifiedbymoniker TEXT REFERENCES engine.__member(moniker)
);

CREATE VIEW engine.blurb AS
SELECT b.*,
       array_agg(s.path ORDER BY s.path) AS sigs
FROM engine.__blurb b
LEFT JOIN engine.map_blurb_sig m ON m.blurbid = b.id
LEFT JOIN engine.sig s ON s.path = m.sigpath
GROUP BY b.id;

-- Replies
CREATE TABLE engine.__blurb_reply (
    id                BIGSERIAL PRIMARY KEY,
    blurb_id          TEXT NOT NULL REFERENCES engine.__blurb(id) ON DELETE CASCADE,
    parent_reply_id   BIGINT REFERENCES engine.__blurb_reply(id),  -- in schema, not used in v1
    author_moniker    TEXT NOT NULL REFERENCES engine.__member(moniker),
    body_md           TEXT NOT NULL,
    datecreated       TIMESTAMPTZ NOT NULL DEFAULT now(),
    datemodified      TIMESTAMPTZ,
    modifiedbymoniker TEXT REFERENCES engine.__member(moniker),
    flags             JSONB NOT NULL DEFAULT '{}'::jsonb     -- e.g. {"hidden":false}
);
CREATE INDEX ON engine.__blurb_reply (blurb_id, datecreated);

CREATE VIEW engine.blurb_reply AS SELECT * FROM engine.__blurb_reply;
```

**One-way note**: `parent-blurb` and `attributes` come from frontmatter; the DB columns exist, but writes back to `.md` are **not** implemented in v1.

## `blurb_sync.php` (one-way md → DB)

```
parse_yaml_frontmatter(path)  # same regex strategy as blurb.php:311-318
  -> returns {folder-path, date, parent-blurb, attributes, ...}
compute blurbid = path.relpath("blurbs/").replace("/", ".").removesuffix(".md")
upsert into engine.__blurb:
  id, kind='markdown', parent_blurb_id (resolved by id),
  attributes = (frontmatter minus {folder-path, date, title})::jsonb,
  contentfilename = relative path,
  datemodified = now(), modifiedbymoniker = 'jam' (or env)
```

Frontmatter key conventions:
- `folder-path: ec/` → already used; ignored at sync (it's the file location, not metadata).
- `date: ...` → already used; ignored (DB uses `datemodified` for sync, not this field).
- `parent-blurb: ec.index` (NEW) → maps to `parent_blurb_id`.
- `attributes:` (NEW, a YAML mapping) → flattened into `attributes` JSONB. Reserved keys excluded: `folder-path`, `date`, `parent-blurb`. If `attributes:` is absent, store `'{}'::jsonb`.

## `blurb_reply.php` API

```
\bbsengine6\blurb_reply\list(string $blurbid, bool $includeHidden=false): array
\bbsengine6\blurb_reply\add(string $blurbid, string $body, string $moniker): int
\bbsengine6\blurb_reply\edit(int $replyid, string $body, string $moniker): void
   // 24h author window, else PERMISSION DENIED
\bbsengine6\blurb_reply\hide(int $replyid, string $moniker): void
   // sysop only (checkflag("SYSOP"))
\bbsengine6\blurb_reply\access(string $op, array $blurb, ?string $moniker): bool
   // mirrors engine.php:1333 accesspost("reply"):
   //   reply  -> auth && !frozen
   //   edit   -> author && (age<24h || sysop)
   //   hide   -> sysop
```

Routes: `SITEROOT/blurb-reply-{blurbid}` (GET form, POST submit), `/blurb-reply-edit-{replyid}`. Redirect to the blurb on success.

## Template changes

**`blurb.tmpl`** — extend `metadata` block to show reply count:
```
{if $replycount > 0}
  <span class="reply-count">
    <span class="label">Replies:</span>
    <span class="value">{$replycount}</span>
  </span>
{/if}
```
(mirrors `socrates_post.tmpl:60-65`).

**`blurb_replies.tmpl`** (new) — extends `blurb.tmpl` footer block; renders the reply tree via `ParsedownExtra` (already loaded in `blurb.php:321-329`); embeds reply and edit forms (gated on `accessblurb("reply")`); hidden replies shown as `[hidden by moderator]` to non-sysops.

**`page-markdown-sections.tmpl`** — assign `parent_blurb_id` to a footer link (if set) and include `blurb_replies.tmpl` after the body.

**`blurb.php::display()`** — after `parseMarkdownSections()` (line 290):
```
$replies = \bbsengine6\blurb_reply\list($blurbid);
$data["replies"] = $replies;
$data["replycount"] = count(flatten($replies));
$data["parent_blurb_id"] = $blurb["parent_blurb_id"] ?? null;
```

## Makefile changes (`blurbs/Makefile`)

Add a new target, called from `prod`:
```
.PHONY: blurb-sync
blurb-sync:
    @php /home/opencode/data/work/bbsengine6/php/blurb_sync.php .
    # iterates *.md, calls engine.__blurb upsert
```

Insert `blurb-sync` ahead of the rsync steps in the existing `prod` target. The rsync itself is unchanged — only the DB needs to be reachable from the build host (which it already is, given other Makefiles in the repo sync DB-backed content the same way).

## Threading (v1)

`engine.__blurb_reply.parent_reply_id` is in the schema and indexed but **not used at render time** in v1. `list()` returns a flat, time-ordered array. The column is reserved so a future migration can enable nested rendering without schema change.

## Out of scope for v1 (explicit)

- DB → `.md` write-back of metadata changes made via UI.
- Email/notification on new reply (the `bbsengine6` notifyd subsystem exists; can be wired later).
- Markdown preview, mention parsing, attachments.
- Reply-as-blurb (using `parent_blurb_id` as a 1:1 "this blurb is a reply" relationship).

## Tests to add (matching the existing test layout)

- `bbsengine6/php/test_blurb_reply.php` — mock DB; covers add, edit window, hide, access checks.
- `bbsengine6/php/test_blurb_sync.php` — fixture frontmatter strings; verifies correct SQL emitted (no real DB).
- `blurbs/test_blurb_sync.sh` — runs `blurb_sync.php` against a temp DB and asserts `engine.__blurb` rows match the fixtures.
