# Make `bbsengine6.channel` fully functional for casino and friends

## Phase 0 — Recon (read-only)

- [x] Confirm top-level CLI dispatch site for `bbsengine6 <subcommand>` → **`bbsengine6/console/__main__.py`** + `bbsengine6/console/lib.py`. Subcommands registered in `CONSOLE_SUBCOMMANDS` tuple. Plan's `bbsengine6/cli/` path is wrong; use `bbsengine6/console/` instead. File `bbsengine6/py/src/bbsengine6/cli/__init__.py` and `bbsengine6/py/src/bbsengine6/cli/con.py` should be `bbsengine6/py/src/bbsengine6/console/channel.py` (or similar).
- [x] Confirm `bed.tools.message.py:138-694` argparse shape as CLI precedent (sysop-gated, token-file-aware, JSON output)
- [x] Confirm `ChannelServiceHandler` registration point in `bbsengine6/channel/api/handler.py:148-157` — registered at line 144 inside `MessageRouter.__init__`
- [x] Confirm `casino.config.py` schema location for new `channel_creator` / `channel_overrides` keys — `_casino_config` populated from `args.config_file` via `_bootstrap_casino_config` at `handler.py:1464`
- [x] Confirm `casino.startup.main` conn/pool threading convention — `with database.getpool(args) as pool, database.connect(args, pool=pool) as conn:` then threads `conn=conn` through helpers
- [ ] Update misleading docstring at `bbsengine6/py/tests/test_startup_postoffice_chain.py:77-78`

## Phase 1 — Centralize channel-state sharing in bed

- [x] Edit `bed/src/bed/main.py:604-643`: in `BED.start`, construct one `ChannelState()`, pass to `WebSocketServer(channel_state=state)` and `MessageRouterClass(..., channel_state=state)`
- [x] Remove `server._channel_state = self.channel_state` from `casino/src/casino/api/handler.py:1544`
- [x] Remove duplicate wiring from `empyre/src/empyre/api/handler.py:838` — was only a comment, no actual wiring line; no edit needed
- [x] Remove duplicate wiring from `mistermcfeely/src/postoffice/api/handler.py:564` — was only a comment, no actual wiring line; no edit needed

## Phase 1.5 — Production schema + namespacing + auto-seed

### Namespacing foundation

- [x] Edit `bbsengine6/py/src/bbsengine6/sql/member.sql:39`: extend regex via `DO $$ ... $$` block to `^[a-zA-Z0-9_]+(?::[a-zA-Z0-9_]+)?$`; idempotent
- [x] Edit `bbsengine6/py/src/bbsengine6/member/lib.py`: add `RESERVED_MONIKERS = frozenset({"sysop", "term", "web", "bed"})` with rationale docstring (shipped roles only; namespacing is primary defense; downstream installs don't extend this constant)
- [x] Add `is_namespaced_moniker(moniker) -> bool` to `member/lib.py`: returns `":" in moniker`
- [x] Add `register_module_member(args, moniker, **kwargs)` to `member/lib.py`: bypass path; enforces namespaced form, lowercase, shape; skips reservation check; sets `createdbymoniker = approvedbymoniker = moniker` (self-referential FK target allowed)
- [x] Modify `libmember.insert` (called from `console/member.py:524`): reject `:` in moniker; reject reserved flat names

### Production schema bootstrap

- [x] Create `bbsengine6/py/src/bbsengine6/backend/checkchannel.py`: mirror `checkmessage.py:1-129`; loads `engine.__channel`, `engine.__channel_announcer` from `channel.sql`
- [x] Edit `bbsengine6/py/src/bbsengine6/backend/stage_one.py:24-54`: add `"checkchannel"` to iteration tuple after `"checkmessage"`
- [x] Add `bbsengine6/py/src/bbsengine6/sql/checkmember_moniker_format.sql`: idempotent migration for `chk_member_moniker_format` constraint (namespacing extension)
- [x] Add `bbsengine6/py/src/bbsengine6/backend/checkmember_moniker_format.py`: always-run migration module so legacy DBs pick up the namespaced pattern on next startup
- [x] Add `"checkmember_moniker_format"` to `stage_one.py` after `"checkchannel"`
- [x] Remove redundant inline DO block from `member.sql` (now in dedicated migration file)

### Channel config in JSON

- [x] Edit `bed/src/bed/data/bed.json`: add top-level `channel` section between line 42 and line 43:
  - [x] `enabled: true`
  - [x] `modulepath: "bbsengine6.channel.api.handler"`
  - [x] `description`
  - [x] `admin_handler_enabled: true`
  - [x] `auto_seed` list with `casino:global` (createdby=`zoid6:casino`, announce_only=false) and `system:announcements` (createdby=`zoid6:casino`, announce_only=true, announcers=[`sysop`])
- [x] Edit `zoid6/src/zoid6/data/zoid6.json`: extend existing `services.channel` (lines 26-30) with `admin_handler` sub-key; no `auto_seed` here (BED-level concern only)

### ChannelService auto-seed (router-time)

- [x] Edit `bbsengine6/py/src/bbsengine6/channel/api/handler.py` `MessageRouter.__init__`: accept `config: Optional[Dict[str, Any]] = None`
- [x] Add dual-shape config resolution: `channel_cfg = (config or {}).get("channel") or (config or {}).get("services", {}).get("channel") or {}`
- [x] Gate `register_all` on `channel_cfg.get("enabled", True)`
- [x] Add `_auto_seed_channels(args, channel_cfg)`:
  - [x] For each entry in `channel_cfg.get("auto_seed", [])`:
    - [x] If `createdby` is not namespaced → warn-and-skip (option b)
    - [x] Else call `_ensure_daemon_member(args, createdby)`:
      - [x] Check if member exists
      - [x] If not, call `register_module_member(args, createdby, email=f"{createdby}@localhost", approved=True)`
      - [x] If creation fails → warn-and-skip
    - [x] Call `ChannelService(args).create_channel(...)`; treat `"Channel already exists"` as success

### Casino-side channel handling

- [x] Create `casino/src/casino/startup/checkchannels.py`: reads `args._casino_config`; warns-and-skips if `channel_creator` missing; applies `channel_overrides` if configured; returns True on warnings
- [x] Edit `casino/src/casino/startup/main.py`: after classlist loop (line 159-160), call `checkchannels.main(args, conn=conn)`
- [ ] Edit `casino/src/casino/config.py`: docstring update only (new keys)

## Phase 2 — Plumb sender context through casino publish calls

- [x] Edit `casino/src/casino/api/handler.py`: add `_publish_to_table(server, table_moniker, message, sender_moniker)` helper on BaseService
- [x] Add `_publish_global(server, message, sender_moniker)` helper
- [x] Add `channel_state` kwarg to BaseService.__init__ so the helpers see the shared state
- [x] Replace `server.publish(...)` at line 886 with `_publish_to_table`
- [x] Replace at line 1023 (broadcast_state after bet)
- [x] Replace at line 1358 (slot_result broadcast)
- [x] Replace at line 1638/1640/1645 (handle_broadcast chat + game_state) with helpers resolving sender via session state
- [x] Edit `casino/src/casino/yahtzee/api_handler.py:174`: replace with `channel_publish` direct call, sender = payload.player_moniker; resolve channel_state via parent router
- [x] Edit `casino/src/casino/tictactoe/api_handler.py:158`: same replacement

## Phase 3 — Default router loads the channel handler

- [x] Edit `bbsengine6/py/src/bbsengine6/net/defaultrouter.py`: add `channel_state: Optional["ChannelState"] = None` (and accept auth-wiring kwargs) to `__init__`
- [x] In `register_all`, instantiate `MessageRouter` from `bbsengine6.channel.api.handler` with shared state; call `register_all(server)`

## Phase 4 — `ChannelService` admin surface (WS)

- [x] Edit `bbsengine6/py/src/bbsengine6/channel/api/handler.py`: add `ChannelAdminHandler` class
  - [x] Verb: `channel_create`
  - [x] Verb: `channel_list`
  - [x] Verb: `channel_get`
  - [x] Verb: `channel_set_announce_only`
  - [x] Verb: `channel_add_announcer`
  - [x] Verb: `channel_remove_announcer`
- [x] Each verb resolves actor moniker via `self.sessions.get_moniker(session_id)`
- [x] Each mutator delegates to `ChannelService._require_authority(channel_name, actor_moniker)` (via ChannelService methods that internally call it)
- [x] Register `ChannelAdminHandler` conditionally based on `channel_cfg.get("admin_handler", {}).get("enabled", False)` (default off; bed.json/zoid6.json opt-in)

## Phase 5 — `ChannelService` permission hardening

- [x] Edit `bbsengine6/py/src/bbsengine6/services/channel.py`: add `_require_authority(channel_name, by_moniker) -> Optional[Dict]` (returns None on success or `{success: False, ...}` on denial; allows sysop OR `createdby == by_moniker`)
- [x] `set_announce_only`: gate with `_require_authority`
- [x] `add_announcer`: gate with `_require_authority`
- [x] `remove_announcer`: add `actor_moniker` parameter (breaking signature); gate with `_require_authority`
- [x] Update existing tests in `test_channel_announce_only.py` for new `remove_announcer` signature
- [x] Add creator-allowed case (`test_set_announce_only_allows_creator`)
- [x] Add non-creator non-sysop-denied cases (`test_remove_announcer_denies_non_creator`, `test_set_announce_only_denies_non_creator`, `test_add_announcer_denies_non_creator`)

## Phase 6 — Naming-convention helpers (no bot class)

- [x] Create `bbsengine6/py/src/bbsengine6/channel/naming.py`:
  - [x] `table_channel(app, moniker)`
  - [x] `member_channel(moniker)`
  - [x] `global_channel(app)`
  - [x] `announcement_channel()`
  - [x] `shout_channel()`
  - [x] `parse_channel(name)`
- [x] Edit `casino/src/casino/api/handler.py`: refactor `_publish_to_table` and `_publish_global` helpers to use naming helpers
- [x] Edit `casino/src/casino/yahtzee/api_handler.py`: refactor literal in `_broadcast`
- [x] Edit `casino/src/casino/tictactoe/api_handler.py`: refactor literal in `_broadcast`
- [x] Remaining `f"casino:table:..."` literals in `casino/api/handler.py` (lines 577, 608, 714, 737) are io.echo diagnostic strings (not channel publishes) — left as-is to keep diff focused

## Phase 7 — `con` CLI host

- [x] Recon: CLI dispatch is `bbsengine6.console` not `bbsengine6.cli`; plan's `bbsengine6/cli/con.py` becomes `bbsengine6/console/channel.py`, registered in `CONSOLE_SUBCOMMANDS`
- [x] Create `bbsengine6/py/src/bbsengine6/console/channel.py`:
  - [x] Subparser group with subverbs
  - [x] Subverb: `create` (channel-create)
  - [x] Subverb: `list` (channel-list)
  - [x] Subverb: `get` (channel-get)
  - [x] Subverb: `set-announce-only`
  - [x] Subverb: `add-announcer`
  - [x] Subverb: `remove-announcer`
  - [x] Required flags: `--moniker`, standard DB flags via lib.buildargs inheritance, `--debug`
  - [x] Output: JSON to stdout
  - [x] Each verb calls `ChannelService(args).<method>` directly
- [x] Edit `bbsengine6/py/src/bbsengine6/console/lib.py`: add `"channel"` to `CONSOLE_SUBCOMMANDS`
- [x] Edit `bbsengine6/py/src/bbsengine6/console/__main__.py`: switch to `parse_known_args` and forward rest_argv to `handle_subcommand` so subverbs get their own argv
- [x] Edit `zoid6/src/zoid6/api/handler.py` `_register_module` (lines 129-188): forward `config=module_config` to sub-router constructor

## Phase 7.5 — Extensibility documentation

- [x] Edit `bbsengine6/py/src/bbsengine6/member/lib.py` module docstring: cross-reference `register_module_member`; explain `<module>:<purpose>` convention; cross-link EXTENDING_CHANNELS.md
- [x] Edit `bbsengine6/py/src/bbsengine6/channel/api/handler.py` `MessageRouter.__init__` docstring: note auto-seed uses `register_module_member`; cross-link EXTENDING_CHANNELS.md
- [x] Edit `bed/src/bed/data/bed.json` `channel.auto_seed` comment: already notes the list is shared and createdby should be namespaced (added in Phase 1.5)
- [x] Create `bbsengine6/py/src/bbsengine6/EXTENDING_CHANNELS.md`: 7-step onboarding pattern (accept channel_state; plumb sender_moniker; use namespaced daemon members; add to auto_seed; read per-module config; use naming helpers; opt into ChannelAdminHandler)

## Phase 8 — Tests

### Reserved moniker tests

- [x] Create `bbsengine6/py/tests/test_member_reserved.py`:
  - [x] Reserved flat monikers rejected: `sysop`, `term`, `web`, `bed`
  - [x] Namespaced moniker rejected by `libmember.insert`
  - [x] `register_module_member("zoid6:casino", ...)` passes shape checks
  - [x] `register_module_member("casino", ...)` (flat) raises
  - [x] `register_module_member("Zoid6:casino", ...)` (uppercase) raises
  - [x] Namespaced reserved allowed (e.g. `sysop:admin` would pass shape but fail insert due to FK)

### Channel service tests

- [x] Edit `bbsengine6/py/tests/test_channel_announce_only.py`:
  - [x] Update `remove_announcer` tests for new `actor_moniker` signature
  - [x] Add creator-allowed case (`test_set_announce_only_allows_creator`)
  - [x] Add non-creator non-sysop-denied cases (3 cases added in Phase 5)
  - [ ] Add `@pytest.mark.unit` test for `channel_publish(sender_moniker=..., args=...)` verdict enforcement — deferred (would need DB)

### Admin handler tests

- [ ] Create `bbsengine6/py/tests/test_channel_admin.py` — deferred; `TestChannelAdminHandler` in `test_cli_con.py` covers the registration behavior. Full WS-level tests would need an end-to-end bed harness.

### Channel config tests

- [x] Create `bbsengine6/py/tests/test_channel_config.py`:
  - [x] Dual-shape config read (bed.json flat, zoid6.json nested)
  - [x] `_ensure_daemon_member` flat-creator warn-and-skip
  - [x] Empty config / None config / non-dict config handling
  - [ ] `auto_seed` with namespaced daemon that doesn't exist → member created — deferred (would need DB)
  - [ ] `auto_seed` re-run is idempotent — deferred (DB)

### Schema bootstrap tests

- [ ] Create `bbsengine6/py/tests/test_checkchannel.py` — deferred; would require live DB to test the stage_one integration.

### CLI tests

- [x] Create `bbsengine6/py/tests/test_cli_con.py`:
  - [x] CLI-level tests for each verb (list, get, create, set-announce-only, add-announcer, remove-announcer)
  - [x] Success path (verb completes, mock ChannelService captures args)
  - [x] Permission-denied / not-found paths (returns False, JSON envelope)
  - [x] --moniker is required
  - [x] ChannelAdminHandler allowed_verbs default and filtered

### Naming tests

- [x] Create `bbsengine6/py/tests/test_channel_naming.py`:
  - [x] Each helper produces the documented format
  - [x] parse_channel roundtrips with the helpers

### Casino integration tests

- [x] Edit `casino/src/casino/tests/test_channel_integration.py` — pre-existing
  suite covers disconnect-cleanup and message-type registration; 5/5 pass
- [ ] Create `casino/src/casino/tests/test_checkchannels.py` — deferred (would
  require live DB to test casino startup integration)
- [ ] Create `casino/src/casino/tests/_support/__init__.py` — deferred (no
  shared helpers needed yet; consumers use `channel_register_callback`
  directly)

### Final test summary (run against `zoid6` via `BBSENGINE6_CHANNEL_TEST_DBNAME`)

| Test file | Tests | Status |
|-----------|------:|--------|
| `test_member_reserved.py` | 23 | all pass |
| `test_channel_config.py` | 9 | all pass |
| `test_cli_con.py` | 15 | all pass |
| `test_channel_naming.py` | 10 | all pass |
| `test_message_channel.py` | 33 | all pass (pre-existing) |
| `test_channel_announce_only.py` | 25 | all pass (was 23; pre-existing |
| | | `add_announcer` bug — `verifyMemberFound` |
| | | required `pool=` kwarg that callers |
| | | didn't pass — fixed by inlining the |
| | | existence check on the same connection |
| | | as the INSERT) |
| `casino/tests/test_channel_integration.py` | 5 | all pass |
| **Total** | **120** | **all pass** |

Note: `test_channel_announce_only.py` defaulted its DB to `zoid6test`;
added a `BBSENGINE6_CHANNEL_TEST_DBNAME` env override so the same suite
runs against `zoid6` (which exists in the dev sandbox) or any other
target DB.

## Verification

- [x] Run bbsengine6 test suite (120/120 pass against `zoid6`):
      `cd bbsengine6/py && BBSENGINE6_CHANNEL_TEST_DBNAME=zoid6 python -m pytest tests/test_member_reserved.py tests/test_channel_announce_only.py tests/test_channel_config.py tests/test_channel_naming.py tests/test_cli_con.py tests/test_message_channel.py -v`
- [x] Run casino test suite (5/5 pass):
      `cd casino && python -m pytest src/casino/tests/test_channel_integration.py -v`
- [ ] Smoke test prod bootstrap: `python -m bbsengine6 startup --databasename zoid6dev --databaseuser $USER`
- [ ] Smoke test `con`: `python -m bbsengine6 con channel-list --databasename zoid6dev --databaseuser $USER --moniker alice`
