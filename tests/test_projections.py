"""
Tests for budget projections and cash flow forecasting.
"""

import pytest
from datetime import date
from dateutil.relativedelta import relativedelta

from src.tally.domain import Account, Snapshot, Plan, AccountKind, PlanType, PlanStatus, Cadence
from src.tally.projections import get_next_plan_date, project_cash_flow, format_projection_summary


class TestGetNextPlanDate:
    """Test plan date calculation for different cadences."""

    def test_monthly_plan_basic(self):
        """Test monthly plan date calculation."""
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

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2025, 2, 1)

        next_date = get_next_plan_date(plan, date(2025, 2, 15))
        assert next_date == date(2025, 3, 15)

    def test_quarterly_plan(self):
        """Test quarterly plan date calculation."""
        plan = Plan(
            id='bonus',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=1000.00,
            currency='USD',
            cadence=Cadence.QUARTERLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2025, 4, 1)

        next_date = get_next_plan_date(plan, date(2025, 4, 1))
        assert next_date == date(2025, 7, 1)

    def test_annual_plan(self):
        """Test annual plan date calculation."""
        plan = Plan(
            id='ira',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='ira',
            amount=6500.00,
            currency='USD',
            cadence=Cadence.ANNUAL,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2026, 1, 1)

    def test_weekly_plan(self):
        """Test weekly plan date calculation."""
        plan = Plan(
            id='weekly-save',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=50.00,
            currency='USD',
            cadence=Cadence.WEEKLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2025, 1, 8)

        next_date = get_next_plan_date(plan, date(2025, 1, 8))
        assert next_date == date(2025, 1, 15)

    def test_biweekly_plan(self):
        """Test biweekly plan date calculation."""
        plan = Plan(
            id='biweekly',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=100.00,
            currency='USD',
            cadence=Cadence.BIWEEKLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.ACTIVE
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2025, 1, 15)

        next_date = get_next_plan_date(plan, date(2025, 1, 15))
        assert next_date == date(2025, 1, 29)

    def test_plan_before_start_date(self):
        """Test plan that hasn't started yet."""
        plan = Plan(
            id='future',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=100.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 6, 1),
            status=PlanStatus.ACTIVE
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date == date(2025, 6, 1)

    def test_plan_with_end_date(self):
        """Test plan that ends after certain date."""
        plan = Plan(
            id='limited',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=100.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            status=PlanStatus.ACTIVE
        )

        # Before end date
        next_date = get_next_plan_date(plan, date(2025, 5, 1))
        assert next_date == date(2025, 6, 1)

        # Would be past end date
        next_date = get_next_plan_date(plan, date(2025, 6, 15))
        assert next_date is None

    def test_paused_plan(self):
        """Test paused plan returns no next date."""
        plan = Plan(
            id='paused',
            type=PlanType.INVEST,
            from_account_id='checking',
            to_account_id='savings',
            amount=100.00,
            currency='USD',
            cadence=Cadence.MONTHLY,
            start_date=date(2025, 1, 1),
            status=PlanStatus.PAUSED
        )

        next_date = get_next_plan_date(plan, date(2025, 1, 1))
        assert next_date is None


class TestProjectCashFlow:
    """Test cash flow projection."""

    def test_simple_monthly_projection(self):
        """Test basic monthly projection with one account and one plan."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='401k', name='401k', kind=AccountKind.INVESTMENT, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='401k', date=date(2025, 1, 1), value=100000.00),
        ]

        plans = [
            Plan(
                id='401k-monthly',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='401k',
                amount=500.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 15),
                status=PlanStatus.ACTIVE
            )
        ]

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=3)

        assert len(result['projections']) == 3
        assert result['starting_balances']['checking'] == 5000.00
        assert result['starting_balances']['401k'] == 100000.00

        # Month 1: One transaction on Jan 15
        month1 = result['projections'][0]
        assert month1['month'] == '2025-01'
        assert len(month1['transactions']) == 1
        assert month1['balances']['checking'] == 4500.00
        assert month1['balances']['401k'] == 100500.00

        # Month 2: One transaction on Feb 15
        month2 = result['projections'][1]
        assert month2['month'] == '2025-02'
        assert len(month2['transactions']) == 1
        assert month2['balances']['checking'] == 4000.00
        assert month2['balances']['401k'] == 101000.00

        # Month 3: One transaction on Mar 15
        month3 = result['projections'][2]
        assert month3['month'] == '2025-03'
        assert len(month3['transactions']) == 1
        assert month3['balances']['checking'] == 3500.00
        assert month3['balances']['401k'] == 101500.00

    def test_multiple_plans_same_month(self):
        """Test multiple plans executing in same month."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
            Account(id='401k', name='401k', kind=AccountKind.INVESTMENT, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=10000.00),
            Snapshot(account_id='savings', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='401k', date=date(2025, 1, 1), value=50000.00),
        ]

        plans = [
            Plan(
                id='401k',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='401k',
                amount=500.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 1),
                status=PlanStatus.ACTIVE
            ),
            Plan(
                id='savings',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='savings',
                amount=1000.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 15),
                status=PlanStatus.ACTIVE
            ),
        ]

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=1)

        month1 = result['projections'][0]
        assert len(month1['transactions']) == 2

        # Total deductions: 500 + 1000 = 1500
        assert month1['balances']['checking'] == 8500.00
        assert month1['balances']['savings'] == 6000.00
        assert month1['balances']['401k'] == 50500.00

    def test_negative_balance_warning(self):
        """Test warning for negative balance."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='401k', name='401k', kind=AccountKind.INVESTMENT, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=1000.00),
            Snapshot(account_id='401k', date=date(2025, 1, 1), value=50000.00),
        ]

        plans = [
            Plan(
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
        ]

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=3)

        # Should have warning about negative balance
        assert len(result['warnings']) > 0
        assert any('Negative balance' in w for w in result['warnings'])

        # Month 3 should show negative balance
        month3 = result['projections'][2]
        assert month3['balances']['checking'] < 0

    def test_multi_currency_projection(self):
        """Test projection with multiple currencies."""
        accounts = [
            Account(id='us-checking', name='US Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='eu-savings', name='EU Savings', kind=AccountKind.CASH, currency='EUR'),
        ]

        snapshots = [
            Snapshot(account_id='us-checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='eu-savings', date=date(2025, 1, 1), value=3000.00),
        ]

        plans = []  # No plans

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=1)

        month1 = result['projections'][0]
        assert month1['net_worth_by_currency']['USD'] == 5000.00
        assert month1['net_worth_by_currency']['EUR'] == 3000.00

    def test_plan_with_end_date_stops(self):
        """Test plan stops executing after end date."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=10000.00),
            Snapshot(account_id='savings', date=date(2025, 1, 1), value=0.00),
        ]

        plans = [
            Plan(
                id='short-save',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='savings',
                amount=100.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),  # Ends after 3 months
                status=PlanStatus.ACTIVE
            )
        ]

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=6)

        # First 3 months should have transactions
        assert len(result['projections'][0]['transactions']) == 1
        assert len(result['projections'][1]['transactions']) == 1
        assert len(result['projections'][2]['transactions']) == 1

        # Last 3 months should have no transactions
        assert len(result['projections'][3]['transactions']) == 0
        assert len(result['projections'][4]['transactions']) == 0
        assert len(result['projections'][5]['transactions']) == 0

        # Final balance should be 3 * 100 = 300
        assert result['projections'][5]['balances']['savings'] == 300.00

    def test_missing_snapshot_warning(self):
        """Test warning when account has no snapshot."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='401k', name='401k', kind=AccountKind.INVESTMENT, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            # No snapshot for 401k
        ]

        plans = []

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=1)

        # Should have warning about missing snapshot
        assert len(result['warnings']) > 0
        assert any('No snapshot' in w and '401k' in w for w in result['warnings'])

        # Should start with 0 balance
        assert result['starting_balances']['401k'] == 0.0

    def test_paused_plan_not_executed(self):
        """Test paused plans are not executed."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
        ]

        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='savings', date=date(2025, 1, 1), value=0.00),
        ]

        plans = [
            Plan(
                id='paused-save',
                type=PlanType.INVEST,
                from_account_id='checking',
                to_account_id='savings',
                amount=100.00,
                currency='USD',
                cadence=Cadence.MONTHLY,
                start_date=date(2025, 1, 1),
                status=PlanStatus.PAUSED
            )
        ]

        result = project_cash_flow(accounts, snapshots, plans, date(2025, 1, 1), months=3)

        # No transactions should occur
        for projection in result['projections']:
            assert len(projection['transactions']) == 0

        # Balances should remain unchanged
        assert result['projections'][2]['balances']['checking'] == 5000.00
        assert result['projections'][2]['balances']['savings'] == 0.00


class TestFormatProjectionSummary:
    """Test projection summary formatting."""

    def test_basic_formatting(self):
        """Test basic summary formatting."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD')
        ]

        projection_data = {
            'starting_balances': {'checking': 5000.00},
            'warnings': [],
            'projections': [
                {
                    'month': '2025-01',
                    'date': date(2025, 1, 31),
                    'balances': {'checking': 5000.00},
                    'transactions': [],
                    'net_worth_by_currency': {'USD': 5000.00},
                }
            ],
        }

        summary = format_projection_summary(projection_data, accounts)

        assert 'Cash Flow Projection' in summary
        assert 'Starting Balances:' in summary
        assert 'Checking' in summary
        assert '2025-01' in summary

    def test_with_warnings(self):
        """Test summary includes warnings."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD')
        ]

        projection_data = {
            'starting_balances': {'checking': 1000.00},
            'warnings': ['Negative balance: Checking will have -500.00 after plan'],
            'projections': [],
        }

        summary = format_projection_summary(projection_data, accounts)

        assert 'Warnings:' in summary
        assert 'Negative balance' in summary

    def test_with_transactions(self):
        """Test summary shows transactions."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
        ]

        projection_data = {
            'starting_balances': {'checking': 5000.00, 'savings': 0.00},
            'warnings': [],
            'projections': [
                {
                    'month': '2025-01',
                    'date': date(2025, 1, 31),
                    'balances': {'checking': 4500.00, 'savings': 500.00},
                    'transactions': [
                        {
                            'date': date(2025, 1, 15),
                            'plan_id': 'save',
                            'from_account': 'checking',
                            'to_account': 'savings',
                            'amount': 500.00,
                            'description': 'Monthly savings',
                        }
                    ],
                    'net_worth_by_currency': {'USD': 5000.00},
                }
            ],
        }

        summary = format_projection_summary(projection_data, accounts)

        assert 'Transactions:' in summary
        assert 'Checking → Savings' in summary
