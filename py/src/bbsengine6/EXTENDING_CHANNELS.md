# Extending bbsengine6 channels

This guide is for module authors (empyre, zoidoffice, murdermotel, etc.)
who want to use the channel pub/sub system from their own module.
bbsengine6 does not need to change to onboard a new module — the
existing primitives in `bbsengine6.net` and the namespacing convention
are designed to be reused.

## 1. Accept a shared `channel_state` in your router's `__init__`

bed.main.BED.start constructs one `ChannelState()` per daemon and passes
it to both the WebSocketServer and the message router. Mirror that
shape in your `MessageRouter.__init__`:

```python
class MessageRouter:
    def __init__(self, args, *, channel_state=None, server=None, config=None, **kwargs):
        self.args = args
        self.channel_state = channel_state or ChannelState()
        self.server = server
        self.config = config or {}  # services.<module> dict from zoid6.json
```

When bed constructs your router it will pass the shared state; the
TypeError fallback in zoid6.api.handler._register_module keeps older
routers working when they only take `args`.

## 2. Plumb `sender_moniker` through `server.publish`

The announce-only enforcement at `bbsengine6.services.channel.ChannelService.can_publish`
only fires when `channel_publish` is given a sender. Without it, the
verdict is always "Channel not found" for unconfigured channels (or
"Channel is open" for configured ones) — fine for open channels,
silently broken for announce-only ones.

Use `channel_publish` directly instead of `server.publish`:

```python
from bbsengine6.net import channel_publish
from bbsengine6.channel.naming import table_channel

async def publish_state(self, table_moniker, state, sender_moniker):
    await channel_publish(
        self.channel_state,
        table_channel("myapp", table_moniker),  # myapp:table:<moniker>
        state,
        server=self.server,
        sender_moniker=sender_moniker,
        args=self.args,
    )
```

## 3. Use namespaced daemon members for service identities

If your module needs a daemon identity (e.g., for auto-seeded channels
whose `createdby` must be a real `engine.__member` row), use a
namespaced moniker of the form `<your-module>:<purpose>`:

```python
from bbsengine6.member.lib import register_module_member

register_module_member(args, "myapp:router")
# creates engine.__member row with moniker "myapp:router"
```

The standard registration path (`console member add`, `libmember.insert`)
rejects namespaced monikers; `register_module_member` is the only path
that accepts them. It also enforces lowercase and shape, so callers
can't accidentally create an invalid row.

bbsengine6 only reserves the four shipped PostgreSQL role names
(`sysop`, `term`, `web`, `bed`) — your module prefix is not reserved
unless you add it to `RESERVED_MONIKERS` in your own fork or wrap it
in your own registration gating.

## 4. Add entries to `bed.json`'s channel.auto_seed list

The channel router runs the auto-seed step at register time:

```jsonc
{
  "channel": {
    "auto_seed": [
      {
        "name": "myapp:global",
        "createdby": "myapp:router",
        "announce_only": false,
        "description": "myapp-wide announcements (open publishing)"
      },
      {
        "name": "system:announcements",
        "createdby": "myapp:router",
        "announce_only": true,
        "announcers": ["sysop"],
        "description": "System-wide announcements (sysop-only)"
      }
    ]
  }
}
```

The seed step is best-effort: if the daemon member can't be created
(insufficient permissions, missing FK, etc.) it warns-and-skips. The
daemon never fails to start because of a seed miss.

## 5. Read per-module config from `args.config_file`

zoid6's `MessageRouter._register_module` forwards `module_config` to
your router constructor (added in Phase 7). Use it for per-module
settings:

```python
def __init__(self, args, *, config=None, **kwargs):
    self.config = config or {}
    self.some_feature_flag = self.config.get("some_feature_flag", False)
```

The config dict is the `services.<module>` entry from `zoid6.json`. To
disable your module at the router level, set `"enabled": false` in
that entry — the dispatch code at `zoid6.api.handler._register_module`
already skips disabled modules.

## 6. Use the naming helpers for channel literals

Inline `f"myapp:table:{moniker}"` is fragile — a future rename is a
grep-and-replace across every module. Use the helpers in
`bbsengine6.channel.naming`:

```python
from bbsengine6.channel.naming import (
    table_channel, member_channel, global_channel,
    announcement_channel, parse_channel,
)

ch = table_channel("myapp", "lobby-1")  # "myapp:table:lobby-1"
app, kind, id_ = parse_channel(ch)  # ("myapp", "table", "lobby-1")
```

## 7. ChannelAdminHandler opt-in

If you want operators to manage your channels via `con channel-*`,
the WS-side `ChannelAdminHandler` is already generic — no per-module
work needed. Just make sure `bed.json`'s `channel.admin_handler.enabled`
is `true` (the default in the shipped config). The handler reads the
acting moniker from the session and threads it through
`ChannelService._require_authority`, so sysops and channel creators
get the right access; everyone else gets a permission-denied error.

## What bbsengine6 doesn't do for you

- **Schema migration** is your responsibility. The shipped `channel.sql`
  defines `engine.__channel` and `engine.__channel_announcer`; if
  your module needs additional persistent state, add your own SQL and
  wire it into your module's `startup` chain (mirroring how
  `casino.startup.checkchannels` works).
- **Authorization rules beyond sysop/creator.** `ChannelService._require_authority`
  allows sysop OR `createdby == actor`. If your module needs finer
  controls (e.g., per-table moderators), add your own gate before
  calling `ChannelService` mutators, or fork `_require_authority`.
- **Per-module channel subscriptions.** The subscription handler in
  `bbsengine6.channel.api.handler.ChannelServiceHandler` is already
  generic — clients send `{"type": "subscribe_channel", "channel": "<name>"}`
  and the server tracks subscriptions in the shared `ChannelState`.
  Your module doesn't need its own subscribe verb.
