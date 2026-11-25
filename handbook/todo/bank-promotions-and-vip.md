# bank: promotions and VIP players (not started)

Status: planned. Nothing has been built. Depends on the fixed 1:1 exchange in casino (`CasinoBankService`,
casino `2eb2865`). Empyre's `EXCHANGE_RATIO = (2, 1)` is a placeholder and is not part of this work.

Goal: let the bank offer temporary promotions and let some players hold VIP status that changes their rate.

## Requirements

- **Promotions**: a time-limited rate change, for all players or a named group. A promotion has a start and end,
  a rate `(num, den)`, and an optional audience. It ends on its own without a manual step.
- **VIP players**: a player can be marked VIP. A VIP player gets a better rate than the standard one.
  VIP status is granted and revoked by a named role (sysop), not by the player.
- **Audit**: every exchange records the rate used, so a transaction can be explained later.
- **Precedence** (to decide): when a VIP player is also inside a promotion, which rate applies?

## Steps

- [ ] Decide the rules (see Questions) and write them into `handbook/specs/bank.md`.
- [ ] Tests first: rate resolution (standard, VIP, promotion, both, expired promotion), against `zoid6test` only.
- [ ] Storage: a VIP flag or tier table and a promotion table, in the owning project's `sql/` (not `zoid6`).
- [ ] Record the rate used on each exchange transaction.
- [ ] Grant and revoke VIP through a sysop-only path, with a test that a non-sysop cannot.
- [ ] Apply to live `zoid6` only after review and an explicit go-ahead.

## Questions

1. Precedence: does a VIP rate beat a promotion, does a promotion beat a VIP rate, or is the better one used?
2. Is a VIP rate per player (a tier table) or a single VIP rate for all VIP players?
3. Can a promotion target only VIP players, or only non-VIP players?
4. Who may grant or revoke VIP: sysop only, or table owners too?
5. Should the rate ever be below 1:1 for a player (a penalty)? If not, the floor is 1:1.

## Risks

- A wrong rate or an unbounded promotion can mint or destroy coins. Cap promotion length and rate, and log every change.
- The per-player rate removed in casino `40cfe7b` was never used. Bring it back only through this plan.
