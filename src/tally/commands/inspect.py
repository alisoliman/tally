"""
Tally 'inspect' command - Show CSV structure and sample rows.
"""

import os
import sys
import csv

from ..cli import C
from ..analyzer import auto_detect_csv_format


def cmd_inspect(args):
    """Handle the 'inspect' subcommand - show CSV structure and sample rows."""

    if not args.file:
        print("Error: No file specified", file=sys.stderr)
        print("\nUsage: tally inspect <file.csv>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  tally inspect data/transactions.csv", file=sys.stderr)
        sys.exit(1)

    filepath = os.path.abspath(args.file)

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    num_rows = args.rows

    print(f"Inspecting: {filepath}")
    print("=" * 70)

    # First, detect file format
    format_info = _detect_file_format(filepath)

    print(f"\nFile Format Detection:")
    print("-" * 70)
    print(f"  Detected type: {format_info['format_type']}")

    if format_info['issues']:
        print(f"\n  Issues:")
        for issue in format_info['issues']:
            print(f"    ⚠ {issue}")

    if format_info['format_type'] == 'fixed_width':
        print(f"\n  Sample lines:")
        for i, line in enumerate(format_info['sample_lines'][:5]):
            if line.strip():
                print(f"    {i}: {line[:80]}{'...' if len(line) > 80 else ''}")

        if format_info['suggestions']:
            print(f"\n  Suggestions:")
            for suggestion in format_info['suggestions']:
                for line in suggestion.split('\n'):
                    print(f"    {line}")
        print()
        return  # Don't try to parse as CSV

    with open(filepath, 'r', encoding='utf-8') as f:
        # Detect if it's a valid CSV
        try:
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            has_header = csv.Sniffer().has_header(sample)
            f.seek(0)
        except csv.Error:
            print("Warning: Could not detect CSV dialect, using default")
            dialect = None
            has_header = True
            f.seek(0)

        reader = csv.reader(f, dialect) if dialect else csv.reader(f)

        rows = []
        for i, row in enumerate(reader):
            rows.append(row)
            if i >= num_rows:  # Get header + N data rows
                break

        if not rows:
            print("File appears to be empty.")
            return

    # Display header info
    if has_header and rows:
        print("\nDetected Headers:")
        print("-" * 70)
        for idx, col in enumerate(rows[0]):
            print(f"  Column {idx}: {col}")

    # Display sample data
    print(f"\nSample Data (first {min(num_rows, len(rows)-1)} rows):")
    print("-" * 70)

    data_rows = rows[1:] if has_header else rows
    for row_num, row in enumerate(data_rows[:num_rows], start=1):
        print(f"\nRow {row_num}:")
        for idx, val in enumerate(row):
            header = rows[0][idx] if has_header and idx < len(rows[0]) else f"Col {idx}"
            # Truncate long values
            display_val = val[:50] + "..." if len(val) > 50 else val
            print(f"  [{idx}] {header}: {display_val}")

    # Attempt auto-detection
    print("\n" + "=" * 70)
    print("Auto-Detection Results:")
    print("-" * 70)

    try:
        spec = auto_detect_csv_format(filepath)
        print("  Successfully detected format!")
        print(f"  - Date column: {spec.date_column} (format: {spec.date_format})")
        print(f"  - Description column: {spec.description_column}")
        print(f"  - Amount column: {spec.amount_column}")
        if spec.location_column is not None:
            print(f"  - Location column: {spec.location_column}")

        # Build suggested format string
        max_col = max(spec.date_column, spec.description_column, spec.amount_column)
        if spec.location_column is not None:
            max_col = max(max_col, spec.location_column)

        cols = []
        for i in range(max_col + 1):
            if i == spec.date_column:
                cols.append(f'{{date:{spec.date_format}}}')
            elif i == spec.description_column:
                cols.append('{description}')
            elif i == spec.amount_column:
                cols.append('{amount}')
            elif spec.location_column is not None and i == spec.location_column:
                cols.append('{location}')
            else:
                cols.append('{_}')

        format_str = ', '.join(cols)
        print(f"\n  Suggested format string:")
        print(f'    format: "{format_str}"')

        # Analyze amount patterns
        analysis = _analyze_amount_patterns(filepath, spec.amount_column, has_header=True)
        if analysis:
            print("\n" + "=" * 70)
            print("Amount Sign Analysis:")
            print("-" * 70)
            print(f"  Positive amounts: {analysis['positive_count']} (${analysis['positive_total']:,.2f})")
            print(f"  Negative amounts: {analysis['negative_count']} (${analysis['negative_total']:,.2f})")
            print(f"  Distribution: {analysis['positive_pct']:.1f}% positive")

            print(f"\n  Sign convention: {analysis['sign_convention'].replace('_', ' ')}")
            print(f"    Rationale: {analysis['rationale']}")

            if analysis['suggest_negate']:
                print("\n  Recommendation: Use {-amount} to normalize signs")
                print("    Your data has expenses as NEGATIVE values.")
                print("    Using {-amount} will flip signs so expenses become positive.")
                print(f'\n    format: "{format_str.replace("{amount}", "{-amount}")}"')
                print("\n  OR: Keep raw signs and write sign-aware rules:")
                print("    match: contains(\"GROCERY\") and amount < 0  # expenses")
                print("    match: contains(\"REFUND\") and amount > 0   # credits")
            else:
                print("\n  Your data has expenses as POSITIVE values (standard convention).")
                print("  No sign normalization needed.")
                print("\n  To match by sign in rules:")
                print("    match: contains(\"GROCERY\") and amount > 0  # expenses")
                print("    match: contains(\"REFUND\") and amount < 0   # credits/refunds")

            # Always show the +amount option for mixed-sign sources
            print("\n  TIP: For mixed-sign sources (e.g., escrow accounts):")
            print(f'    format: "{format_str.replace("{amount}", "{+amount}")}"')
            print("    {+amount} takes absolute value - all amounts become positive.")

            # Show sample credits as hints
            if analysis['sample_credits']:
                print("\n  Sample negative amounts (may be refunds/credits/income):")
                for desc, amt in analysis['sample_credits'][:5]:
                    truncated = desc[:40] + '...' if len(desc) > 40 else desc
                    print(f"    ${amt:,.2f}  {truncated}")
                print("\n  Use special tags to handle these transactions:")
                print(f"    {C.CYAN}refund{C.RESET}   - Returns/credits (nets against merchant spending)")
                print(f"    {C.CYAN}income{C.RESET}   - Deposits/salary (excluded from spending)")
                print(f"    {C.CYAN}transfer{C.RESET} - Account transfers (excluded from spending)")
                print("\n  Example rule for refunds:")
                print("    [Amazon Refund]")
                print("    match: contains(\"AMAZON\") and amount < 0")
                print("    category: Shopping")
                print("    subcategory: Online")
                print(f"    {C.CYAN}tags: refund{C.RESET}")

    except ValueError as e:
        print(f"  Could not auto-detect: {e}")
        print("\n  Use a manual format string. Example:")
        print('    format: "{date:%m/%d/%Y}, {description}, {amount}"')

    print()


def _detect_file_format(filepath):
    """Detect if file is CSV, fixed-width text, or other format.

    Returns dict with:
        - format_type: 'csv', 'fixed_width', 'unknown'
        - delimiter: detected delimiter for CSV
        - has_header: whether file has headers
        - issues: list of potential issues detected
        - suggestions: list of suggestions
    """
    import re

    result = {
        'format_type': 'unknown',
        'delimiter': ',',
        'has_header': True,
        'issues': [],
        'suggestions': [],
        'sample_lines': []
    }

    with open(filepath, 'r', encoding='utf-8') as f:
        sample = f.read(8192)
        lines = sample.split('\n')[:20]
        result['sample_lines'] = lines

    # Check for fixed-width format indicators
    fixed_width_indicators = 0

    # Check if lines have consistent length (fixed-width)
    line_lengths = [len(l) for l in lines if l.strip() and not l.startswith('#')]
    if line_lengths:
        avg_len = sum(line_lengths) / len(line_lengths)
        if avg_len > 80 and max(line_lengths) - min(line_lengths) < 20:
            fixed_width_indicators += 1

    # Check for date pattern at start of lines (bank statement format)
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}\s{2,}')
    date_matches = sum(1 for l in lines if date_pattern.match(l))
    if date_matches >= 3:
        fixed_width_indicators += 2

    # Check for amounts with thousands separators at end of lines
    amount_at_end = re.compile(r'\s+-?[\d,]+\.\d{2}\s*$')
    amount_matches = sum(1 for l in lines if amount_at_end.search(l))
    if amount_matches >= 3:
        fixed_width_indicators += 1

    # Check if commas appear in what looks like amounts (thousands separators)
    # This would break CSV parsing
    thousands_pattern = re.compile(r'\d{1,3},\d{3}')
    has_thousands_separators = any(thousands_pattern.search(l) for l in lines)

    # Try CSV sniffing
    csv_dialect = None
    csv_header = True
    try:
        csv_dialect = csv.Sniffer().sniff(sample)
        csv_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        pass

    # Make determination
    if fixed_width_indicators >= 3:
        result['format_type'] = 'fixed_width'
        result['issues'].append("File appears to be fixed-width format (like Bank of America statements)")
        result['suggestions'].append("Use 'delimiter: regex' with a pattern, or convert to CSV")

        # Try to detect the fixed-width pattern
        # BOA format: MM/DD/YYYY  Description...  Amount  Balance
        if date_matches >= 3:
            result['suggestions'].append(
                'Suggested config:\n'
                '  delimiter: "regex:^(\\d{2}/\\d{2}/\\d{4})\\s+(.+?)\\s+([-\\d,]+\\.\\d{2})\\s+([-\\d,]+\\.\\d{2})$"\n'
                '  format: "{date:%m/%d/%Y}, {description}, {-amount}, {_}"\n'
                '  has_header: false'
            )
    elif csv_dialect:
        result['format_type'] = 'csv'
        result['delimiter'] = csv_dialect.delimiter
        result['has_header'] = csv_header

        if has_thousands_separators and csv_dialect.delimiter == ',':
            result['issues'].append("Warning: File contains comma thousands separators which may conflict with CSV delimiter")
            result['suggestions'].append("Ensure amount columns are quoted, or export with different delimiter")
    else:
        result['format_type'] = 'unknown'
        result['issues'].append("Could not determine file format")

    return result


def _analyze_amount_patterns(filepath, amount_col, has_header=True, delimiter=None, max_rows=1000):
    """
    Analyze amount column patterns to help users understand their data's sign convention.

    Returns dict with:
        - positive_count: number of positive amounts
        - negative_count: number of negative amounts
        - positive_total: sum of positive amounts
        - negative_total: sum of negative amounts (as positive number)
        - sign_convention: 'expenses_positive' or 'expenses_negative'
        - suggest_negate: True if user should use {-amount} to normalize
        - sample_credits: list of (description, amount) for likely transfers/income
    """
    import re as re_mod

    positive_count = 0
    negative_count = 0
    positive_total = 0.0
    negative_total = 0.0
    sample_credits = []  # (description, amount) tuples

    def parse_amount(val):
        """Parse amount string to float, handling currency symbols and parentheses."""
        if not val:
            return None
        val = val.strip()
        # Remove currency symbols, commas
        val = re_mod.sub(r'[$€£¥,]', '', val)
        # Handle parentheses as negative
        if val.startswith('(') and val.endswith(')'):
            val = '-' + val[1:-1]
        try:
            return float(val)
        except ValueError:
            return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if delimiter and delimiter.startswith('regex:'):
                # Regex-based parsing
                pattern = re_mod.compile(delimiter[6:])
                for i, line in enumerate(f):
                    if has_header and i == 0:
                        continue
                    if i >= max_rows:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    match = pattern.match(line)
                    if match:
                        groups = match.groups()
                        if amount_col < len(groups):
                            amount = parse_amount(groups[amount_col])
                            if amount is not None:
                                desc = groups[1] if len(groups) > 1 else ''
                                if amount >= 0:
                                    positive_count += 1
                                    positive_total += amount
                                else:
                                    negative_count += 1
                                    negative_total += abs(amount)
                                    if len(sample_credits) < 10:
                                        sample_credits.append((desc.strip(), amount))
            else:
                # Standard CSV
                reader = csv.reader(f)
                if has_header:
                    headers = next(reader, None)
                    desc_col = 1  # default
                    for idx, h in enumerate(headers or []):
                        hl = h.lower()
                        if 'desc' in hl or 'merchant' in hl or 'payee' in hl or 'name' in hl:
                            desc_col = idx
                            break
                else:
                    desc_col = 1

                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    if amount_col < len(row):
                        amount = parse_amount(row[amount_col])
                        if amount is not None:
                            desc = row[desc_col] if desc_col < len(row) else ''
                            if amount >= 0:
                                positive_count += 1
                                positive_total += amount
                            else:
                                negative_count += 1
                                negative_total += abs(amount)
                                if len(sample_credits) < 10:
                                    sample_credits.append((desc.strip(), amount))
    except Exception:
        return None

    total_count = positive_count + negative_count
    if total_count == 0:
        return None

    # Determine sign convention based on distribution
    # Expenses positive: mostly positive amounts (typical credit card export)
    # Expenses negative: mostly negative amounts (typical bank export)
    positive_pct = positive_count / total_count * 100

    if positive_pct > 70:
        sign_convention = 'expenses_positive'
        suggest_negate = False
        rationale = "mostly positive amounts (expenses are positive)"
    elif positive_pct < 30:
        sign_convention = 'expenses_negative'
        suggest_negate = True
        rationale = "mostly negative amounts (expenses are negative)"
    else:
        # Mixed - harder to tell
        if positive_total > negative_total:
            sign_convention = 'expenses_positive'
            suggest_negate = False
            rationale = "total positive exceeds negative"
        else:
            sign_convention = 'expenses_negative'
            suggest_negate = True
            rationale = "total negative exceeds positive"

    return {
        'positive_count': positive_count,
        'negative_count': negative_count,
        'positive_total': positive_total,
        'negative_total': negative_total,
        'positive_pct': positive_pct,
        'sign_convention': sign_convention,
        'suggest_negate': suggest_negate,
        'rationale': rationale,
        'sample_credits': sample_credits,
    }
