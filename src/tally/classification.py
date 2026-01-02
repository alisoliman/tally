"""
Transaction Classification - Centralized classification logic.

This module defines constants and helper functions for classifying transactions
based on tags. Use these functions consistently across Python code.

The JavaScript equivalent is defined at the top of spending_report.js.
"""

from typing import List, Set, Dict

# =============================================================================
# CONSTANTS
# =============================================================================

# Tags with special meaning in spending analysis
INCOME_TAG = 'income'
TRANSFER_TAG = 'transfer'
INVESTMENT_TAG = 'investment'

# All special tags that affect classification
SPECIAL_TAGS: Set[str] = {INCOME_TAG, TRANSFER_TAG, INVESTMENT_TAG}

# Tags that exclude transactions from spending totals
EXCLUDED_FROM_SPENDING: Set[str] = {INCOME_TAG, TRANSFER_TAG, INVESTMENT_TAG}


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def get_tags_lower(tags: List[str]) -> Set[str]:
    """Convert tags list to lowercase set for consistent comparison."""
    return {t.lower() for t in (tags or [])}


def is_income(tags: List[str]) -> bool:
    """Check if transaction is tagged as income."""
    return INCOME_TAG in get_tags_lower(tags)


def is_transfer(tags: List[str]) -> bool:
    """Check if transaction is tagged as transfer."""
    return TRANSFER_TAG in get_tags_lower(tags)


def is_investment(tags: List[str]) -> bool:
    """Check if transaction is tagged as investment."""
    return INVESTMENT_TAG in get_tags_lower(tags)


def is_excluded_from_spending(tags: List[str]) -> bool:
    """Check if transaction should be excluded from spending totals."""
    tags_lower = get_tags_lower(tags)
    return bool(tags_lower & EXCLUDED_FROM_SPENDING)


# =============================================================================
# AMOUNT NORMALIZATION
# =============================================================================

def normalize_amount(amount: float, tags: List[str]) -> float:
    """
    Normalize transaction amount for consistent handling.

    Rules:
    - Income: Always positive (abs) - bank data may show as negative
    - Investment: Always positive (abs)
    - Transfer: Raw amount (positive = in, negative = out)
    - Spending/Credit: Raw amount (positive = purchase, negative = refund)

    Returns the normalized amount.
    """
    if is_income(tags) or is_investment(tags):
        return abs(amount)
    return amount


def categorize_amount(amount: float, tags: List[str]) -> Dict[str, float]:
    """
    Categorize a transaction amount into appropriate bucket.

    All returned values are positive (or zero). The sign is implicit in the key:
    - income: money coming in (always positive)
    - investment: retirement contributions (always positive)
    - transfer_in: money transferred in (positive transfers)
    - transfer_out: money transferred out (from negative transfers, stored positive)
    - spending: purchases (from positive non-tagged amounts)
    - credits: refunds/returns (from negative non-tagged amounts, stored positive)

    Returns dict with exactly one non-zero key.
    """
    result = {
        'income': 0.0,
        'investment': 0.0,
        'transfer_in': 0.0,
        'transfer_out': 0.0,
        'spending': 0.0,
        'credits': 0.0,
    }

    tags_lower = get_tags_lower(tags)

    if INCOME_TAG in tags_lower:
        result['income'] = abs(amount)
    elif INVESTMENT_TAG in tags_lower:
        result['investment'] = abs(amount)
    elif TRANSFER_TAG in tags_lower:
        if amount > 0:
            result['transfer_in'] = amount
        else:
            result['transfer_out'] = abs(amount)
    else:
        # Normal spending/credits
        if amount > 0:
            result['spending'] = amount
        else:
            result['credits'] = abs(amount)

    return result


# =============================================================================
# TOTALS CALCULATION
# =============================================================================

def calculate_cash_flow(income: float, spending: float, credits: float) -> float:
    """
    Calculate cash flow from totals.

    Args:
        income: Total income (positive)
        spending: Total spending (positive)
        credits: Total credits/refunds (positive)

    Returns:
        Cash flow = income - spending + credits
        (credits reduce net spending, so they add to cash flow)
    """
    return income - spending + credits


def calculate_transfers_net(transfers_in: float, transfers_out: float) -> float:
    """
    Calculate net transfers.

    Args:
        transfers_in: Total transfers in (positive)
        transfers_out: Total transfers out (positive)

    Returns:
        Net = in - out (positive means net inflow)
    """
    return transfers_in - transfers_out
