"""
Integration tests for bank module CRUD operations.
Uses the zoid6test database with automatic transaction rollback.
"""

import argparse
import pytest
import getpass

from bbsengine6 import database
from bbsengine6.bank import Account, Transaction, Transfer, BankService


def make_test_args(databasename: str = "zoid6test"):
    """Create test args object for bank operations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


@pytest.fixture(scope="function")
def test_args():
    """Create test args for bank tests."""
    return make_test_args()


@pytest.fixture(scope="function")
def test_pool(test_args):
    """Create test pool for bank tests."""
    pool = database.getpool(test_args, dbname=test_args.databasename)
    yield pool
    database.reset_pool_cache()


@pytest.fixture(autouse=True)
def cleanup_test_accounts(db_connection):
    """Clean up test accounts before and after each test."""
    user = getpass.getuser()
    test_monikers = [
        f"test_{user}_1",
        f"test_{user}_2",
        f"test_{user}_3",
    ]
    
    with db_connection.cursor() as cur:
        for moniker in test_monikers:
            cur.execute("DELETE FROM bank.__transfer WHERE fromaccountid IN (SELECT id FROM bank.__account WHERE moniker = %s) OR toaccountid IN (SELECT id FROM bank.__account WHERE moniker = %s)", (moniker, moniker))
            cur.execute("DELETE FROM bank.__transaction WHERE accountid IN (SELECT id FROM bank.__account WHERE moniker = %s)", (moniker,))
            cur.execute("DELETE FROM bank.__account WHERE moniker = %s", (moniker,))
    db_connection.commit()
    
    yield
    
    with db_connection.cursor() as cur:
        for moniker in test_monikers:
            cur.execute("DELETE FROM bank.__transfer WHERE fromaccountid IN (SELECT id FROM bank.__account WHERE moniker = %s) OR toaccountid IN (SELECT id FROM bank.__account WHERE moniker = %s)", (moniker, moniker))
            cur.execute("DELETE FROM bank.__transaction WHERE accountid IN (SELECT id FROM bank.__account WHERE moniker = %s)", (moniker,))
            cur.execute("DELETE FROM bank.__account WHERE moniker = %s", (moniker,))
    db_connection.commit()


class TestAccountCrud:
    """Test Account CRUD operations."""

    def test_create_account(self, test_args, test_pool):
        """Test creating a new account."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        result = account.get_or_create(moniker, initial_balance=1000)

        assert result is not None
        assert result["moniker"] == moniker
        assert result["balance"] == 1000
        assert result["minbalance"] == 0
        assert result["maxtransfer"] == 1000

    def test_get_existing_account(self, test_args, test_pool):
        """Test getting an existing account."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=500)
        result = account.get(moniker)

        assert result is not None
        assert result["moniker"] == moniker
        assert result["balance"] == 500

    def test_get_nonexistent_account(self, test_args, test_pool):
        """Test getting a non-existent account returns None."""
        account = Account(test_args)

        result = account.get("nonexistent_user_12345")

        assert result is None

    def test_get_by_id(self, test_args, test_pool):
        """Test getting account by ID."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        created = account.get_or_create(moniker, initial_balance=100)
        result = account.get_by_id(created["id"])

        assert result is not None
        assert result["moniker"] == moniker
        assert result["balance"] == 100

    def test_get_balance(self, test_args, test_pool):
        """Test getting account balance."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=2500)
        balance = account.get_balance(moniker)

        assert balance == 2500

    def test_get_balance_nonexistent(self, test_args, test_pool):
        """Test getting balance for non-existent account returns 0."""
        account = Account(test_args)

        balance = account.get_balance("nonexistent_user_12345")

        assert balance == 0

    def test_update_balance(self, test_args, test_pool):
        """Test updating account balance."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=100)
        result = account.update_balance(moniker, 500)

        assert result is True

        updated = account.get(moniker)
        assert updated["balance"] == 500

    def test_update_settings(self, test_args, test_pool):
        """Test updating account settings."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=100)
        result = account.update_settings(moniker, minbalance=50, maxtransfer=5000)

        assert result is not None
        assert result["minbalance"] == 50
        assert result["maxtransfer"] == 5000


class TestTransactionCrud:
    """Test Transaction CRUD operations."""

    def test_add_transaction(self, test_args, test_pool):
        """Test adding a transaction."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        transaction = Transaction(test_args)

        account = Account(test_args)
        account.get_or_create(moniker, initial_balance=1000)

        result = transaction.add(
            moniker,
            amount=100,
            transaction_type="credit",
            description="Test deposit",
            member_moniker=user,
        )

        assert result is not None
        assert result["amount"] == 100
        assert result["transactiontype"] == "credit"
        assert result["description"] == "Test deposit"

    def test_add_transaction_nonexistent_account(self, test_args, test_pool):
        """Test adding transaction to non-existent account returns None."""
        transaction = Transaction(test_args)

        result = transaction.add(
            "nonexistent_user_12345",
            amount=100,
            transaction_type="credit",
            description="Test",
        )

        assert result is None

    def test_get_history(self, test_args, test_pool):
        """Test getting transaction history."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        transaction = Transaction(test_args)
        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=1000)
        transaction.add(moniker, 100, "credit", "Deposit 1")
        transaction.add(moniker, 50, "debit", "Withdrawal 1")
        transaction.add(moniker, 200, "credit", "Deposit 2")

        history = transaction.get_history(moniker, limit=10)

        assert len(history) == 3
        assert history[0]["amount"] == 200
        assert history[1]["amount"] == 50
        assert history[2]["amount"] == 100


class TestTransferCrud:
    """Test Transfer CRUD operations."""

    def test_create_transfer(self, test_args, test_pool):
        """Test creating a pending transfer."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker1, initial_balance=1000)
        account.get_or_create(moniker2, initial_balance=0)

        result = transfer.create(moniker1, moniker2, 100, user)

        assert result["success"] is True
        assert "transfer_id" in result

    def test_create_transfer_same_account_fails(self, test_args, test_pool):
        """Test that transferring to same account fails."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker, initial_balance=1000)

        result = transfer.create(moniker, moniker, 100, user)

        assert result["success"] is False
        assert "Cannot transfer to same account" in result["message"]

    def test_create_transfer_insufficient_funds(self, test_args, test_pool):
        """Test that transfer fails with insufficient funds."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker1, initial_balance=50)
        account.get_or_create(moniker2, initial_balance=0)

        result = transfer.create(moniker1, moniker2, 100, user)

        assert result["success"] is False
        assert "Insufficient funds" in result["message"]

    def test_approve_transfer(self, test_args, test_pool):
        """Test approving a pending transfer."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker1, initial_balance=1000)
        account.get_or_create(moniker2, initial_balance=0)

        create_result = transfer.create(moniker1, moniker2, 100, user)
        transfer_id = create_result["transfer_id"]

        approve_result = transfer.approve(transfer_id, user)

        assert approve_result["success"] is True
        assert approve_result["from_balance"] == 900
        assert approve_result["to_balance"] == 100

    def test_reject_transfer(self, test_args, test_pool):
        """Test rejecting a pending transfer."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker1, initial_balance=1000)
        account.get_or_create(moniker2, initial_balance=0)

        create_result = transfer.create(moniker1, moniker2, 100, user)
        transfer_id = create_result["transfer_id"]

        reject_result = transfer.reject(transfer_id, user)

        assert reject_result["success"] is True

    def test_get_pending_transfers(self, test_args, test_pool):
        """Test getting pending transfers."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        transfer = Transfer(test_args)
        account = Account(test_args)

        account.get_or_create(moniker1, initial_balance=1000)
        account.get_or_create(moniker2, initial_balance=0)

        transfer.create(moniker1, moniker2, 50, user)
        transfer.create(moniker1, moniker2, 75, user)

        pending = transfer.get_pending(moniker1)

        assert len(pending) == 2


class TestBankService:
    """Test BankService combining all operations."""

    def test_add_funds(self, test_args, test_pool):
        """Test adding funds via BankService."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=100)
        result = bank.add_funds(moniker, 200, description="Test deposit")

        assert result["success"] is True
        assert result["new_balance"] == 300

    def test_add_funds_negative_fails(self, test_args, test_pool):
        """Test that adding negative funds fails."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=100)
        result = bank.add_funds(moniker, -50)

        assert result["success"] is False

    def test_remove_funds(self, test_args, test_pool):
        """Test removing funds via BankService."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=500)
        result = bank.remove_funds(moniker, 100, description="Test withdrawal")

        assert result["success"] is True
        assert result["new_balance"] == 400

    def test_remove_funds_insufficient(self, test_args, test_pool):
        """Test that removing more than balance fails."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=100)
        result = bank.remove_funds(moniker, 200)

        assert result["success"] is False
        assert "Insufficient funds" in result["message"]

    def test_get_balance(self, test_args, test_pool):
        """Test getting balance via BankService."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=750)
        balance = bank.get_balance(moniker)

        assert balance == 750

    def test_full_transfer_flow(self, test_args, test_pool):
        """Test complete transfer flow: create, approve, verify balances."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker1, initial_balance=1000)
        bank.account.get_or_create(moniker2, initial_balance=0)

        create_result = bank.transfer(moniker1, moniker2, 250, user)
        assert create_result["success"] is True

        transfer_id = create_result["transfer_id"]

        approve_result = bank.approve_transfer(transfer_id, user)
        assert approve_result["success"] is True

        assert bank.get_balance(moniker1) == 750
        assert bank.get_balance(moniker2) == 250

    def test_get_history(self, test_args, test_pool):
        """Test getting transaction history via BankService."""
        user = getpass.getuser()
        moniker = f"test_{user}_1"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker, initial_balance=1000)
        bank.add_funds(moniker, 100, description="Deposit 1")
        bank.add_funds(moniker, 200, description="Deposit 2")
        bank.remove_funds(moniker, 50, description="Withdrawal")

        history = bank.get_history(moniker)

        assert len(history) == 3

    def test_get_pending_transfers(self, test_args, test_pool):
        """Test getting pending transfers via BankService."""
        user = getpass.getuser()
        moniker1 = f"test_{user}_1"
        moniker2 = f"test_{user}_2"

        bank = BankService(test_args)

        bank.account.get_or_create(moniker1, initial_balance=1000)
        bank.account.get_or_create(moniker2, initial_balance=0)

        bank.transfer(moniker1, moniker2, 100, user)
        bank.transfer(moniker1, moniker2, 150, user)

        pending = bank.get_pending_transfers(moniker1)

        assert len(pending) == 2
