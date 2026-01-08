"""
Configuration loader for Tally v1 features.

Loads accounts, snapshots, and plans from YAML files.
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
        List of Account objects

    Raises:
        FileNotFoundError: If accounts file doesn't exist
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for v1 features. Install with: pip install pyyaml")

    # Resolve path
    if accounts_file:
        if os.path.isabs(accounts_file):
            path = accounts_file
        else:
            path = os.path.join(config_dir, accounts_file)
    else:
        path = os.path.join(config_dir, 'accounts.yaml')

    if not os.path.exists(path):
        # Return empty list if file doesn't exist (v1 features disabled)
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
        List of Snapshot objects

    Raises:
        FileNotFoundError: If snapshots file doesn't exist
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for v1 features. Install with: pip install pyyaml")

    # Resolve path
    if snapshots_file:
        if os.path.isabs(snapshots_file):
            path = snapshots_file
        else:
            path = os.path.join(config_dir, snapshots_file)
    else:
        path = os.path.join(config_dir, 'snapshots.yaml')

    if not os.path.exists(path):
        # Return empty list if file doesn't exist
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
        List of Plan objects

    Raises:
        FileNotFoundError: If plans file doesn't exist
        ValueError: If YAML is malformed or validation fails
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for v1 features. Install with: pip install pyyaml")

    # Resolve path
    if plans_file:
        if os.path.isabs(plans_file):
            path = plans_file
        else:
            path = os.path.join(config_dir, plans_file)
    else:
        path = os.path.join(config_dir, 'plans.yaml')

    if not os.path.exists(path):
        # Return empty list if file doesn't exist
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


def load_v1_config(config_dir: str, settings: dict) -> dict:
    """
    Load all v1 configuration (accounts, snapshots, plans).

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
        'v1_enabled': False,
        'v1_errors': [],
        'v1_warnings': [],
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

        # v1 is enabled if we have accounts
        result['v1_enabled'] = len(result['accounts']) > 0

        # Validate plans against accounts
        for plan in result['plans']:
            errors = validate_plan_accounts(plan, result['accounts'])
            result['v1_errors'].extend(errors)

        # Validate snapshots reference existing accounts
        account_ids = {a.id for a in result['accounts']}
        for snapshot in result['snapshots']:
            if snapshot.account_id not in account_ids:
                result['v1_warnings'].append(
                    f"Snapshot for account '{snapshot.account_id}' on {snapshot.date}: "
                    f"account does not exist in accounts.yaml"
                )

    except ImportError as e:
        # PyYAML not available - v1 features unavailable
        result['v1_errors'].append(str(e))
    except Exception as e:
        # Unexpected error loading v1 config
        result['v1_errors'].append(f"Error loading v1 configuration: {e}")

    return result


def is_v1_enabled(config: dict) -> bool:
    """
    Check if v1 features are enabled.

    Args:
        config: Loaded config dict

    Returns:
        True if v1 features should be enabled
    """
    # Explicit disable flag
    if config.get('enable_v1_features') is False:
        return False

    # Auto-detect: v1 enabled if we have accounts
    return len(config.get('accounts', [])) > 0
