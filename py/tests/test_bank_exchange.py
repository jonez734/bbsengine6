"""BankService.exchange: convert between coins and tokens at a whole-number ratio, in one transaction.

  exchange(moniker, amount, *, to, ratio=(num, den), token_moniker)
    to="tokens": tokens = amount * num / den; credits are debited, tokens credited.
    to="credits":  coins  = amount * den / num; tokens are debited, coins credited.

Tokens are a second balance. The token account is named by the caller through ``token_moniker`` so bbsengine6 does not
depend on any project's table. Amounts are positive integers. A conversion that is not a whole number is refused with no
change. Both balances change together or neither does.
"""

import threading
from types import SimpleNamespace

import pytest

from bbsengine6.bank.bank import BankService


@pytest.fixture(scope="function")
def test_args():
    return SimpleNamespace(debug=False, databasename="zoid6test", databasehost=None, databaseport=None,
                           databaseuser=None, databasepassword=None)


@pytest.fixture(scope="function")
def test_pool(test_args):
    """An isolated pool for this test, following test_bank.py."""
    from bbsengine6 import database
    with database.isolated_pool_cache():
        yield database.getpool(test_args, dbname=test_args.databasename)


@pytest.fixture
def bank(test_args, test_pool):
    return BankService(test_args)


@pytest.fixture
def accounts(bank):
    """A coin account and a token account, both at known balances, created in the test database."""
    coin, token = "exch_coin_jam", "exch_token_jam"
    bank.account.update_balance  # ensure the module is loaded
    for moniker, balance in ((coin, 100), (token, 0)):
        bank.add_funds(moniker, balance, transaction_type="setup", description="exchange fixture") if balance else \
            bank.account.get_or_create(moniker)
    return coin, token


def _balance(bank, moniker):
    return bank.get_balance(moniker)


class TestRefusals:
    @pytest.mark.parametrize("amount", [0, -5, 2.5, "3"])
    def test_a_non_positive_or_non_integer_amount_is_refused(self, bank, accounts, amount):
        coin, token = accounts
        before = (_balance(bank, coin), _balance(bank, token))
        result = bank.exchange(coin, amount, to="tokens", ratio=(2, 1), token_moniker=token)
        assert result["success"] is False
        assert (_balance(bank, coin), _balance(bank, token)) == before

    def test_a_non_whole_conversion_is_refused_with_no_change(self, bank, accounts):
        coin, token = accounts
        before = (_balance(bank, coin), _balance(bank, token))
        result = bank.exchange(coin, 3, to="tokens", ratio=(3, 2), token_moniker=token)  # 4.5 tokens
        assert result["success"] is False
        assert "whole" in result["message"]
        assert (_balance(bank, coin), _balance(bank, token)) == before

    def test_insufficient_coins_is_refused_with_no_change(self, bank, accounts):
        coin, token = accounts
        before = (_balance(bank, coin), _balance(bank, token))
        result = bank.exchange(coin, 10_000, to="tokens", ratio=(1, 1), token_moniker=token)
        assert result["success"] is False
        assert (_balance(bank, coin), _balance(bank, token)) == before

    def test_insufficient_tokens_is_refused_with_no_change(self, bank, accounts):
        coin, token = accounts
        before = (_balance(bank, coin), _balance(bank, token))
        result = bank.exchange(token, 10_000, to="credits", ratio=(1, 1), token_moniker=coin)
        assert result["success"] is False
        assert (_balance(bank, coin), _balance(bank, token)) == before


class TestSuccess:
    def test_coins_to_tokens_debits_coins_and_credits_tokens(self, bank, accounts):
        coin, token = accounts
        c0, t0 = _balance(bank, coin), _balance(bank, token)
        result = bank.exchange(coin, 4, to="tokens", ratio=(3, 2), token_moniker=token)  # 4 * 3 / 2 = 6
        assert result["success"] is True
        assert result["tokens"] == 6
        assert _balance(bank, coin) == c0 - 4
        assert _balance(bank, token) == t0 + 6

    def test_tokens_to_coins_debits_tokens_and_credits_coins(self, bank, accounts):
        coin, token = accounts
        bank.exchange(coin, 4, to="tokens", ratio=(3, 2), token_moniker=token)  # seed tokens
        c0, t0 = _balance(bank, coin), _balance(bank, token)
        result = bank.exchange(token, 6, to="credits", ratio=(3, 2), token_moniker=coin)  # 6 * 2 / 3 = 4
        assert result["success"] is True
        assert result["credits"] == 4
        assert _balance(bank, token) == t0 - 6
        assert _balance(bank, coin) == c0 + 4

    def test_a_successful_exchange_logs_both_sides_with_positive_amounts(self, bank, accounts):
        coin, token = accounts
        bank.exchange(coin, 2, to="tokens", ratio=(1, 1), token_moniker=token)
        out = [r for r in bank.transaction.get_history(coin, limit=5) if r.get("transactiontype") == "exchange_out"]
        inn = [r for r in bank.transaction.get_history(token, limit=5) if r.get("transactiontype") == "exchange_in"]
        assert out and inn
        assert out[0]["amount"] == 2 and inn[0]["amount"] == 2


class TestLockOrder:
    def test_opposing_exchanges_do_not_deadlock(self, bank, accounts):
        """Two exchanges in opposite directions on the same pair finish, because both take locks in account-id order."""
        coin, token = accounts
        bank.exchange(coin, 20, to="tokens", ratio=(1, 1), token_moniker=token)
        errors, done = [], []

        def forward():
            try:
                for _ in range(10):
                    bank.exchange(coin, 1, to="tokens", ratio=(1, 1), token_moniker=token)
                done.append("f")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        def backward():
            try:
                for _ in range(10):
                    bank.exchange(token, 1, to="credits", ratio=(1, 1), token_moniker=coin)
                done.append("b")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=forward), threading.Thread(target=backward)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not any(t.is_alive() for t in threads), "exchanges deadlocked"
        assert errors == []
        assert sorted(done) == ["b", "f"]
