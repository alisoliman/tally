"""
Integration tests for config loading with personal finance data.

Tests the full configuration loading pipeline including accounts, snapshots, and plans.
"""

import pytest
from pathlib import Path
from src.tally.config_loader import load_config


def test_load_config_with_no_personal_finance_files(tmp_path):
    """Test config loading when no personal finance files exist."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    config = load_config(str(config_dir))

    # Personal finance data should be empty lists
    assert config['accounts'] == []
    assert config['snapshots'] == []
    assert config['plans'] == []


def test_load_config_with_accounts_only(tmp_path):
    """Test config loading with accounts.yaml but no snapshots or plans."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    # Create accounts.yaml
    accounts = config_dir / "accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Main Checking
    kind: cash
    currency: USD

  - id: savings
    name: High-Yield Savings
    kind: cash
    currency: USD
""")

    config = load_config(str(config_dir))

    # Should have 2 accounts
    assert len(config['accounts']) == 2
    assert config['accounts'][0].id == 'checking'
    assert config['accounts'][0].name == 'Main Checking'
    assert config['accounts'][1].id == 'savings'

    # No snapshots or plans
    assert config['snapshots'] == []
    assert config['plans'] == []


def test_load_config_with_full_personal_finance(tmp_path):
    """Test config loading with accounts, snapshots, and plans."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    # Create accounts.yaml
    accounts = config_dir / "accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Main Checking
    kind: cash
    currency: USD

  - id: 401k
    name: Vanguard 401k
    kind: investment
    currency: USD
""")

    # Create snapshots.yaml
    snapshots = config_dir / "snapshots.yaml"
    snapshots.write_text("""
snapshots:
  - account: checking
    date: 2025-01-01
    value: 5000.00

  - account: 401k
    date: 2025-01-01
    value: 100000.00
    note: "Q4 2024 statement"
""")

    # Create plans.yaml
    plans = config_dir / "plans.yaml"
    plans.write_text("""
plans:
  - id: 401k-monthly
    type: invest
    from: checking
    to: 401k
    amount: 500.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

    config = load_config(str(config_dir))

    # Verify accounts
    assert len(config['accounts']) == 2
    assert config['accounts'][0].id == 'checking'
    assert config['accounts'][1].id == '401k'

    # Verify snapshots
    assert len(config['snapshots']) == 2
    assert config['snapshots'][0].account_id == 'checking'
    assert config['snapshots'][0].value == 5000.00
    assert config['snapshots'][1].account_id == '401k'
    assert config['snapshots'][1].note == 'Q4 2024 statement'

    # Verify plans
    assert len(config['plans']) == 1
    assert config['plans'][0].id == '401k-monthly'
    assert config['plans'][0].from_account_id == 'checking'
    assert config['plans'][0].to_account_id == '401k'
    assert config['plans'][0].amount == 500.00


def test_load_config_with_custom_filenames(tmp_path):
    """Test config loading with custom file paths specified in settings."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml with custom file paths
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
accounts_file: my_accounts.yaml
snapshots_file: my_balances.yaml
""")

    # Create custom accounts file
    accounts = config_dir / "my_accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Test Account
    kind: cash
    currency: EUR
""")

    # Create custom snapshots file
    snapshots = config_dir / "my_balances.yaml"
    snapshots.write_text("""
snapshots:
  - account: checking
    date: 2025-01-01
    value: 1000.00
""")

    config = load_config(str(config_dir))

    # Should load from custom files
    assert len(config['accounts']) == 1
    assert config['accounts'][0].currency == 'EUR'
    assert len(config['snapshots']) == 1
    assert config['plans'] == []  # No custom plans file


def test_load_config_with_validation_errors(tmp_path):
    """Test that validation errors are captured in warnings."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    # Create accounts.yaml
    accounts = config_dir / "accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Main Checking
    kind: cash
    currency: USD
""")

    # Create plans.yaml with invalid account references
    plans = config_dir / "plans.yaml"
    plans.write_text("""
plans:
  - id: bad-plan
    type: invest
    from: nonexistent-account
    to: checking
    amount: 100.00
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
""")

    config = load_config(str(config_dir))

    # Should have validation errors in warnings
    assert len(config['_warnings']) > 0
    error_messages = [w['message'] for w in config['_warnings'] if w['type'] == 'error']
    assert any('nonexistent-account' in msg for msg in error_messages)


def test_load_config_with_snapshot_warnings(tmp_path):
    """Test that snapshots referencing missing accounts generate warnings."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    # Create accounts.yaml with one account
    accounts = config_dir / "accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Main Checking
    kind: cash
    currency: USD
""")

    # Create snapshots.yaml with reference to missing account
    snapshots = config_dir / "snapshots.yaml"
    snapshots.write_text("""
snapshots:
  - account: checking
    date: 2025-01-01
    value: 1000.00

  - account: missing-account
    date: 2025-01-01
    value: 5000.00
""")

    config = load_config(str(config_dir))

    # Should have warning about missing account
    warnings = [w for w in config['_warnings'] if w['type'] == 'warning']
    assert any('missing-account' in w['message'] for w in warnings)


def test_load_config_without_pyyaml(tmp_path, monkeypatch):
    """Test graceful handling when PyYAML is not installed."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create settings.yaml
    settings = config_dir / "settings.yaml"
    settings.write_text("""
title: "Test Analysis"
data_sources: []
""")

    # Create accounts.yaml
    accounts = config_dir / "accounts.yaml"
    accounts.write_text("""
accounts:
  - id: checking
    name: Main Checking
    kind: cash
    currency: USD
""")

    # Mock the import to simulate PyYAML not being available
    import src.tally.accounts_loader as loader_module
    monkeypatch.setattr(loader_module, 'HAS_YAML', False)

    config = load_config(str(config_dir))

    # Should have error about missing PyYAML
    errors = [w for w in config['_warnings'] if w['type'] == 'error']
    assert any('PyYAML' in w['message'] for w in errors)

    # Personal finance data should be empty
    assert config['accounts'] == []
    assert config['snapshots'] == []
    assert config['plans'] == []
