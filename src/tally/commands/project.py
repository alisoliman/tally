"""
Tally 'project' command - Project future cash flow based on plans.
"""

import os
import sys
from datetime import date

from ..colors import C
from ..cli_utils import resolve_config_dir
from ..config_loader import load_config
from ..projections import project_cash_flow, format_projection_summary


def cmd_project(args):
    """Handle the 'project' subcommand - project future cash flow."""
    # Determine config directory
    config_dir = resolve_config_dir(args, required=True)

    # Load configuration
    try:
        config = load_config(config_dir, args.settings)
    except Exception as e:
        print(f"{C.RED}Error loading configuration:{C.RESET} {e}", file=sys.stderr)
        sys.exit(1)

    # Check for errors
    if config.get('_warnings'):
        errors = [w for w in config['_warnings'] if w['type'] == 'error']
        if errors:
            print(f"{C.RED}Configuration errors:{C.RESET}", file=sys.stderr)
            for error in errors:
                print(f"  • {error['message']}", file=sys.stderr)
            sys.exit(1)

    # Get accounts, snapshots, and plans
    accounts = config.get('accounts', [])
    snapshots = config.get('snapshots', [])
    plans = config.get('plans', [])

    # Check if we have data
    if not accounts:
        print(f"{C.YELLOW}No accounts configured.{C.RESET}", file=sys.stderr)
        print(f"\nTo get started:", file=sys.stderr)
        print(f"  1. Create config/accounts.yaml with your account definitions", file=sys.stderr)
        print(f"  2. Create config/snapshots.yaml with balance snapshots", file=sys.stderr)
        print(f"  3. Create config/plans.yaml with recurring plans", file=sys.stderr)
        sys.exit(1)

    if not snapshots:
        print(f"{C.YELLOW}No snapshots found.{C.RESET}", file=sys.stderr)
        print(f"\nCreate config/snapshots.yaml with balance snapshots.", file=sys.stderr)
        sys.exit(1)

    if not plans:
        print(f"{C.YELLOW}No plans configured.{C.RESET}", file=sys.stderr)
        print(f"\nCreate config/plans.yaml with recurring investment/savings plans.", file=sys.stderr)
        print(f"\nProjections require active plans to forecast cash flow.", file=sys.stderr)
        sys.exit(1)

    # Determine start date
    start_date = date.today()
    if args.start_date:
        try:
            start_date = date.fromisoformat(args.start_date)
        except ValueError:
            print(f"{C.RED}Invalid start date:{C.RESET} {args.start_date}", file=sys.stderr)
            print(f"Use YYYY-MM-DD format (e.g., 2025-01-01)", file=sys.stderr)
            sys.exit(1)

    # Project cash flow
    try:
        projection_data = project_cash_flow(
            accounts,
            snapshots,
            plans,
            start_date,
            months=args.months
        )
    except Exception as e:
        print(f"{C.RED}Error projecting cash flow:{C.RESET} {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Get currency format from config
    currency_format = config.get('currency_format', '${amount}')

    # Format and print
    if args.format == 'json':
        import json
        # Convert date objects to strings for JSON serialization
        output = {
            'start_date': start_date.isoformat(),
            'months': args.months,
            'starting_balances': projection_data['starting_balances'],
            'warnings': projection_data['warnings'],
            'projections': [
                {
                    'month': p['month'],
                    'date': p['date'].isoformat(),
                    'balances': p['balances'],
                    'transactions': [
                        {
                            **txn,
                            'date': txn['date'].isoformat()
                        }
                        for txn in p['transactions']
                    ],
                    'net_worth_by_currency': p['net_worth_by_currency'],
                }
                for p in projection_data['projections']
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable format
        summary = format_projection_summary(projection_data, accounts, currency_format)
        print(summary)

        # Show config warnings
        warnings = [w for w in config.get('_warnings', []) if w['type'] == 'warning']
        if warnings:
            print()
            print(f"{C.YELLOW}Configuration Warnings:{C.RESET}")
            for warning in warnings:
                print(f"  • {warning['message']}")
