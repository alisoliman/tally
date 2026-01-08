"""
Tests for accounts_loader module (loading accounts, snapshots, plans from YAML).
"""

import pytest
import os
import tempfile
from datetime import date

from tally.accounts_loader import (
    load_accounts, load_snapshots, load_plans, load_personal_finance_config
)
from tally.domain import AccountKind, PlanType, PlanStatus, Cadence


class TestLoadAccounts:
    """Tests for load_accounts function."""

    def test_load_accounts_from_yaml(self, tmp_path):
        """Test loading accounts from YAML file."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Chase Checking
    kind: cash
    currency: USD
  - id: 401k
    name: Vanguard 401(k)
    kind: investment
    currency: USD
""")

        accounts = load_accounts(str(tmp_path), 'accounts.yaml')

        assert len(accounts) == 2
        assert accounts[0].id == 'checking'
        assert accounts[0].name == 'Chase Checking'
        assert accounts[0].kind == AccountKind.CASH
        assert accounts[0].currency == 'USD'

        assert accounts[1].id == '401k'
        assert accounts[1].kind == AccountKind.INVESTMENT

    def test_load_accounts_empty_file(self, tmp_path):
        """Test loading from empty YAML file returns empty list."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("")

        accounts = load_accounts(str(tmp_path), 'accounts.yaml')
        assert accounts == []

    def test_load_accounts_missing_file(self, tmp_path):
        """Test loading from missing file returns empty list."""
        accounts = load_accounts(str(tmp_path), 'accounts.yaml')
        assert accounts == []

    def test_load_accounts_multi_currency(self, tmp_path):
        """Test loading accounts with different currencies."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: usd-checking
    name: USD Checking
    kind: cash
    currency: USD
  - id: eur-checking
    name: EUR Checking
    kind: cash
    currency: EUR
  - id: gbp-savings
    name: GBP Savings
    kind: cash
    currency: GBP
""")

        accounts = load_accounts(str(tmp_path), 'accounts.yaml')

        assert len(accounts) == 3
        assert accounts[0].currency == 'USD'
        assert accounts[1].currency == 'EUR'
        assert accounts[2].currency == 'GBP'

    def test_load_accounts_missing_required_field(self, tmp_path):
        """Test that missing required field raises ValueError."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Checking
    # Missing: kind
    currency: USD
""")

        with pytest.raises(ValueError, match="'kind' is required"):
            load_accounts(str(tmp_path), 'accounts.yaml')

    def test_load_accounts_invalid_kind(self, tmp_path):
        """Test that invalid account kind raises ValueError."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Checking
    kind: invalid_kind
    currency: USD
""")

        with pytest.raises(ValueError):
            load_accounts(str(tmp_path), 'accounts.yaml')


class TestLoadSnapshots:
    """Tests for load_snapshots function."""

    def test_load_snapshots_from_yaml(self, tmp_path):
        """Test loading snapshots from YAML file."""
        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("""
snapshots:
  - account: checking
    date: 2025-01-01
    value: 1000.00
    note: "Starting balance"
  - account: checking
    date: 2025-01-08
    value: 1200.00
  - account: savings
    date: 2025-01-01
    value: 5000.00
    attachment: screenshots/savings.png
""")

        snapshots = load_snapshots(str(tmp_path), 'snapshots.yaml')

        assert len(snapshots) == 3
        assert snapshots[0].account_id == 'checking'
        assert snapshots[0].date == date(2025, 1, 1)
        assert snapshots[0].value == 1000.00
        assert snapshots[0].note == "Starting balance"

        assert snapshots[2].attachment == "screenshots/savings.png"

    def test_load_snapshots_empty_file(self, tmp_path):
        """Test loading from empty file returns empty list."""
        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("")

        snapshots = load_snapshots(str(tmp_path), 'snapshots.yaml')
        assert snapshots == []

    def test_load_snapshots_missing_file(self, tmp_path):
        """Test loading from missing file returns empty list."""
        snapshots = load_snapshots(str(tmp_path), 'snapshots.yaml')
        assert snapshots == []

    def test_load_snapshots_invalid_date_format(self, tmp_path):
        """Test that invalid date format raises ValueError."""
        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("""
snapshots:
  - account: checking
    date: 01/08/2025
    value: 1000.00
""")

        with pytest.raises(ValueError, match="Invalid date format"):
            load_snapshots(str(tmp_path), 'snapshots.yaml')

    def test_load_snapshots_missing_required_field(self, tmp_path):
        """Test that missing required field raises ValueError."""
        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("""
snapshots:
  - account: checking
    # Missing: date
    value: 1000.00
""")

        with pytest.raises(ValueError, match="'date' is required"):
            load_snapshots(str(tmp_path), 'snapshots.yaml')


class TestLoadPlans:
    """Tests for load_plans function."""

    def test_load_plans_from_yaml(self, tmp_path):
        """Test loading plans from YAML file."""
        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("""
plans:
  - id: 401k-monthly
    type: invest
    from: checking
    to: 401k
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
  - id: ira-paused
    type: invest
    from: checking
    to: ira
    amount: 250.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: paused
""")

        plans = load_plans(str(tmp_path), 'plans.yaml')

        assert len(plans) == 2
        assert plans[0].id == '401k-monthly'
        assert plans[0].type == PlanType.INVEST
        assert plans[0].from_account_id == 'checking'
        assert plans[0].to_account_id == '401k'
        assert plans[0].amount == 500.00
        assert plans[0].currency == 'USD'
        assert plans[0].cadence == Cadence.MONTHLY
        assert plans[0].start_date == date(2025, 1, 1)
        assert plans[0].status == PlanStatus.ACTIVE

        assert plans[1].status == PlanStatus.PAUSED

    def test_load_plans_empty_file(self, tmp_path):
        """Test loading from empty file returns empty list."""
        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("")

        plans = load_plans(str(tmp_path), 'plans.yaml')
        assert plans == []

    def test_load_plans_missing_file(self, tmp_path):
        """Test loading from missing file returns empty list."""
        plans = load_plans(str(tmp_path), 'plans.yaml')
        assert plans == []

    def test_load_plans_missing_required_field(self, tmp_path):
        """Test that missing required field raises ValueError."""
        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("""
plans:
  - id: 401k
    type: invest
    from: checking
    # Missing: to
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

        with pytest.raises(ValueError, match="'to' is required"):
            load_plans(str(tmp_path), 'plans.yaml')

    def test_load_plans_invalid_type(self, tmp_path):
        """Test that invalid plan type raises ValueError."""
        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("""
plans:
  - id: bad-plan
    type: invalid_type
    from: checking
    to: 401k
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

        with pytest.raises(ValueError):
            load_plans(str(tmp_path), 'plans.yaml')


class TestLoadPersonalFinanceConfig:
    """Tests for load_personal_finance_config function."""

    def test_load_complete_config(self, tmp_path):
        """Test loading complete personal finance configuration."""
        # Create accounts file
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Checking
    kind: cash
    currency: USD
  - id: 401k
    name: 401(k)
    kind: investment
    currency: USD
""")

        # Create snapshots file
        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("""
snapshots:
  - account: checking
    date: 2025-01-01
    value: 1000.00
  - account: 401k
    date: 2025-01-01
    value: 50000.00
""")

        # Create plans file
        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("""
plans:
  - id: 401k-monthly
    type: invest
    from: checking
    to: 401k
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

        settings = {
            'accounts_file': 'accounts.yaml',
            'snapshots_file': 'snapshots.yaml',
            'plans_file': 'plans.yaml'
        }

        result = load_personal_finance_config(str(tmp_path), settings)

        assert len(result['accounts']) == 2
        assert len(result['snapshots']) == 2
        assert len(result['plans']) == 1
        assert len(result['errors']) == 0
        assert len(result['warnings']) == 0

    def test_load_config_validates_plan_accounts(self, tmp_path):
        """Test that plan validation is performed."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Checking
    kind: cash
    currency: USD
""")

        plans_file = tmp_path / "plans.yaml"
        plans_file.write_text("""
plans:
  - id: bad-plan
    type: invest
    from: checking
    to: nonexistent-account
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

        settings = {
            'accounts_file': 'accounts.yaml',
            'plans_file': 'plans.yaml'
        }

        result = load_personal_finance_config(str(tmp_path), settings)

        assert len(result['errors']) > 0
        assert any("nonexistent-account" in err for err in result['errors'])

    def test_load_config_validates_snapshot_accounts(self, tmp_path):
        """Test that snapshot account validation is performed."""
        accounts_file = tmp_path / "accounts.yaml"
        accounts_file.write_text("""
accounts:
  - id: checking
    name: Checking
    kind: cash
    currency: USD
""")

        snapshots_file = tmp_path / "snapshots.yaml"
        snapshots_file.write_text("""
snapshots:
  - account: nonexistent-account
    date: 2025-01-01
    value: 1000.00
""")

        settings = {
            'accounts_file': 'accounts.yaml',
            'snapshots_file': 'snapshots.yaml'
        }

        result = load_personal_finance_config(str(tmp_path), settings)

        assert len(result['warnings']) > 0
        assert any("nonexistent-account" in warn for warn in result['warnings'])

    def test_load_config_all_files_missing(self, tmp_path):
        """Test loading when all files are missing returns empty results."""
        settings = {}
        result = load_personal_finance_config(str(tmp_path), settings)

        assert result['accounts'] == []
        assert result['snapshots'] == []
        assert result['plans'] == []
        # Should not have errors for missing files
        assert len(result['errors']) == 0
