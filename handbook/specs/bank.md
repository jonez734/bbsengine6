# bbsengine6 bank: ledger, units, and conversion

> Status: canonical for the ledger and `exchange`. The currency design in the last section is a
> requirement, not built. Updated 2026-11-25.

This spec covers the bank ledger, what a balance means, the `exchange` operation, and what a
multi-currency bank would need. Authorization of bank requests (who may call which operation) is
in [auth-bank.md](./auth-bank.md).

## The ledger

- `bank.__account`: one row per moniker. Columns that matter here: `id`, `moniker`, `balance`
  (numeric), `minbalance`, `maxtransfer`, `overdraft_limit`, `attrs` (jsonb), `created`.
- `bank.__transaction`: one row per balance change. `accountid`, `amount` (always a positive
  number), `transactiontype` (a label such as `credit`, `debit`, `exchange_out`, `exchange_in`),
  `description`, `membermoniker`.
- `bank.__transfer`: a transfer **request** that needs approval before anything moves.

**A balance is in credits.** `balance` is the system bank's credit balance, one implicit currency.
The ledger cannot hold two currencies today. Every operation that changes `balance` writes a
`__transaction` row, with the amount as a positive number and the direction in `transactiontype`.
Games keep their own currency (empyre's coins, priced in credits) outside the ledger.

## Operations

| Operation | Moves value? | Notes |
|---|---|---|
| `add_funds` / `remove_funds` | yes, one account | Writes one transaction row. Refuses non-positive amounts. |
| `transfer` | no, creates a request | Needs `approve_transfer`. Never moves tokens by itself. |
| `exchange` | yes, two accounts | Converts between credits and tokens at a fixed ratio, in one transaction. |

### `exchange`

```
BankService.exchange(moniker, amount, *, to, ratio=(num, den), token_moniker)
```

- `to="tokens"`: debit `amount` credits from `moniker`; credit `amount * num / den` tokens to
  `token_moniker`.
- `to="coins"`: debit `amount` tokens from `moniker`; credit `amount * den / num` credits to
  `token_moniker`.
- `ratio` is `(num, den)`: `num` tokens for every `den` credits. Both are positive integers, and the
  **caller** supplies the ratio. The bank does not hold a rate.
- `amount` must be a positive integer.
- The result must be a whole number. If `amount * num` (or `amount * den`) is not divisible, the call
  is refused with no change. There is no rounding.
- Both account rows are locked `FOR UPDATE` in ascending `id` order, so two opposing exchanges cannot
  deadlock. Every check runs before any write. Both sides log an `exchange_out` / `exchange_in` row.
- The token side is named by `token_moniker`. The bank does not depend on any project's table.

Callers own their rates. `empyre.player.EXCHANGE_RATIO` is empyre's rate for its coins against
the bank's tokens; casino's per-player rate is `casino.__bank_player.ratio_num / ratio_den`.
The ledger side of every exchange is a credit balance, so "credits" is the name the bank uses.

## Why exchange is not a transfer

`transfer` is a request that waits for approval, so it is the right tool for moving value between
players. `exchange` converts between units immediately and is the only operation that changes two
accounts in one call. The two never share a code path, so an unapproved transfer cannot move tokens.

## Future: more than one currency

The bank will need to accept currencies beyond coins and tokens (for example BTC or ETH). That is a
requirement, not a current feature. A multi-currency design needs three things the bank does not have:

1. **A currency identity on every balance.** `bank.__account` has no unit column. Either add a
   `currency` column (with the account keyed by `(moniker, currency)`), or one account per currency.
   Until this exists, a balance of 100 is 100 of "the" currency, and no conversion is meaningful.
   This is the foundation; do it first.

2. **A rate source, recorded.** A fixed ratio is a constant the caller owns. A market price changes,
   so a conversion must reference a specific rate that was in effect at a specific time. The rate
   record needs: the pair (`from_currency`, `to_currency`), the price, its timestamp, and its source.
   A conversion stores the rate it used, so it can be audited. Policy for stale rates (refuse, or
   use the last known, with a limit) is decided before the feed is built.

3. **Precision and rounding per currency.** Coins and tokens are whole numbers, so the whole-number
   rule is exact. Crypto has its own precision (satoshis, wei) and market prices are decimals, so
   most real conversions are not whole. The rounding policy (round down, round to nearest, or
   refuse) and the minimum unit per currency must be fixed before the arithmetic is written. The
   current `exchange` rule (refuse non-whole results) is the strictest choice and remains correct for
   fixed-ratio units.

### Proposed order

1. Add the currency column (or per-currency accounts) and keep every existing row as the current
   unit. No behaviour change.
2. Add a rate record table with the fields in (2), and an operator or feed writer. No conversion yet.
3. Generalise `exchange` to take a rate record and a rounding policy, with the fixed-ratio case as
   one policy. Existing callers keep the whole-number rule.
4. Add the market-rate source and its staleness policy.

Each step is independently shippable and testable. Step 3 must not change any existing caller's result.

## Open questions

- The ledger's unit is credits (recorded here). Naming it `currency = 'credits'` is step 1 of the
  currency migration.
- Should a conversion to crypto be a separate operation (`convert`) or the same `exchange` with a
  currency argument? Using one operation keeps the audit trail in one place.
- Who may set a fixed rate, and where is that authority recorded? Today empyre's constant is code,
  which is reviewed. A stored rate needs an access rule and an audit row.
