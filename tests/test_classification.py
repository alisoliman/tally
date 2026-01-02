"""Tests for the classification module."""

import pytest
from tally.classification import (
    INCOME_TAG, TRANSFER_TAG, INVESTMENT_TAG,
    SPECIAL_TAGS, EXCLUDED_FROM_SPENDING,
    get_tags_lower, is_income, is_transfer, is_investment,
    is_excluded_from_spending, normalize_amount, categorize_amount,
    calculate_cash_flow, calculate_transfers_net,
)


class TestTagHelpers:
    """Tests for tag classification helper functions."""

    def test_get_tags_lower_converts_to_lowercase(self):
        assert get_tags_lower(['Income', 'TRANSFER']) == {'income', 'transfer'}

    def test_get_tags_lower_handles_empty(self):
        assert get_tags_lower([]) == set()
        assert get_tags_lower(None) == set()

    def test_is_income(self):
        assert is_income(['income']) is True
        assert is_income(['Income']) is True  # Case insensitive
        assert is_income(['transfer']) is False
        assert is_income([]) is False

    def test_is_transfer(self):
        assert is_transfer(['transfer']) is True
        assert is_transfer(['Transfer']) is True
        assert is_transfer(['income']) is False

    def test_is_investment(self):
        assert is_investment(['investment']) is True
        assert is_investment(['Investment']) is True
        assert is_investment(['income']) is False

    def test_is_excluded_from_spending(self):
        # All special tags exclude from spending
        assert is_excluded_from_spending(['income']) is True
        assert is_excluded_from_spending(['transfer']) is True
        assert is_excluded_from_spending(['investment']) is True
        # Regular tags don't exclude
        assert is_excluded_from_spending(['groceries']) is False
        assert is_excluded_from_spending([]) is False


class TestNormalizeAmount:
    """Tests for normalize_amount function."""

    def test_income_uses_absolute_value(self):
        # Income from bank might be negative (credit)
        assert normalize_amount(-3000.00, ['income']) == 3000.00
        assert normalize_amount(3000.00, ['income']) == 3000.00

    def test_investment_uses_absolute_value(self):
        assert normalize_amount(-500.00, ['investment']) == 500.00
        assert normalize_amount(500.00, ['investment']) == 500.00

    def test_transfer_preserves_sign(self):
        # Transfers: positive = in, negative = out
        assert normalize_amount(100.00, ['transfer']) == 100.00
        assert normalize_amount(-100.00, ['transfer']) == -100.00

    def test_regular_transactions_preserve_sign(self):
        assert normalize_amount(50.00, ['groceries']) == 50.00
        assert normalize_amount(-25.00, ['refund']) == -25.00


class TestCategorizeAmount:
    """Tests for categorize_amount function."""

    def test_income_categorized(self):
        result = categorize_amount(-3000.00, ['income'])
        assert result['income'] == 3000.00
        assert result['spending'] == 0
        assert result['credits'] == 0

    def test_investment_categorized(self):
        result = categorize_amount(-500.00, ['investment'])
        assert result['investment'] == 500.00
        assert result['income'] == 0
        assert result['spending'] == 0

    def test_transfer_in_categorized(self):
        result = categorize_amount(100.00, ['transfer'])
        assert result['transfer_in'] == 100.00
        assert result['transfer_out'] == 0

    def test_transfer_out_categorized(self):
        result = categorize_amount(-100.00, ['transfer'])
        assert result['transfer_out'] == 100.00  # Stored as positive
        assert result['transfer_in'] == 0

    def test_spending_categorized(self):
        result = categorize_amount(50.00, [])
        assert result['spending'] == 50.00
        assert result['credits'] == 0

    def test_credit_categorized(self):
        result = categorize_amount(-25.00, ['refund'])
        assert result['credits'] == 25.00  # Stored as positive
        assert result['spending'] == 0


class TestCalculations:
    """Tests for total calculation functions."""

    def test_calculate_cash_flow(self):
        # income - spending + credits
        assert calculate_cash_flow(3000, 2000, 100) == 1100  # 3000 - 2000 + 100
        assert calculate_cash_flow(0, 500, 50) == -450  # 0 - 500 + 50
        assert calculate_cash_flow(1000, 1000, 0) == 0

    def test_calculate_transfers_net(self):
        # in - out
        assert calculate_transfers_net(500, 300) == 200
        assert calculate_transfers_net(100, 500) == -400
        assert calculate_transfers_net(0, 0) == 0
