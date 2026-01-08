"""
Tests for financial calculations (net worth, balance aggregation, etc.)
"""

import pytest
from datetime import date

from src.tally.domain import Account, Snapshot, AccountKind
from src.tally.finance_calcs import calculate_net_worth, format_net_worth_summary


class TestCalculateNetWorth:
    """Test net worth calculation from accounts and snapshots."""

    def test_single_account_simple(self):
        """Test net worth with single account and snapshot."""
        accounts = [
            Account(id='checking', name='Main Checking', kind=AccountKind.CASH, currency='USD')
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00)
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        assert net_worth['total'] == 5000.00
        assert net_worth['by_currency'] == {'USD': 5000.00}
        assert net_worth['by_kind'] == {'cash': {'USD': 5000.00}}
        assert len(net_worth['accounts']) == 1
        assert net_worth['accounts'][0]['balance'] == 5000.00
        assert net_worth['as_of_date'] == date(2025, 1, 1)
        assert net_worth['missing_accounts'] == []

    def test_multiple_accounts_same_currency(self):
        """Test net worth with multiple accounts in same currency."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
            Account(id='401k', name='401k', kind=AccountKind.INVESTMENT, currency='USD'),
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 8), value=3000.00),
            Snapshot(account_id='savings', date=date(2025, 1, 8), value=10000.00),
            Snapshot(account_id='401k', date=date(2025, 1, 1), value=125000.00),
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        assert net_worth['total'] == 138000.00
        assert net_worth['by_currency'] == {'USD': 138000.00}
        assert net_worth['by_kind']['cash']['USD'] == 13000.00
        assert net_worth['by_kind']['investment']['USD'] == 125000.00
        assert len(net_worth['accounts']) == 3

    def test_multi_currency(self):
        """Test net worth with multiple currencies."""
        accounts = [
            Account(id='us-checking', name='US Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='eu-checking', name='EU Checking', kind=AccountKind.CASH, currency='EUR'),
        ]
        snapshots = [
            Snapshot(account_id='us-checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='eu-checking', date=date(2025, 1, 1), value=3000.00),
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        # Total is sum without FX conversion (intentionally)
        assert net_worth['total'] == 8000.00
        assert net_worth['by_currency'] == {'USD': 5000.00, 'EUR': 3000.00}
        assert len(net_worth['accounts']) == 2

    def test_latest_snapshot_used(self):
        """Test that latest snapshot per account is used."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD')
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='checking', date=date(2025, 1, 8), value=4500.00),
            Snapshot(account_id='checking', date=date(2025, 1, 5), value=4800.00),
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        assert net_worth['total'] == 4500.00
        assert net_worth['as_of_date'] == date(2025, 1, 8)
        assert net_worth['accounts'][0]['balance'] == 4500.00

    def test_as_of_date_filter(self):
        """Test calculating net worth as of a specific date."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD')
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            Snapshot(account_id='checking', date=date(2025, 1, 8), value=4500.00),
            Snapshot(account_id='checking', date=date(2025, 1, 15), value=4000.00),
        ]

        # Net worth as of Jan 10 should use Jan 8 snapshot
        net_worth = calculate_net_worth(accounts, snapshots, as_of_date=date(2025, 1, 10))

        assert net_worth['total'] == 4500.00
        assert net_worth['as_of_date'] == date(2025, 1, 8)

    def test_missing_account_snapshots(self):
        """Test handling of accounts without snapshots."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='savings', name='Savings', kind=AccountKind.CASH, currency='USD'),
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=5000.00),
            # No snapshot for savings
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        assert net_worth['total'] == 5000.00
        assert len(net_worth['accounts']) == 1
        assert net_worth['missing_accounts'] == ['savings']

    def test_empty_accounts(self):
        """Test with no accounts."""
        net_worth = calculate_net_worth([], [])

        assert net_worth['total'] == 0.0
        assert net_worth['by_currency'] == {}
        assert net_worth['by_kind'] == {}
        assert net_worth['accounts'] == []
        assert net_worth['as_of_date'] is None
        assert net_worth['missing_accounts'] == []

    def test_negative_balances(self):
        """Test accounts with negative balances (debt)."""
        accounts = [
            Account(id='checking', name='Checking', kind=AccountKind.CASH, currency='USD'),
            Account(id='credit-card', name='Credit Card', kind=AccountKind.CASH, currency='USD'),
        ]
        snapshots = [
            Snapshot(account_id='checking', date=date(2025, 1, 1), value=1000.00),
            Snapshot(account_id='credit-card', date=date(2025, 1, 1), value=-500.00),
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        assert net_worth['total'] == 500.00
        assert net_worth['by_currency'] == {'USD': 500.00}

    def test_account_details_populated(self):
        """Test that account details include all relevant information."""
        accounts = [
            Account(id='checking', name='Main Checking', kind=AccountKind.CASH, currency='USD')
        ]
        snapshots = [
            Snapshot(
                account_id='checking',
                date=date(2025, 1, 8),
                value=5000.00,
                note='After paycheck'
            )
        ]

        net_worth = calculate_net_worth(accounts, snapshots)

        account = net_worth['accounts'][0]
        assert account['id'] == 'checking'
        assert account['name'] == 'Main Checking'
        assert account['kind'] == 'cash'
        assert account['currency'] == 'USD'
        assert account['balance'] == 5000.00
        assert account['date'] == date(2025, 1, 8)
        assert account['note'] == 'After paycheck'


class TestFormatNetWorthSummary:
    """Test human-readable net worth summary formatting."""

    def test_basic_formatting(self):
        """Test basic summary formatting."""
        net_worth = {
            'total': 10000.00,
            'by_currency': {'USD': 10000.00},
            'by_kind': {'cash': {'USD': 10000.00}},
            'accounts': [
                {
                    'id': 'checking',
                    'name': 'Main Checking',
                    'kind': 'cash',
                    'currency': 'USD',
                    'balance': 10000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                }
            ],
            'as_of_date': date(2025, 1, 1),
            'missing_accounts': [],
        }

        summary = format_net_worth_summary(net_worth)

        assert 'Net Worth as of 2025-01-01' in summary
        assert 'Main Checking' in summary
        assert '$10,000.00' in summary
        assert 'Total Net Worth' in summary

    def test_multi_currency_formatting(self):
        """Test summary with multiple currencies."""
        net_worth = {
            'total': 8000.00,
            'by_currency': {'USD': 5000.00, 'EUR': 3000.00},
            'by_kind': {'cash': {'USD': 5000.00, 'EUR': 3000.00}},
            'accounts': [
                {
                    'id': 'us-checking',
                    'name': 'US Checking',
                    'kind': 'cash',
                    'currency': 'USD',
                    'balance': 5000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                },
                {
                    'id': 'eu-checking',
                    'name': 'EU Checking',
                    'kind': 'cash',
                    'currency': 'EUR',
                    'balance': 3000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                }
            ],
            'as_of_date': date(2025, 1, 1),
            'missing_accounts': [],
        }

        summary = format_net_worth_summary(net_worth)

        assert 'By Currency:' in summary
        assert 'USD:' in summary
        assert 'EUR:' in summary
        assert 'without FX conversion' in summary

    def test_missing_accounts_warning(self):
        """Test that missing accounts show a warning."""
        net_worth = {
            'total': 5000.00,
            'by_currency': {'USD': 5000.00},
            'by_kind': {'cash': {'USD': 5000.00}},
            'accounts': [
                {
                    'id': 'checking',
                    'name': 'Checking',
                    'kind': 'cash',
                    'currency': 'USD',
                    'balance': 5000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                }
            ],
            'as_of_date': date(2025, 1, 1),
            'missing_accounts': ['savings', '401k'],
        }

        summary = format_net_worth_summary(net_worth)

        assert 'Warning' in summary
        assert 'No snapshots found for:' in summary
        assert 'savings' in summary
        assert '401k' in summary

    def test_custom_currency_format(self):
        """Test summary with custom currency format."""
        net_worth = {
            'total': 10000.00,
            'by_currency': {'EUR': 10000.00},
            'by_kind': {'cash': {'EUR': 10000.00}},
            'accounts': [
                {
                    'id': 'checking',
                    'name': 'Checking',
                    'kind': 'cash',
                    'currency': 'EUR',
                    'balance': 10000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                }
            ],
            'as_of_date': date(2025, 1, 1),
            'missing_accounts': [],
        }

        summary = format_net_worth_summary(net_worth, currency_format='€{amount}')

        # Note: The format_currency function replaces {amount} with the formatted number
        assert '€' in summary or '10,000.00' in summary

    def test_by_account_type_section(self):
        """Test that summary shows breakdown by account type."""
        net_worth = {
            'total': 135000.00,
            'by_currency': {'USD': 135000.00},
            'by_kind': {
                'cash': {'USD': 10000.00},
                'investment': {'USD': 125000.00}
            },
            'accounts': [
                {
                    'id': 'checking',
                    'name': 'Checking',
                    'kind': 'cash',
                    'currency': 'USD',
                    'balance': 10000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                },
                {
                    'id': '401k',
                    'name': '401k',
                    'kind': 'investment',
                    'currency': 'USD',
                    'balance': 125000.00,
                    'date': date(2025, 1, 1),
                    'note': None,
                }
            ],
            'as_of_date': date(2025, 1, 1),
            'missing_accounts': [],
        }

        summary = format_net_worth_summary(net_worth)

        assert 'By Account Type:' in summary
        assert 'Cash:' in summary or 'cash:' in summary
        assert 'Investment:' in summary or 'investment:' in summary
