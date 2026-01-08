"""
Configuration loader for Tally accounts, snapshots, and plans.

Loads personal finance data from YAML files.
"""

import os
from datetime import date
from typing import Optional

from .domain import (
    Account, Snapshot, Plan,
    AccountKind, PlanType, PlanStatus, Cadence,
    validate_plan_accounts
)

# Try to import yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_accounts(config_dir: str, accounts_file: Optional[str] = None) -> list[Account]:
    """
    Load accounts from accounts.yaml.

    Args:
        config_dir: Path to config directory
        accounts_file: Optional override path (relative to config_dir or absolute)

    Returns:
        List of Account objects (empty if file doesn't exist)

    Raises:
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for account tracking. Install with: pip install pyyaml")

    # Resolve path
    if accounts_file:
        if os.path.isabs(accounts_file):
            path = accounts_file
        else:
            path = os.path.join(config_dir, accounts_file)
    else:
        path = os.path.join(config_dir, 'accounts.yaml')

    if not os.path.exists(path):
        return []

    # Load YAML
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    accounts = []
    for i, acc_data in enumerate(data.get('accounts', [])):
        try:
            # Validate required fields
            if 'id' not in acc_data:
                raise ValueError(f"Account #{i+1}: 'id' is required")
            if 'name' not in acc_data:
                raise ValueError(f"Account #{i+1}: 'name' is required")
            if 'kind' not in acc_data:
                raise ValueError(f"Account #{i+1}: 'kind' is required")
            if 'currency' not in acc_data:
                raise ValueError(f"Account #{i+1}: 'currency' is required")

            account = Account(
                id=acc_data['id'],
                name=acc_data['name'],
                kind=AccountKind(acc_data['kind'].lower()),
                currency=acc_data['currency']
            )
            accounts.append(account)

        except (ValueError, KeyError) as e:
            raise ValueError(f"Error loading account #{i+1} from {path}: {e}")

    return accounts


def load_snapshots(config_dir: str, snapshots_file: Optional[str] = None) -> list[Snapshot]:
    """
    Load snapshots from snapshots.yaml.

    Args:
        config_dir: Path to config directory
        snapshots_file: Optional override path (relative to config_dir or absolute)

    Returns:
        List of Snapshot objects (empty if file doesn't exist)

    Raises:
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for snapshot tracking. Install with: pip install pyyaml")

    # Resolve path
    if snapshots_file:
        if os.path.isabs(snapshots_file):
            path = snapshots_file
        else:
            path = os.path.join(config_dir, snapshots_file)
    else:
        path = os.path.join(config_dir, 'snapshots.yaml')

    if not os.path.exists(path):
        return []

    # Load YAML
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    snapshots = []
    for i, snap_data in enumerate(data.get('snapshots', [])):
        try:
            # Validate required fields
            if 'account' not in snap_data:
                raise ValueError(f"Snapshot #{i+1}: 'account' is required")
            if 'date' not in snap_data:
                raise ValueError(f"Snapshot #{i+1}: 'date' is required")
            if 'value' not in snap_data:
                raise ValueError(f"Snapshot #{i+1}: 'value' is required")

            # Parse date
            snap_date = snap_data['date']
            if isinstance(snap_date, str):
                from datetime import datetime
                try:
                    snap_date = datetime.strptime(snap_date, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError(f"Invalid date format: {snap_date}. Use YYYY-MM-DD")
            elif not isinstance(snap_date, date):
                # YAML parser might return datetime.date directly
                snap_date = snap_date

            snapshot = Snapshot(
                account_id=snap_data['account'],
                date=snap_date,
                value=float(snap_data['value']),
                note=snap_data.get('note'),
                attachment=snap_data.get('attachment')
            )
            snapshots.append(snapshot)

        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"Error loading snapshot #{i+1} from {path}: {e}")

    return snapshots


def load_plans(config_dir: str, plans_file: Optional[str] = None) -> list[Plan]:
    """
    Load plans from plans.yaml.

    Args:
        config_dir: Path to config directory
        plans_file: Optional override path (relative to config_dir or absolute)

    Returns:
        List of Plan objects (empty if file doesn't exist)

    Raises:
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for plan tracking. Install with: pip install pyyaml")

    # Resolve path
    if plans_file:
        if os.path.isabs(plans_file):
            path = plans_file
        else:
            path = os.path.join(config_dir, plans_file)
    else:
        path = os.path.join(config_dir, 'plans.yaml')

    if not os.path.exists(path):
        return []

    # Load YAML
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    plans = []
    for i, plan_data in enumerate(data.get('plans', [])):
        try:
            # Validate required fields
            required_fields = ['id', 'type', 'from', 'to', 'amount', 'currency', 'cadence', 'start_date', 'status']
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"Plan #{i+1}: '{field}' is required")

            # Parse start_date
            start = plan_data['start_date']
            if isinstance(start, str):
                from datetime import datetime
                try:
                    start = datetime.strptime(start, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError(f"Invalid date format: {start}. Use YYYY-MM-DD")

            plan = Plan(
                id=plan_data['id'],
                type=PlanType(plan_data['type'].lower()),
                from_account_id=plan_data['from'],
                to_account_id=plan_data['to'],
                amount=float(plan_data['amount']),
                currency=plan_data['currency'],
                cadence=Cadence(plan_data['cadence'].lower()),
                start_date=start,
                status=PlanStatus(plan_data['status'].lower())
            )
            plans.append(plan)

        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"Error loading plan #{i+1} from {path}: {e}")

    return plans


def load_personal_finance_config(config_dir: str, settings: dict) -> dict:
    """
    Load all personal finance configuration (accounts, snapshots, plans).

    Args:
        config_dir: Path to config directory
        settings: Loaded settings dict from settings.yaml

    Returns:
        Dict with 'accounts', 'snapshots', 'plans', and validation errors/warnings
    """
    result = {
        'accounts': [],
        'snapshots': [],
        'plans': [],
        'errors': [],
        'warnings': [],
    }

    try:
        # Load accounts
        accounts_file = settings.get('accounts_file', 'config/accounts.yaml')
        result['accounts'] = load_accounts(config_dir, accounts_file)

        # Load snapshots
        snapshots_file = settings.get('snapshots_file', 'config/snapshots.yaml')
        result['snapshots'] = load_snapshots(config_dir, snapshots_file)

        # Load plans
        plans_file = settings.get('plans_file', 'config/plans.yaml')
        result['plans'] = load_plans(config_dir, plans_file)

        # Validate plans against accounts
        for plan in result['plans']:
            errors = validate_plan_accounts(plan, result['accounts'])
            result['errors'].extend(errors)

        # Validate snapshots reference existing accounts
        account_ids = {a.id for a in result['accounts']}
        for snapshot in result['snapshots']:
            if snapshot.account_id not in account_ids:
                result['warnings'].append(
                    f"Snapshot for account '{snapshot.account_id}' on {snapshot.date}: "
                    f"account does not exist in accounts.yaml"
                )

    except ImportError as e:
        # PyYAML not available
        result['errors'].append(str(e))
    except Exception as e:
        # Unexpected error loading configuration
        result['errors'].append(f"Error loading personal finance configuration: {e}")

    return result
