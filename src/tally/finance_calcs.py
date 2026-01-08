"""
Financial calculations for personal finance tracking.

Provides net worth calculation, balance aggregation, and other financial metrics.
"""

from datetime import date
from typing import Optional
from collections import defaultdict

from .domain import Account, Snapshot, get_latest_snapshot


def calculate_net_worth(accounts: list[Account], snapshots: list[Snapshot],
                       as_of_date: Optional[date] = None) -> dict:
    """
    Calculate net worth from accounts and snapshots.

    Args:
        accounts: List of Account objects
        snapshots: List of Snapshot objects
        as_of_date: Optional date to calculate net worth as of (defaults to latest)

    Returns:
        Dict with:
        - total: Total net worth across all currencies
        - by_currency: Dict mapping currency -> net worth
        - by_kind: Dict mapping AccountKind -> {currency -> value}
        - accounts: List of dicts with per-account balances
        - as_of_date: Date of the latest snapshot used
        - missing_accounts: List of account IDs without snapshots
    """
    result = {
        'total': 0.0,
        'by_currency': defaultdict(float),
        'by_kind': defaultdict(lambda: defaultdict(float)),
        'accounts': [],
        'as_of_date': None,
        'missing_accounts': [],
    }

    # Build account lookup
    account_map = {acc.id: acc for acc in accounts}

    # Get latest snapshot per account
    for account in accounts:
        latest = get_latest_snapshot(snapshots, account.id, as_of_date)

        if latest is None:
            result['missing_accounts'].append(account.id)
            continue

        # Track latest date
        if result['as_of_date'] is None or latest.date > result['as_of_date']:
            result['as_of_date'] = latest.date

        # Add to totals
        result['by_currency'][account.currency] += latest.value
        result['by_kind'][account.kind.value][account.currency] += latest.value

        # Add account detail
        result['accounts'].append({
            'id': account.id,
            'name': account.name,
            'kind': account.kind.value,
            'currency': account.currency,
            'balance': latest.value,
            'date': latest.date,
            'note': latest.note,
        })

    # Convert defaultdicts to regular dicts for cleaner output
    result['by_currency'] = dict(result['by_currency'])
    result['by_kind'] = {
        kind: dict(currencies)
        for kind, currencies in result['by_kind'].items()
    }

    # Calculate total (sum all currencies - assumes single currency or manual aggregation)
    # If multiple currencies, this is just a sum without FX conversion
    result['total'] = sum(result['by_currency'].values())

    return result


def format_net_worth_summary(net_worth: dict, currency_format: str = '${amount}') -> str:
    """
    Format net worth calculation as human-readable text.

    Args:
        net_worth: Result from calculate_net_worth()
        currency_format: Currency format string (default: '${amount}')

    Returns:
        Formatted string with net worth breakdown
    """
    from .analyzer import format_currency

    lines = []

    # Header
    if net_worth['as_of_date']:
        lines.append(f"Net Worth as of {net_worth['as_of_date']}")
    else:
        lines.append("Net Worth")
    lines.append("=" * 60)
    lines.append("")

    # Missing accounts warning
    if net_worth['missing_accounts']:
        lines.append("⚠️  Warning: No snapshots found for:")
        for acc_id in net_worth['missing_accounts']:
            lines.append(f"   - {acc_id}")
        lines.append("")

    # By currency summary
    if len(net_worth['by_currency']) > 1:
        lines.append("By Currency:")
        for currency, total in sorted(net_worth['by_currency'].items()):
            formatted = format_currency(total, currency_format.replace('{amount}', f'{total:,.2f}'))
            lines.append(f"  {currency}: {formatted}")
        lines.append("")

    # By account kind
    if net_worth['by_kind']:
        lines.append("By Account Type:")
        for kind, currencies in sorted(net_worth['by_kind'].items()):
            kind_total = sum(currencies.values())
            formatted = format_currency(kind_total, currency_format.replace('{amount}', f'{kind_total:,.2f}'))
            lines.append(f"  {kind.capitalize()}: {formatted}")
        lines.append("")

    # Account details
    if net_worth['accounts']:
        lines.append("Account Balances:")
        lines.append(f"{'Account':<30} {'Type':<12} {'Balance':>15}")
        lines.append("-" * 60)

        # Sort by kind, then by balance descending
        sorted_accounts = sorted(
            net_worth['accounts'],
            key=lambda a: (a['kind'], -a['balance'])
        )

        for acc in sorted_accounts:
            balance_str = f"{acc['balance']:,.2f} {acc['currency']}"
            lines.append(f"{acc['name']:<30} {acc['kind']:<12} {balance_str:>15}")

        lines.append("")

    # Total
    lines.append("=" * 60)
    total_formatted = format_currency(
        net_worth['total'],
        currency_format.replace('{amount}', f"{net_worth['total']:,.2f}")
    )
    lines.append(f"Total Net Worth: {total_formatted}")

    if len(net_worth['by_currency']) > 1:
        lines.append("(Note: Multi-currency totals are summed without FX conversion)")

    return '\n'.join(lines)
