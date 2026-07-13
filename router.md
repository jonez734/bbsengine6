# Router Plan

## Problem

`https://zoidtechnologies.com/teos/rec/` returns a WSOD (white screen of death).
Other paths may also return empty bodies (e.g. `/teos/rec/rec/arts/`).

### Root causes

1. **`router_displayDirectoryListing` skips subdirectories.**
   The function used `is_file($fullpath)` and `continue`d on directories. Since
   `rec/` contains only `arts/` (a subdirectory) and no `.md` files, the listing
   was empty — and an empty string in the response body is a WSOD.

2. **`router_displayDirectoryListing` calls `safe_path_web` with an absolute path.**
   `safe_path_web` rejects absolute paths in its components (security feature).
   The first call to `safe_path_web` in `router_handleFolder` succeeded, but the
   second call inside `router_displayDirectoryListing` passed the full
   `/srv/.../rec` path, which was rejected. `safe_path_web` returned `false`,
   `router_displayDirectoryListing` returned `null`, and the router emitted an
   empty string.

3. **`router_handleError` returned `null`.**
   When no handler matched, the loop returned `null` to the HTTP layer, which
   echoed nothing. A 404 must be returned instead.

4. **`TEOSURL` was defined early as `""`.**
   The early `define('TEOSURL', '')` at the top of `router.php` runs before the
   HTTP block tries to redefine `TEOSURL` to `"/teos"`. The `if (!defined)`
   guard made the override a no-op. Directory listing links were therefore
   rendered as relative paths (`rec/arts/`), which the browser resolved against
   the current URL, producing duplicated paths like `/rec/rec/arts/`.

5. **The handler loop returned `null`/`false` instead of continuing.**
   Any handler returning `null` or `false` was treated as a successful result
   and the empty value was emitted as the response body.

## Fixes

### 1. `bbsengine6/engine/router.php`

- Removed the early `TEOSURL` and `TEOSDIR` `define` calls that pinned the
  constants to empty strings. They are now defined only inside the HTTP
  execution block.
- Added `router_get_teosurl()` and `router_get_teosdir()` helpers. These read
  from `TEOSURL`/`TEOSDIR` (constants or env vars) and fall back to sane
  defaults. Handlers and templates use these helpers instead of the bare
  constants so they always have a non-empty value.
- `router_displayDirectoryListing`:
  - Uses `realpath($dirpath)` instead of `safe_path_web` (the caller has
    already validated the path).
  - Includes subdirectory entries in the listing. Each directory entry has
    `is_dir => true` and a trailing `/` is rendered next to the link.
  - Always returns a non-empty string. On `scandir` failure or `realpath`
    failure, it returns the result of `router_handleError` (a 404 page) rather
    than `null`.
- `router_handleError`:
  - Always returns a 404 HTML string.
  - If `bbsengine6\page\error` exists, it is called first; if it returns
    `null`/`false`, the function falls back to a built-in 404.
  - Calls `http_response_code(404)`.
- The main handler loop:
  - Continues to the next handler on `ROUTER_NEXT`, `null`, or `false`.
  - Only returns a non-empty string result.
  - If no handler matches, calls `router_handleError($uri)` which always
    returns a 404 page.
- The HTTP entry point:
  - Defines `TEOSURL` and `TEOSDIR` only here (no early defines).
  - Catches all `Throwable`s and emits a 500 with a clean error message rather
    than a WSOD.
  - Catches `null`/`false` returns and emits a 500 instead of an empty body.
- Removed the unused `ROUTER_STOP` constant references that referenced the old
  early `define` block.

### 2. `test_zoidtechnologies_comp.py`

- Added `test_rec_index`, `test_rec_arts`, `test_rec_arts_magic` to ensure the
  rec blurb directory pages are non-empty (not WSOD).
- Added `test_nonexistent_404` to ensure that bogus paths (`rec/rec/arts`,
  `rec/arts/void`, `top/banana`, `rec/rec/rec`) return a non-empty response
  body — never a WSOD.
- Added `test_rec_all_pages_nonempty` to load every rec blurb subdirectory and
  assert each renders content.

## Deployment

The router is served from
`/srv/www/vhosts/zoidtechnologies.com/html/engine/router.php` on the live
server. The live filesystem is read-only for the current user. The fix is
committed in this repository at `bbsengine6/engine/router.php` and must be
copied to the server by a user with write access (e.g. via `make engine` in
`bbsengine6`, or `rsync` over `ssh`).
