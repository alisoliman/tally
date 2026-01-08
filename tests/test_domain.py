"""
Tests for Tally domain objects (Account, Snapshot, Plan).
"""

import pytest
from datetime import date

from tally.domain import (
    Account, Snapshot, Plan,
    AccountKind, PlanType, PlanStatus, Cadence,
    get_latest_snapshot, validate_plan_accounts
)


class TestAccount:
    """Tests for Account domain object."""

    def test_create_cash_account(self):
        """Test creating a cash account."""
        account = Account(
            id='checking',
            name='Chase Checking',
            kind=AccountKind.CASH,
            currency='USD'
        )
        assert account.id == 'checking'
        assert account.name == 'Chase Checking'
        assert account.kind == AccountKind.CASH
        assert account.currency == 'USD'

    def test_create_investment_account(self):
        """Test creating an investment account."""
        account = Account(
            id='401k',
            name='Vanguard 401(k)',
            kind=AccountKind.INVESTMENT,
            currency='USD'
        )
        assert account.id == '401k'
        assert account.kind == AccountKind.INVESTMENT

    def test_currency_normalized_to_uppercase(self):
        """Test that currency is normalized to uppercase."""
        account = Account(
            id='checking',
            name='Checking',
            kind=AccountKind.CASH,
            currency='usd'
        )
        assert account.currency == 'USD'

    def test_kind_from_string(self):
        """Test creating account with kind as string."""
        account = Account(
            id='checking',
            name='Checking',
            kind='cash',
            currency='USD'
        )
        assert account.kind == AccountKind.CASH

    def test_empty_id_raises_error(self):
        """Test that empty id raises ValueError."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Account(
                id='',
                name='Checking',
                kind=AccountKind.CASH,
                currency='USD'
            )

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Account(
                id='checking',
                name='',
                kind=AccountKind.CASH,
                currency='USD'
            )

    def test_empty_currency_raises_error(self):
        """Test that empty currency raises ValueError."""
        with pytest.raises(ValueError, match="currency cannot be empty"):
            Account(
                id='checking',
                name='Checking',
                kind=AccountKind.CASH,
                currency=''
            )

    def test_multi_currency_accounts(self):
        """Test creating accounts with different currencies."""
        usd_account = Account(id='usd', name='USD Account', kind=AccountKind.CASH, currency='USD')
        eur_account = Account(id='eur', name='EUR Account', kind=AccountKind.CASH, currency='EUR')
        gbp_account = Account(id='gbp', name='GBP Account', kind=AccountKind.CASH, currency='GBP')

        assert usd_account.currency == 'USD'
        assert eur_account.currency == 'EUR'
        assert gbp_account.currency == 'GBP'


class TestSnapshot:
    """Tests for Snapshot domain object."""

    def test_create_snapshot(self):
        """Test creating a snapshot."""
        snapshot = Snapshot(
            account_id='checking',
            date=date(2025, 1, 8),
            value=5432.10,
            note='Starting balance'
        )
        assert snapshot.account_id == 'checking'
        assert snapshot.date == date(2025, 1, 8)
        assert snapshot.value == 5432.10
        assert snapshot.note == 'Starting balance'
        assert snapshot.attachment is None

    def test_snapshot_with_attachment(self):
        """Test snapshot with attachment path."""
        snapshot = Snapshot(
            account_id='checking',
            date=date(2025, 1, 8),
            value=5432.10,
            attachment='screenshots/checking.png'
        )
        assert snapshot.attachment == 'screenshots/checking.png'

    def test_snapshot_from_string_date(self):
        """Test creating snapshot with date as string."""
        snapshot = Snapshot(
            account_id='checking',
            date='2025-01-08',
            value=5432.10
        )
        assert snapshot.date == date(2025, 1, 8)

    def test_invalid_date_format_raises_error(self):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            Snapshot(
                account_id='checking',
                date='01/08/2025',  # Wrong format
                value=5432.10
            )

    def test_empty_account_id_raises_error(self):
        """Test that empty account_id raises ValueError."""
        with pytest.raises(ValueError, match="account_id cannot be empty"):
            Snapshot(
                account_id='',
                date=date(2025, 1, 8),
                value=5432.10
            )

    def test_negative_value_allowed(self):
        """Test that negative snapshot values are allowed (overdrafts)."""
        snapshot = Snapshot(
            account_id='checking',
            date=date(2025, 1, 8),
            value=-150.00,
            note='Overdraft'
        )
        assert snapshot.value == -150.00


class TestPlan:
    """Tests for Plan domain object."""

    def test_create_investment_plan(self):
        """Test creating an investment plan."""
        plan = Plan(
            id='401k-monthly',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        assert plan.id == '401k-monthly'
        assert plan.type == PlanType.INVEST
        assert plan.from_account_id == 'checking'
        assert plan.to_account_id == '401k'
        assert plan.amount == 500.00
        assert plan.currency == 'USD'
        assert plan.cadence == Cadence.MONTHLY
        assert plan.status == PlanStatus.ACTIVE

    def test_plan_from_strings(self):
        """Test creating plan with enums as strings."""
        plan = Plan(
            id='401k',
            type='invest',
            from_account_id='checking',
            to_account_id='401k',
            amount=500.00,
            currency='usd',
            cadence='monthly',
            start_date='2025-01-01',
            status='active'
        )
        assert plan.type == PlanType.INVEST
        assert plan.cadence == Cadence.MONTHLY
        assert plan.status == PlanStatus.ACTIVE
        assert plan.currency == 'USD'
        assert plan.start_date == date(2025, 1, 1)

    def test_paused_plan(self):
        """Test creating a paused plan."""
        plan = Plan(
            id='ira',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='ira',
            amount=250.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.PAUSED
        )
        assert plan.status == PlanStatus.PAUSED

    def test_zero_amount_raises_error(self):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="amount must be positive"):
            Plan(
                id='401k',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='401k',
                amount=0.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 1),
                status=PlanStatus.ACTIVE
            )

    def test_negative_amount_raises_error(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="amount must be positive"):
            Plan(
                id='401k',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='401k',
                amount=-500.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 1),
                status=PlanStatus.ACTIVE
            )


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot utility function."""

    def test_get_latest_snapshot(self):
        """Test getting the latest snapshot for an account."""
        snapshots = [
            Snapshot('checking', date(2025, 1, 1), 1000.00),
            Snapshot('checking', date(2025, 1, 8), 1200.00),
            Snapshot('checking', date(2025, 1, 5), 1100.00),
        ]
        latest = get_latest_snapshot(snapshots, 'checking')
        assert latest.date == date(2025, 1, 8)
        assert latest.value == 1200.00

    def test_get_latest_snapshot_no_snapshots(self):
        """Test getting latest snapshot when none exist."""
        snapshots = []
        latest = get_latest_snapshot(snapshots, 'checking')
        assert latest is None

    def test_get_latest_snapshot_different_account(self):
        """Test getting latest snapshot for different account."""
        snapshots = [
            Snapshot('checking', date(2025, 1, 8), 1200.00),
            Snapshot('savings', date(2025, 1, 1), 5000.00),
        ]
        latest = get_latest_snapshot(snapshots, 'savings')
        assert latest.account_id == 'savings'
        assert latest.value == 5000.00

    def test_get_latest_snapshot_multiple_accounts(self):
        """Test getting latest snapshot with multiple accounts."""
        snapshots = [
            Snapshot('checking', date(2025, 1, 1), 1000.00),
            Snapshot('savings', date(2025, 1, 1), 5000.00),
            Snapshot('checking', date(2025, 1, 8), 1200.00),
        ]
        checking_latest = get_latest_snapshot(snapshots, 'checking')
        savings_latest = get_latest_snapshot(snapshots, 'savings')

        assert checking_latest.value == 1200.00
        assert savings_latest.value == 5000.00

    def test_get_latest_snapshot_with_as_of_date(self):
        """Test getting latest snapshot as of a specific date."""
        snapshots = [
            Snapshot('checking', date(2025, 1, 1), 1000.00),
            Snapshot('checking', date(2025, 1, 8), 1200.00),
            Snapshot('checking', date(2025, 1, 15), 1300.00),
        ]
        # Get latest snapshot as of Jan 10
        latest = get_latest_snapshot(snapshots, 'checking', as_of_date=date(2025, 1, 10))
        assert latest.date == date(2025, 1, 8)
        assert latest.value == 1200.00

    def test_get_latest_snapshot_as_of_date_no_match(self):
        """Test getting latest snapshot when as_of_date is before all snapshots."""
        snapshots = [
            Snapshot('checking', date(2025, 1, 8), 1200.00),
            Snapshot('checking', date(2025, 1, 15), 1300.00),
        ]
        # Get latest snapshot as of Jan 1 (before any snapshots)
        latest = get_latest_snapshot(snapshots, 'checking', as_of_date=date(2025, 1, 1))
        assert latest is None


class TestValidatePlanAccounts:
    """Tests for validate_plan_accounts utility function."""

    def test_valid_investment_plan(self):
        """Test validation passes for valid investment plan."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'USD'),
            Account('401k', '401(k)', AccountKind.INVESTMENT, 'USD'),
        ]
        plan = Plan(
            id='401k-monthly',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 0

    def test_missing_from_account(self):
        """Test validation fails when from_account doesn't exist."""
        accounts = [
            Account('401k', '401(k)', AccountKind.INVESTMENT, 'USD'),
        ]
        plan = Plan(
            id='401k',
            type=PlanType.INVEST,
            from_account_id='checking',  # Doesn't exist
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "from_account 'checking' does not exist" in errors[0]

    def test_missing_to_account(self):
        """Test validation fails when to_account doesn't exist."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'USD'),
        ]
        plan = Plan(
            id='401k',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='401k',  # Doesn't exist
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "to_account '401k' does not exist" in errors[0]

    def test_invest_plan_requires_cash_from_account(self):
        """Test invest plan must have cash from_account."""
        accounts = [
            Account('brokerage', 'Brokerage', AccountKind.INVESTMENT, 'USD'),
            Account('401k', '401(k)', AccountKind.INVESTMENT, 'USD'),
        ]
        plan = Plan(
            id='transfer',
            type=PlanType.INVEST,
            from_account_id='brokerage',  # Investment account
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "must have cash from_account" in errors[0]

    def test_invest_plan_requires_investment_to_account(self):
        """Test invest plan must have investment to_account."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'USD'),
            Account('savings', 'Savings', AccountKind.CASH, 'USD'),
        ]
        plan = Plan(
            id='transfer',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',  # Cash account
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "must have investment to_account" in errors[0]

    def test_currency_mismatch_from_account(self):
        """Test validation fails when plan currency doesn't match from_account."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'EUR'),
            Account('401k', '401(k)', AccountKind.INVESTMENT, 'USD'),
        ]
        plan = Plan(
            id='401k',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "currency mismatch with from_account" in errors[0]

    def test_currency_mismatch_to_account(self):
        """Test validation fails when plan currency doesn't match to_account."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'USD'),
            Account('401k', '401(k)', AccountKind.INVESTMENT, 'EUR'),
        ]
        plan = Plan(
            id='401k',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='401k',
            amount=500.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        assert len(errors) == 1
        assert "currency mismatch with to_account" in errors[0]

    def test_multiple_validation_errors(self):
        """Test that all validation errors are returned."""
        accounts = [
            Account('checking', 'Checking', AccountKind.CASH, 'EUR'),
            Account('savings', 'Savings', AccountKind.CASH, 'USD'),
        ]
        plan = Plan(
            id='bad-plan',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',  # Wrong kind
            amount=500.00,
            currency='USD',  # Wrong currency
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )
        errors = validate_plan_accounts(plan, accounts)
        # Should have multiple errors: wrong to_account kind and currency mismatch
        assert len(errors) >= 2
