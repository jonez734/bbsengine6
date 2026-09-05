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

- [ ] Edit `bbsengine6/py/src/bbsengine6/channel/api/handler.py`: add `ChannelAdminHandler` class
  - [ ] Verb: `channel_create`
  - [ ] Verb: `channel_list`
  - [ ] Verb: `channel_get`
  - [ ] Verb: `channel_set_announce_only`
  - [ ] Verb: `channel_add_announcer`
  - [ ] Verb: `channel_remove_announcer`
- [ ] Each verb resolves actor moniker via `self.sessions.get_moniker(session_id)`
- [ ] Each mutator delegates to `ChannelService._require_authority(channel_name, actor_moniker)`
- [ ] Register `ChannelAdminHandler` conditionally based on `channel_cfg.get("admin_handler", {}).get("enabled", False)` (default off)

## Phase 5 — `ChannelService` permission hardening

- [x] Edit `bbsengine6/py/src/bbsengine6/services/channel.py`: add `_require_authority(channel_name, by_moniker) -> Optional[Dict]` (returns None on success or `{success: False, ...}` on denial; allows sysop OR `createdby == by_moniker`)
- [x] `set_announce_only`: gate with `_require_authority`
- [x] `add_announcer`: gate with `_require_authority`
- [x] `remove_announcer`: add `actor_moniker` parameter (breaking signature); gate with `_require_authority`
- [x] Update existing tests in `test_channel_announce_only.py` for new `remove_announcer` signature
- [x] Add creator-allowed case (`test_set_announce_only_allows_creator`)
- [x] Add non-creator non-sysop-denied cases (`test_remove_announcer_denies_non_creator`, `test_set_announce_only_denies_non_creator`, `test_add_announcer_denies_non_creator`)

## Phase 6 — Naming-convention helpers (no bot class)

- [ ] Create `bbsengine6/py/src/bbsengine6/channel/naming.py`:
  - [ ] `table_channel(app, moniker)`
  - [ ] `member_channel(moniker)`
  - [ ] `global_channel(app)`
  - [ ] `announcement_channel()`
  - [ ] `parse_channel(name)`
- [ ] Edit `casino/src/casino/api/handler.py`: refactor 8 literal `f"casino:table:{table_moniker}"` sites to `naming.table_channel("casino", table_moniker)`
- [ ] Refactor `f"casino:global"` to `naming.global_channel("casino")`

## Phase 7 — `con` CLI host

- [ ] Create `bbsengine6/py/src/bbsengine6/cli/__init__.py` (empty marker)
- [ ] Create `bbsengine6/py/src/bbsengine6/cli/con.py`:
  - [ ] Subparser group with subverbs
  - [ ] Subverb: `channel-create`
  - [ ] Subverb: `channel-list`
  - [ ] Subverb: `channel-get`
  - [ ] Subverb: `channel-set-announce-only`
  - [ ] Subverb: `channel-add-announcer`
  - [ ] Subverb: `channel-remove-announcer`
  - [ ] `console` registered as hidden alias
  - [ ] Required flags: `--moniker` (or `--token-file` mirroring `bed.tools.message.py`), standard DB flags, `--debug`
  - [ ] Output: JSON to stdout
  - [ ] Each verb calls `ChannelService(args).<method>` directly
- [ ] Edit `zoid6/src/zoid6/api/handler.py` `_register_module` (lines 129-188): forward `config=module_config` to sub-router constructor
- [ ] Wire `con` into top-level dispatch site (TBD after Phase 0 recon)

## Phase 7.5 — Extensibility documentation

- [ ] Edit `bbsengine6/py/src/bbsengine6/member/lib.py` module docstring: cross-reference `register_module_member`; explain `<module>:<purpose>` convention
- [ ] Edit `bbsengine6/py/src/bbsengine6/channel/api/handler.py` `MessageRouter.__init__` docstring: note auto-seed uses `register_module_member`; cross-reference
- [ ] Edit `bed/src/bed/data/bed.json` `channel.auto_seed` comment: note list is shared across all modules; `createdby` should be namespaced per owning module
- [ ] Create `bbsengine6/py/src/bbsengine6/EXTENDING_CHANNELS.md`: four-step onboarding pattern (add `channel_state` kwarg; plumb `sender_moniker`; add JSON entry; pre-create or let auto-seed handle daemon member)

## Phase 8 — Tests

### Reserved moniker tests

- [ ] Create `bbsengine6/py/tests/test_member_reserved.py`:
  - [ ] Reserved flat monikers rejected: `sysop`, `term`, `web`, `bed`
  - [ ] `:` in moniker rejected by `libmember.insert`
  - [ ] `register_module_member("zoid6:casino", ...)` succeeds
  - [ ] `register_module_member("casino", ...)` (flat) raises
  - [ ] `register_module_member("Zoid6:Casino", ...)` (uppercase) raises
  - [ ] `register_module_member("sysop:admin", ...)` (namespaced reserved) — confirm allowed

### Channel service tests

- [ ] Edit `bbsengine6/py/tests/test_channel_announce_only.py`:
  - [ ] Update `remove_announcer` tests for new `actor_moniker` signature
  - [ ] Add creator-allowed case
  - [ ] Add sysop-allowed case
  - [ ] Add non-creator non-sysop-denied case
  - [ ] Add `@pytest.mark.unit` test: `channel_publish(sender_moniker=..., args=...)` consults `ChannelService.can_publish` and drops denied messages

### Admin handler tests

- [ ] Create `bbsengine6/py/tests/test_channel_admin.py`:
  - [ ] WS-level tests for each `channel_*` verb
  - [ ] Sysop success case
  - [ ] Creator success case
  - [ ] Non-creator non-sysop denial case

### Channel config tests

- [ ] Create `bbsengine6/py/tests/test_channel_config.py`:
  - [ ] Dual-shape config read (bed.json flat, zoid6.json nested)
  - [ ] `auto_seed` with namespaced daemon that doesn't exist → member created, channel seeded
  - [ ] `auto_seed` with namespaced daemon where member creation fails → warn-and-skip
  - [ ] `auto_seed` re-run is idempotent
  - [ ] `admin_handler` opt-in flag works

### Schema bootstrap tests

- [ ] Create `bbsengine6/py/tests/test_checkchannel.py`: `stage_one` invokes `checkchannel.main` and lands schema on fresh DB

### CLI tests

- [ ] Create `bbsengine6/py/tests/test_cli_con.py`:
  - [ ] CLI-level tests for each `con` verb
  - [ ] Success path
  - [ ] Permission-denied path

### Casino integration tests

- [ ] Edit `casino/src/casino/tests/test_channel_integration.py`:
  - [ ] Bot-style callback (via `channel_register_callback` directly + local helper in `_support`) receives `casino:table:*` broadcasts
  - [ ] Non-announcer publish to announce-only channel is dropped
- [ ] Create `casino/src/casino/tests/test_checkchannels.py`:
  - [ ] `casino.startup.checkchannels.main` applies overrides when configured
  - [ ] Warn-and-skip when `channel_creator` absent
- [ ] Create `casino/src/casino/tests/_support/__init__.py` (empty marker)

## Verification

- [ ] Run bbsengine6 test suite:
      `cd bbsengine6/py && pytest tests/test_member_reserved.py tests/test_channel_announce_only.py tests/test_channel_admin.py tests/test_channel_config.py tests/test_checkchannel.py tests/test_cli_con.py -v`
- [ ] Run casino test suite:
      `cd casino && pytest src/casino/tests/test_checkchannels.py src/casino/tests/test_channel_integration.py -v`
- [ ] Smoke test prod bootstrap: `python -m bbsengine6 startup --databasename zoid6dev --databaseuser $USER`
- [ ] Smoke test `con`: `python -m bbsengine6 con channel-list --databasename zoid6dev --databaseuser $USER --moniker alice`
