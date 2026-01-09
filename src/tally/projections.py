"""
Budget projections and cash flow forecasting.

Projects future account balances based on current snapshots and active plans.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from typing import Optional

from .domain import Account, Snapshot, Plan, Cadence, PlanStatus, get_latest_snapshot


def get_next_plan_date(plan: Plan, from_date: date) -> Optional[date]:
    """
    Calculate the next date when a plan should execute AFTER from_date.

    Args:
        plan: Plan to calculate next date for
        from_date: Date to calculate from (looks for next execution after this)

    Returns:
        Next execution date, or None if plan shouldn't execute anymore
    """
    # Check if plan is active
    if plan.status != PlanStatus.ACTIVE:
        return None

    # If we're before the start date, the next execution is the start date
    if from_date < plan.start_date:
        return plan.start_date

    # Check if we're past the end date
    if plan.end_date and from_date > plan.end_date:
        return None

    # Calculate next date based on cadence
    next_date = from_date

    if plan.cadence == Cadence.MONTHLY:
        # Next month, same day
        next_date = from_date + relativedelta(months=1)
    elif plan.cadence == Cadence.QUARTERLY:
        # Next quarter (3 months)
        next_date = from_date + relativedelta(months=3)
    elif plan.cadence == Cadence.ANNUAL:
        # Next year
        next_date = from_date + relativedelta(years=1)
    elif plan.cadence == Cadence.BIWEEKLY:
        # Every 2 weeks
        next_date = from_date + timedelta(days=14)
    elif plan.cadence == Cadence.WEEKLY:
        # Every week
        next_date = from_date + timedelta(days=7)

    # Check if next date is past end date
    if plan.end_date and next_date > plan.end_date:
        return None

    return next_date


def project_cash_flow(accounts: list[Account], snapshots: list[Snapshot],
                     plans: list[Plan], start_date: date, months: int = 12) -> dict:
    """
    Project future cash flow based on current balances and active plans.

    Args:
        accounts: List of Account objects
        snapshots: List of Snapshot objects
        plans: List of Plan objects
        start_date: Date to start projection from
        months: Number of months to project (default: 12)

    Returns:
        Dict with:
        - projections: List of monthly projection dicts
        - warnings: List of warning messages (negative balances, etc.)
        - starting_balances: Dict mapping account_id -> starting balance
    """
    result = {
        'projections': [],
        'warnings': [],
        'starting_balances': {},
    }

    # Build account lookup
    account_map = {acc.id: acc for acc in accounts}

    # Get starting balances from latest snapshots
    balances = {}
    for account in accounts:
        latest = get_latest_snapshot(snapshots, account.id, start_date)
        if latest:
            balances[account.id] = latest.value
            result['starting_balances'][account.id] = latest.value
        else:
            # No snapshot available
            balances[account.id] = 0.0
            result['starting_balances'][account.id] = 0.0
            result['warnings'].append(
                f"No snapshot found for account '{account.id}' on or before {start_date}. Starting with $0."
            )

    # Filter to active plans
    active_plans = [p for p in plans if p.status == PlanStatus.ACTIVE]

    # Track plan execution dates
    plan_next_dates = {}
    for plan in active_plans:
        # If plan starts on or after our start date, first execution is the plan's start date
        if plan.start_date >= start_date:
            plan_next_dates[plan.id] = plan.start_date
        else:
            # Plan already started before our projection, find next occurrence
            # Use start_date - 1 day so we get the next occurrence on or after start_date
            next_date = get_next_plan_date(plan, start_date - timedelta(days=1))
            if next_date:
                plan_next_dates[plan.id] = next_date

    # Project month by month
    current_date = start_date
    for month_num in range(months):
        # Calculate end of current month
        month_end = current_date + relativedelta(months=1) - timedelta(days=1)

        # Track transactions for this month
        month_transactions = []

        # Execute all plans that fall within this month
        for plan in active_plans:
            if plan.id not in plan_next_dates:
                continue

            while plan_next_dates[plan.id] and plan_next_dates[plan.id] <= month_end:
                execution_date = plan_next_dates[plan.id]

                # Validate accounts exist
                if plan.from_account_id not in account_map:
                    result['warnings'].append(
                        f"Plan '{plan.id}' references unknown from_account '{plan.from_account_id}'"
                    )
                    del plan_next_dates[plan.id]
                    break

                if plan.to_account_id not in account_map:
                    result['warnings'].append(
                        f"Plan '{plan.id}' references unknown to_account '{plan.to_account_id}'"
                    )
                    del plan_next_dates[plan.id]
                    break

                # Execute the transfer
                balances[plan.from_account_id] -= plan.amount
                balances[plan.to_account_id] += plan.amount

                month_transactions.append({
                    'date': execution_date,
                    'plan_id': plan.id,
                    'from_account': plan.from_account_id,
                    'to_account': plan.to_account_id,
                    'amount': plan.amount,
                    'description': f"{plan.id}: {plan.amount} {plan.currency}",
                })

                # Check for negative balance warning
                if balances[plan.from_account_id] < 0:
                    account_name = account_map[plan.from_account_id].name
                    result['warnings'].append(
                        f"Negative balance: {account_name} will have {balances[plan.from_account_id]:.2f} "
                        f"after '{plan.id}' on {execution_date}"
                    )

                # Calculate next execution date
                next_date = get_next_plan_date(plan, execution_date)
                if next_date:
                    plan_next_dates[plan.id] = next_date
                else:
                    # Plan is complete
                    del plan_next_dates[plan.id]
                    break

        # Record month-end projection
        projection = {
            'month': current_date.strftime('%Y-%m'),
            'date': month_end,
            'balances': dict(balances),  # Copy current balances
            'transactions': month_transactions,
            'net_worth_by_currency': defaultdict(float),
        }

        # Calculate net worth by currency
        for account_id, balance in balances.items():
            account = account_map[account_id]
            projection['net_worth_by_currency'][account.currency] += balance

        projection['net_worth_by_currency'] = dict(projection['net_worth_by_currency'])

        result['projections'].append(projection)

        # Move to next month
        current_date = current_date + relativedelta(months=1)

    return result


def format_projection_summary(projection_data: dict, accounts: list[Account],
                              currency_format: str = '${amount}') -> str:
    """
    Format cash flow projection as human-readable text.

    Args:
        projection_data: Result from project_cash_flow()
        accounts: List of Account objects for names
        currency_format: Currency format string

    Returns:
        Formatted string with projection summary
    """
    from .analyzer import format_currency

    lines = []
    account_map = {acc.id: acc for acc in accounts}

    # Header
    lines.append("Cash Flow Projection")
    lines.append("=" * 80)
    lines.append("")

    # Starting balances
    if projection_data['starting_balances']:
        lines.append("Starting Balances:")
        for account_id, balance in projection_data['starting_balances'].items():
            account = account_map.get(account_id)
            if account:
                balance_str = format_currency(balance, currency_format.replace('{amount}', f'{balance:,.2f}'))
                lines.append(f"  {account.name:<30} {balance_str:>15}")
        lines.append("")

    # Warnings
    if projection_data['warnings']:
        lines.append("⚠️  Warnings:")
        for warning in projection_data['warnings']:
            lines.append(f"  • {warning}")
        lines.append("")

    # Monthly projections
    if projection_data['projections']:
        lines.append("Monthly Projections:")
        lines.append("")

        for projection in projection_data['projections']:
            lines.append(f"Month: {projection['month']}")
            lines.append("-" * 80)

            # Transactions
            if projection['transactions']:
                lines.append("  Transactions:")
                for txn in projection['transactions']:
                    from_acc = account_map.get(txn['from_account'], {'name': txn['from_account']})
                    to_acc = account_map.get(txn['to_account'], {'name': txn['to_account']})
                    from_name = from_acc.name if hasattr(from_acc, 'name') else txn['from_account']
                    to_name = to_acc.name if hasattr(to_acc, 'name') else txn['to_account']

                    amount_str = format_currency(
                        txn['amount'],
                        currency_format.replace('{amount}', f"{txn['amount']:,.2f}")
                    )
                    lines.append(f"    {txn['date']}: {from_name} → {to_name}: {amount_str}")

            # End of month balances
            lines.append("  End of Month Balances:")
            for account_id, balance in projection['balances'].items():
                account = account_map.get(account_id)
                if account:
                    balance_str = format_currency(
                        balance,
                        currency_format.replace('{amount}', f'{balance:,.2f}')
                    )
                    lines.append(f"    {account.name:<28} {balance_str:>15}")

            # Net worth
            if len(projection['net_worth_by_currency']) > 0:
                lines.append("  Net Worth:")
                for currency, total in projection['net_worth_by_currency'].items():
                    total_str = format_currency(
                        total,
                        currency_format.replace('{amount}', f'{total:,.2f}')
                    )
                    lines.append(f"    {currency}: {total_str}")

            lines.append("")

    return '\n'.join(lines)
