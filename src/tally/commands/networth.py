"""
Tally 'networth' command - Display net worth from account snapshots.
"""

import os
import sys
from datetime import datetime

from ..colors import C
from ..cli_utils import resolve_config_dir
from ..config_loader import load_config
from ..finance_calcs import calculate_net_worth, format_net_worth_summary


def cmd_networth(args):
    """Handle the 'networth' subcommand - calculate and display net worth."""
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

    # Get accounts and snapshots
    accounts = config.get('accounts', [])
    snapshots = config.get('snapshots', [])

    # Check if we have data
    if not accounts:
        print(f"{C.YELLOW}No accounts configured.{C.RESET}", file=sys.stderr)
        print(f"\nTo get started:", file=sys.stderr)
        print(f"  1. Create config/accounts.yaml with your account definitions", file=sys.stderr)
        print(f"  2. Create config/snapshots.yaml with balance snapshots", file=sys.stderr)
        print(f"\nSee example files:", file=sys.stderr)
        print(f"  {C.CYAN}config/accounts.yaml.example{C.RESET}", file=sys.stderr)
        print(f"  {C.CYAN}config/snapshots.yaml.example{C.RESET}", file=sys.stderr)
        sys.exit(1)

    if not snapshots:
        print(f"{C.YELLOW}No snapshots found.{C.RESET}", file=sys.stderr)
        print(f"\nCreate config/snapshots.yaml with balance snapshots.", file=sys.stderr)
        print(f"See: {C.CYAN}config/snapshots.yaml.example{C.RESET}", file=sys.stderr)
        sys.exit(1)

    # Parse as_of_date if provided
    as_of_date = None
    if args.as_of:
        try:
            as_of_date = datetime.strptime(args.as_of, '%Y-%m-%d').date()
        except ValueError:
            print(f"{C.RED}Invalid date format:{C.RESET} {args.as_of}", file=sys.stderr)
            print(f"Use YYYY-MM-DD format (e.g., 2025-01-08)", file=sys.stderr)
            sys.exit(1)

    # Calculate net worth
    net_worth = calculate_net_worth(accounts, snapshots, as_of_date)

    # Get currency format from config
    currency_format = config.get('currency_format', '${amount}')

    # Format and print
    if args.format == 'json':
        import json
        # Convert date objects to strings for JSON serialization
        output = {
            'total': net_worth['total'],
            'by_currency': net_worth['by_currency'],
            'by_kind': net_worth['by_kind'],
            'accounts': [
                {
                    **acc,
                    'date': acc['date'].isoformat()
                }
                for acc in net_worth['accounts']
            ],
            'as_of_date': net_worth['as_of_date'].isoformat() if net_worth['as_of_date'] else None,
            'missing_accounts': net_worth['missing_accounts'],
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable format
        summary = format_net_worth_summary(net_worth, currency_format)
        print(summary)

        # Show warnings
        warnings = [w for w in config.get('_warnings', []) if w['type'] == 'warning']
        if warnings:
            print()
            print(f"{C.YELLOW}Warnings:{C.RESET}")
            for warning in warnings:
                print(f"  • {warning['message']}")
