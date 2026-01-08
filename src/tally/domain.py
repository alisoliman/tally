"""
Domain objects for Tally v1 personal finance modeling.

This module defines the core domain objects for v1 features:
- Account: Cash or investment accounts with balances
- Snapshot: Point-in-time authoritative balance records
- Plan: Recurring financial intentions (investments, savings)
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class AccountKind(Enum):
    """Type of account."""
    CASH = 'cash'           # Spendable money (checking, savings)
    INVESTMENT = 'investment'  # Owned value, not directly spendable


class PlanType(Enum):
    """Type of financial plan."""
    INVEST = 'invest'      # Transfer to investment account (v1 only)
    SAVE = 'save'          # Transfer to savings (future)
    WITHDRAW = 'withdraw'  # Planned withdrawal (future)


class Cadence(Enum):
    """Frequency of recurring plan."""
    MONTHLY = 'monthly'    # v1 only
    BIWEEKLY = 'biweekly'  # future
    WEEKLY = 'weekly'      # future
    QUARTERLY = 'quarterly'  # future
    ANNUAL = 'annual'      # future


class PlanStatus(Enum):
    """Status of a plan."""
    ACTIVE = 'active'
    PAUSED = 'paused'


@dataclass
class Account:
    """
    An account represents anything with a balance you care about.

    Attributes:
        id: Unique identifier (user-defined, e.g., "checking", "401k")
        name: Display name (e.g., "Chase Checking")
        kind: Account type (cash or investment)
        currency: ISO currency code (e.g., "USD", "EUR")
    """
    id: str
    name: str
    kind: AccountKind
    currency: str

    def __post_init__(self):
        """Validate account data."""
        if not self.id:
            raise ValueError("Account id cannot be empty")
        if not self.name:
            raise ValueError("Account name cannot be empty")
        if not self.currency:
            raise ValueError("Account currency cannot be empty")

        # Normalize currency to uppercase
        self.currency = self.currency.upper()

        # Ensure kind is AccountKind enum
        if isinstance(self.kind, str):
            self.kind = AccountKind(self.kind.lower())


@dataclass
class Snapshot:
    """
    A snapshot is an authoritative point-in-time balance for an account.

    Snapshots define the truth. The latest snapshot per account is the current balance.
    Snapshots can jump freely without reconciliation with transactions.

    Attributes:
        account_id: ID of the account this snapshot belongs to
        date: Date of the snapshot
        value: Balance amount in account currency
        note: Optional note/description
        attachment: Optional path to screenshot or statement
    """
    account_id: str
    date: date
    value: float
    note: Optional[str] = None
    attachment: Optional[str] = None

    def __post_init__(self):
        """Validate snapshot data."""
        if not self.account_id:
            raise ValueError("Snapshot account_id cannot be empty")
        if self.date is None:
            raise ValueError("Snapshot date is required")
        if self.value is None:
            raise ValueError("Snapshot value is required")

        # Ensure date is a date object
        if isinstance(self.date, str):
            # Try to parse if string
            from datetime import datetime
            try:
                self.date = datetime.strptime(self.date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Invalid date format: {self.date}. Use YYYY-MM-DD")


@dataclass
class Plan:
    """
    A plan represents recurring financial intent (future-looking).

    Plans say what SHOULD happen, not what did happen. They affect budget
    projections but don't change account balances.

    Attributes:
        id: Unique identifier (user-defined)
        type: Type of plan (invest, save, withdraw)
        from_account_id: Source account (must be cash)
        to_account_id: Destination account (for invest: must be investment)
        amount: Amount per occurrence
        currency: Currency (must match both accounts)
        cadence: Frequency (monthly, biweekly, etc.)
        start_date: When the plan starts
        status: Active or paused
    """
    id: str
    type: PlanType
    from_account_id: str
    to_account_id: str
    amount: float
    currency: str
    cadence: Cadence
    start_date: date
    status: PlanStatus

    def __post_init__(self):
        """Validate plan data."""
        if not self.id:
            raise ValueError("Plan id cannot be empty")
        if not self.from_account_id:
            raise ValueError("Plan from_account_id cannot be empty")
        if not self.to_account_id:
            raise ValueError("Plan to_account_id cannot be empty")
        if self.amount is None or self.amount <= 0:
            raise ValueError("Plan amount must be positive")
        if not self.currency:
            raise ValueError("Plan currency cannot be empty")

        # Normalize currency to uppercase
        self.currency = self.currency.upper()

        # Ensure enums
        if isinstance(self.type, str):
            self.type = PlanType(self.type.lower())
        if isinstance(self.cadence, str):
            self.cadence = Cadence(self.cadence.lower())
        if isinstance(self.status, str):
            self.status = PlanStatus(self.status.lower())

        # Ensure date is a date object
        if isinstance(self.start_date, str):
            from datetime import datetime
            try:
                self.start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Invalid date format: {self.start_date}. Use YYYY-MM-DD")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_latest_snapshot(snapshots: list[Snapshot], account_id: str,
                       as_of_date: Optional[date] = None) -> Optional[Snapshot]:
    """
    Get the latest snapshot for an account.

    Args:
        snapshots: List of all snapshots
        account_id: Account ID to find snapshot for
        as_of_date: Optional date to filter snapshots (returns latest snapshot <= this date)

    Returns:
        Latest snapshot for the account, or None if no snapshots exist
    """
    account_snapshots = [s for s in snapshots if s.account_id == account_id]

    # Filter by as_of_date if provided
    if as_of_date is not None:
        account_snapshots = [s for s in account_snapshots if s.date <= as_of_date]

    if not account_snapshots:
        return None
    return max(account_snapshots, key=lambda s: s.date)


def validate_plan_accounts(plan: Plan, accounts: list[Account]) -> list[str]:
    """
    Validate that a plan's accounts exist and are compatible.

    Args:
        plan: Plan to validate
        accounts: List of all accounts

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Build account lookup
    accounts_by_id = {a.id: a for a in accounts}

    # Check from_account exists
    from_account = accounts_by_id.get(plan.from_account_id)
    if not from_account:
        errors.append(f"Plan '{plan.id}': from_account '{plan.from_account_id}' does not exist")
        return errors  # Can't continue validation

    # Check to_account exists
    to_account = accounts_by_id.get(plan.to_account_id)
    if not to_account:
        errors.append(f"Plan '{plan.id}': to_account '{plan.to_account_id}' does not exist")
        return errors

    # Type-specific validation
    if plan.type == PlanType.INVEST:
        if from_account.kind != AccountKind.CASH:
            errors.append(f"Plan '{plan.id}': invest plans must have cash from_account (got {from_account.kind.value})")
        if to_account.kind != AccountKind.INVESTMENT:
            errors.append(f"Plan '{plan.id}': invest plans must have investment to_account (got {to_account.kind.value})")

    # Currency validation
    if from_account.currency != plan.currency:
        errors.append(f"Plan '{plan.id}': currency mismatch with from_account (plan: {plan.currency}, account: {from_account.currency})")
    if to_account.currency != plan.currency:
        errors.append(f"Plan '{plan.id}': currency mismatch with to_account (plan: {plan.currency}, account: {to_account.currency})")

    return errors
