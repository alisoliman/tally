# Tally v1 Implementation Plan
## Personal Finance Modeling System

**Status:** Planning Phase
**Date:** 2026-01-08 (Updated)
**Branch:** claude/tally-v1-plan-updated
**Based on:** Latest main (commit 120fa5c)

---

## Executive Summary

### Current State (Latest main - Jan 2026)

Tally is a **transaction categorization and spending analysis tool** that:
- Parses CSV transaction exports from banks (supports folders and glob patterns)
- Categorizes transactions using powerful expression-based rule engine
- Supports field transforms and custom captures
- Generates HTML/JSON/Markdown reports with spending summaries
- Includes report diff feature to track changes between runs
- Well-architected with modular CLI commands
- Focuses exclusively on historical expense analysis

### Target State (v1)

Transform Tally into a **comprehensive personal finance modeling system** that:
- Tracks accounts (cash and investment) with balances
- Records authoritative snapshots (balance truth at points in time)
- Models future plans (recurring investments, savings goals)
- Analyzes historical transactions (income and expenses)
- Supports multi-currency portfolios
- Generates net worth and budget projections

### Core Philosophy

**The v1 mental model:**
- **Plans** say what should happen (future intent)
- **Transactions** say what did happen (historical evidence)
- **Snapshots** say what is true now (authoritative state)

This model eliminates the need for reconciliation while maintaining simplicity.

---

## Current Architecture Analysis (Updated Jan 2026)

### File Structure (Latest)

```
tally/
├── src/tally/
│   ├── analyzer.py           # Core transaction analysis + report diff
│   ├── classification.py     # Transaction categorization logic
│   ├── config_loader.py      # Settings and data source loading
│   ├── merchant_engine.py    # Rule matching engine
│   ├── merchant_utils.py     # Merchant normalization
│   ├── parsers.py            # CSV parsing
│   ├── report.py             # HTML report generation
│   ├── section_engine.py     # View grouping logic
│   ├── format_parser.py      # Format string parsing
│   ├── expr_parser.py        # Expression parsing
│   ├── modifier_parser.py    # Field transform parsing
│   ├── cli.py                # Main CLI entry point (streamlined)
│   ├── cli_utils.py          # NEW: CLI utilities (config resolution)
│   ├── colors.py             # NEW: Terminal color support
│   ├── path_utils.py         # NEW: Path resolution (glob/folder support)
│   ├── templates.py          # Starter file templates
│   ├── migrations.py         # Config migrations
│   └── commands/             # CLI subcommands (modular)
│       ├── run.py           # tally up command
│       ├── explain.py       # tally explain
│       ├── discover.py      # tally discover
│       ├── diag.py          # tally diag
│       ├── inspect.py       # tally inspect
│       ├── workflow.py      # tally workflow
│       ├── reference.py     # tally reference
│       ├── init.py          # tally init
│       └── update.py        # tally update
├── config/                   # Example configurations
├── data/                     # User transaction CSVs
└── output/                   # Generated reports
```

### Recent Architecture Improvements (Relevant to v1)

1. **Modular CLI Architecture** (`cli_utils.py`, `colors.py`)
   - Config resolution extracted to reusable functions
   - `resolve_config_dir()` handles --config flag and auto-detection
   - Terminal color support separated
   - Better foundation for adding v1 commands

2. **Path Resolution System** (`path_utils.py`)
   - `resolve_data_source_paths()` supports files, directories, and globs
   - Handles recursive patterns (`**/*.csv`)
   - Performance warnings for expensive glob patterns
   - **v1 implication**: Can use same system for discovering snapshot/account files

3. **Report Diff Feature** (`analyzer.py`)
   - `compare_reports()` tracks changes between runs
   - Detects new/removed merchants, tag changes, category changes
   - `format_diff_summary()` and `format_diff_detailed()` for output
   - **v1 implication**: Can add net worth diff, balance change tracking

4. **Field Transforms**
   - Support for `field.amount` transforms (fee columns)
   - Transform system already in place
   - **v1 implication**: Could use for account-specific amount adjustments

5. **Deprecated Settings Handling**
   - `year` setting deprecated in favor of `title`
   - Clean migration warnings system
   - **v1 implication**: Good pattern to follow for v1 opt-in features

### Key Data Structures (Current)

#### Transaction (current)
```python
{
    'date': datetime,
    'amount': float,           # Positive = expense, Negative = refund
    'description': str,
    'merchant': str,           # Normalized
    'category': str,
    'subcategory': str,
    'tags': List[str],        # e.g., ['income', 'transfer', 'business']
    'source': str,            # Which data source
    'extra_fields': Dict,     # Custom captures from format string
    'match_info': Dict        # Which rule matched
}
```

#### Analysis Results
```python
{
    'by_merchant': {
        'merchant_name': {
            'total': float,
            'count': int,
            'monthly_value': float,
            'months_active': int,
            'category': str,
            'subcategory': str,
            'tags': Set[str],
            'transactions': List[dict]
        }
    },
    'by_category': {...},
    'by_month': {...},
    'income_total': float,
    'spending_total': float,
    'cash_flow': float,
    'transfers_in': float,
    'transfers_out': float,
    'investment_total': float,
    'gross_spending': float,    # For percentage calculations
}
```

### Current Strengths (Reaffirmed)

1. **Flexible CSV Parsing** - Format strings + glob/folder support
2. **Powerful Rule Engine** - Expression-based with field transforms
3. **Tag System** - Special tags control classification
4. **Views/Sections** - Custom spending groupings
5. **Multiple Output Formats** - HTML, JSON, Markdown
6. **Report Diff** - Track changes between runs
7. **Modular Architecture** - Well-organized command structure
8. **Path Flexibility** - Supports files, folders, globs

### Current Limitations (v1 will address)

1. **No Account Tracking** - Doesn't know about bank accounts or balances
2. **No Balance State** - Cannot track what you currently own
3. **No Multi-Currency** - Assumes single currency
4. **No Future Planning** - Only analyzes past transactions
5. **Spending-Focused** - Designed for expense analysis, not net worth
6. **No Investment Tracking** - Investment contributions are tagged but not tracked as assets

---

## New Domain Model

### 1. Account

**Definition:** Anything with a balance you care about (checking, savings, brokerage, 401k).

```python
class Account:
    id: str                    # Unique identifier (user-defined)
    name: str                  # Display name
    kind: AccountKind          # Enum: CASH, INVESTMENT
    currency: str              # ISO code (EUR, USD, GBP)

    # Derived (not stored):
    current_balance: float     # From latest snapshot
    last_updated: date         # Date of latest snapshot
```

**Account Kinds:**
- `CASH` - Spendable money (checking, savings, cash)
- `INVESTMENT` - Owned value, not directly spendable (brokerage, 401k, IRA, stocks)

**Design Decisions:**
- Account kind affects budgeting logic (only cash is "spendable")
- No sub-types in v1 (no distinction between checking vs savings)
- Currency is per-account (enables multi-currency portfolios)

### 2. Snapshot

**Definition:** An authoritative point-in-time balance for an account.

```python
class Snapshot:
    account_id: str
    date: date
    value: float               # In account currency
    note: Optional[str]
    attachment: Optional[str]  # Path to screenshot/statement
```

**Rules:**
- Latest snapshot per account = current truth
- Snapshots can jump freely (no reconciliation needed)
- Initial balance = first snapshot
- No assumptions about transaction completeness

**Why Snapshots?**
- Bank scraping is unreliable and breaks frequently
- Manual screenshots/checks are reliable
- Users know their balances accurately from bank apps
- Avoids complex reconciliation logic

### 3. Plan

**Definition:** Recurring intent for future actions.

```python
class Plan:
    id: str
    type: PlanType             # Enum: INVEST, SAVE, WITHDRAW (v1: only INVEST)
    from_account_id: str       # Must be CASH
    to_account_id: str         # Must be INVESTMENT (for INVEST)
    amount: float
    currency: str              # Must match both accounts
    cadence: Cadence           # Enum: MONTHLY (v1 only)
    start_date: date
    status: PlanStatus         # Enum: ACTIVE, PAUSED
```

**v1 Scope: Investment Plans Only**
```python
# Example: Monthly 401k contribution
{
    'id': '401k-monthly',
    'type': PlanType.INVEST,
    'from_account_id': 'checking',
    'to_account_id': '401k',
    'amount': 500.00,
    'currency': 'USD',
    'cadence': Cadence.MONTHLY,
    'start_date': date(2025, 1, 1),
    'status': PlanStatus.ACTIVE
}
```

**Design Decisions:**
- Plans affect budget projections, not balances
- No automatic execution or transaction matching
- Plans are declarative (what *should* happen)
- Transactions are evidence (what *did* happen)
- These can differ without reconciliation

### 4. Transaction (Enhanced)

**Definition:** A cash-flow event (past-looking). Extends current transaction model.

```python
class Transaction:
    # Existing fields (keep current structure)
    date: date
    amount: float
    currency: str              # NEW: Currency of transaction
    description: str
    category: str
    subcategory: str
    direction: Direction       # NEW: Enum: INCOME, EXPENSE
    tags: List[str]

    # NEW: Optional account linkage (v1 allows None)
    account_id: Optional[str]  # Which account this transaction affects

    # Existing fields
    merchant: str
    source: str               # CSV data source name
    extra_fields: Dict
    match_info: Dict
```

**v1 Behavior:**
- Transactions don't define balances (snapshots do)
- `account_id` is optional in v1 (backward compatible)
- Used for income/expense reporting and budgeting
- No balance reconciliation

---

## Storage Architecture

### Design Philosophy
**File-based, version-controllable, AI-friendly**

### Storage Layers

#### 1. Configuration Files (User-Editable)

```
tally/
├── config/
│   ├── settings.yaml         # Existing: data sources, output settings
│   ├── accounts.yaml         # NEW: Account definitions
│   ├── snapshots.yaml        # NEW: Balance snapshots
│   ├── plans.yaml            # NEW: Investment plans
│   ├── merchants.rules       # Existing: Transaction categorization
│   └── views.rules           # Existing: Spending groupings
├── data/
│   ├── transactions-2025.csv # Existing: Transaction imports
│   └── ...
└── output/
    ├── spending_summary.html  # Existing: Spending report
    ├── networth_report.html   # NEW: Net worth dashboard
    └── budget_projection.html # NEW: Budget projections
```

#### 2. accounts.yaml Format

```yaml
# Tally Accounts
# Define all accounts with balances you want to track

accounts:
  # Cash accounts (spendable money)
  - id: checking
    name: Chase Checking
    kind: cash
    currency: USD

  - id: savings
    name: Ally Savings
    kind: cash
    currency: USD

  # Investment accounts (owned value, not spendable)
  - id: 401k
    name: Vanguard 401(k)
    kind: investment
    currency: USD

  - id: brokerage
    name: Fidelity Brokerage
    kind: investment
    currency: USD

  # Multi-currency example
  - id: eu-checking
    name: N26 Checking (Europe)
    kind: cash
    currency: EUR
```

#### 3. snapshots.yaml Format

```yaml
# Tally Snapshots
# Record point-in-time balances (the authoritative truth)
# Latest snapshot per account = current balance

snapshots:
  # Checking account
  - account: checking
    date: 2025-01-01
    value: 5432.10
    note: "Starting balance"

  - account: checking
    date: 2025-01-08
    value: 4821.45
    note: "After rent payment"

  # Savings account
  - account: savings
    date: 2025-01-01
    value: 10000.00

  - account: savings
    date: 2025-01-08
    value: 10500.00
    attachment: screenshots/savings-jan-8.png

  # Investment accounts
  - account: 401k
    date: 2025-01-01
    value: 125000.00
    note: "Statement balance"

  - account: brokerage
    date: 2025-01-01
    value: 45000.00
    note: "Market value"
```

#### 4. plans.yaml Format

```yaml
# Tally Plans
# Define recurring financial intentions (investments, savings goals)

plans:
  # Monthly 401k contribution
  - id: 401k-monthly
    type: invest
    from: checking          # Must be a cash account
    to: 401k                # Must be an investment account
    amount: 500.00
    currency: USD           # Must match both accounts
    cadence: monthly
    start_date: 2025-01-01
    status: active

  # Paused plan example
  - id: ira-biweekly
    type: invest
    from: checking
    to: ira
    amount: 250.00
    currency: USD
    cadence: biweekly       # Future: not v1
    start_date: 2025-01-15
    status: paused
```

#### 5. Data Loading Architecture (Extends Existing)

```python
# config_loader.py (existing module, will be extended)

def load_config(config_dir):
    """Load all configuration (existing function, will be enhanced)."""
    config = {
        # Existing
        'data_sources': load_data_sources(config_dir),
        'merchants_file': load_merchants_file(config_dir),
        'views_file': load_views_file(config_dir),
        'currency_format': load_currency_format(config_dir),
        'title': config.get('title', 'Financial Report'),

        # NEW for v1
        'accounts': load_accounts(config_dir),
        'snapshots': load_snapshots(config_dir),
        'plans': load_plans(config_dir),
        'primary_currency': load_primary_currency(config_dir),
    }
    return config

def load_accounts(config_dir) -> List[Account]:
    """Load accounts from accounts.yaml."""
    accounts_file = os.path.join(config_dir, 'accounts.yaml')
    if not os.path.exists(accounts_file):
        return []

    with open(accounts_file, 'r') as f:
        data = yaml.safe_load(f) or {}

    accounts = []
    for acc_data in data.get('accounts', []):
        accounts.append(Account(
            id=acc_data['id'],
            name=acc_data['name'],
            kind=AccountKind(acc_data['kind'].lower()),
            currency=acc_data['currency']
        ))
    return accounts

def load_snapshots(config_dir) -> List[Snapshot]:
    """Load snapshots from snapshots.yaml."""
    # Similar implementation
    pass

def load_plans(config_dir) -> List[Plan]:
    """Load plans from plans.yaml."""
    # Similar implementation
    pass
```

### Leveraging Existing Infrastructure

**Path Resolution** (use `path_utils.py`):
```python
# Could support glob patterns for snapshot files
# Example: snapshots/*.yaml or snapshots/**/*.yaml
from .path_utils import resolve_data_source_paths

snapshot_files, kind = resolve_data_source_paths(
    config_dir,
    config.get('snapshots_file', 'config/snapshots.yaml')
)
```

**Config Resolution** (use `cli_utils.py`):
```python
# v1 commands can use existing resolve_config_dir()
from .cli_utils import resolve_config_dir

config_dir = resolve_config_dir(args, required=True)
```

---

## Configuration Design

### settings.yaml Extensions

```yaml
# Existing settings (keep all)
title: "2025 Budget Analysis"      # NEW: replaces deprecated 'year'
data_sources: [...]
output_dir: output
merchants_file: config/merchants.rules
views_file: config/views.rules
currency_format: "€{amount}"

# NEW v1 settings
primary_currency: EUR          # Default currency for UI/reports
accounts_file: config/accounts.yaml
snapshots_file: config/snapshots.yaml
plans_file: config/plans.yaml

# NEW: Currency-specific formats (optional)
currency_formats:
  USD: "${amount}"
  EUR: "€{amount}"
  GBP: "£{amount}"
  PLN: "{amount} zł"

# NEW: v1 feature flag (optional, auto-detected if files exist)
enable_v1_features: true
```

### Backward Compatibility Strategy

**Principles:**
1. v1 features are **additive** - existing configs work unchanged
2. If `accounts.yaml` doesn't exist, v1 features are disabled
3. Transaction analysis works independently of account tracking
4. Users can adopt v1 features incrementally

**Detection Pattern** (extends existing patterns):
```python
def is_v1_enabled(config):
    """Check if user has opted into v1 features."""
    # Explicit flag
    if config.get('enable_v1_features') is False:
        return False

    # Auto-detect: if accounts.yaml exists and has accounts
    return len(config.get('accounts', [])) > 0

# In analyzer.py or commands/run.py
def analyze_and_report(config):
    # Existing transaction analysis (always runs)
    transaction_stats = analyze_transactions(transactions)

    # v1 features (only if enabled)
    if is_v1_enabled(config):
        from .networth import calculate_networth
        from .budget import calculate_budget

        accounts = config['accounts']
        snapshots = config['snapshots']
        plans = config['plans']

        networth_stats = calculate_networth(accounts, snapshots)
        budget_stats = calculate_budget(accounts, snapshots, plans, transaction_stats)

        # Generate new reports
        generate_networth_report(config, networth_stats)
        generate_budget_report(config, budget_stats)
```

---

## Multi-Currency Support

### Design Principles
1. **No FX conversion in v1** - Avoid exchange rate complexity
2. **Group by currency** - Reports show totals per currency
3. **Account-level currency** - Each account has its own currency
4. **Primary currency for UI** - Default display format

### Data Model

```python
class Account:
    currency: str  # ISO code (EUR, USD, GBP, etc.)

class Snapshot:
    value: float   # In account.currency

class Transaction:
    currency: str  # Currency of transaction (may differ from account)
```

### Reporting Strategy

#### Cash Position (by currency)
```python
{
    'USD': {
        'accounts': [
            {'name': 'Chase Checking', 'balance': 4821.45},
            {'name': 'Ally Savings', 'balance': 10500.00}
        ],
        'total': 15321.45
    },
    'EUR': {
        'accounts': [
            {'name': 'N26 Checking', 'balance': 2500.00}
        ],
        'total': 2500.00
    }
}
```

#### Net Worth (by currency)
```python
{
    'USD': {
        'cash': 15321.45,
        'investments': 170000.00,
        'total': 185321.45
    },
    'EUR': {
        'cash': 2500.00,
        'investments': 0.00,
        'total': 2500.00
    }
}
```

### UI Display (Extends Existing Format Helpers)

```python
# report.py already has format_currency()
# Extend for multi-currency display

def format_currency_by_code(amount, currency_code, config):
    """Format amount with currency-specific format."""
    formats = config.get('currency_formats', {})
    format_str = formats.get(currency_code, config.get('currency_format', '${amount}'))
    return format_currency(amount, format_str)
```

---

## Budgeting Engine

### v1 Budgeting Scope

**Inputs:**
1. Income transactions (from CSV imports, tagged `income`)
2. Expense transactions (from CSV imports)
3. Active investment plans (from `plans.yaml`)
4. Cash account balances (from latest snapshots)

**Outputs:**
1. Monthly income
2. Monthly expenses
3. Planned investments
4. Available cash (after investments)
5. Surplus/deficit

### Calculation Logic

```python
# budget.py (new module)

def calculate_budget(accounts, snapshots, plans, transaction_stats, config):
    """
    Calculate monthly budget projections.

    Returns budget breakdown per currency.
    """
    # Get latest cash balances by currency
    cash_by_currency = {}
    for account in accounts:
        if account.kind != AccountKind.CASH:
            continue
        latest_snapshot = get_latest_snapshot(snapshots, account.id)
        if latest_snapshot:
            if account.currency not in cash_by_currency:
                cash_by_currency[account.currency] = 0
            cash_by_currency[account.currency] += latest_snapshot.value

    # Get active investment plans grouped by currency
    active_plans = [p for p in plans if p.status == PlanStatus.ACTIVE]
    investments_by_currency = {}
    for plan in active_plans:
        if plan.currency not in investments_by_currency:
            investments_by_currency[plan.currency] = 0

        # Monthly investment amount (v1: only monthly cadence)
        if plan.cadence == Cadence.MONTHLY:
            investments_by_currency[plan.currency] += plan.amount

    # Get income and spending from transactions
    income_total = transaction_stats.get('income_total', 0)
    spending_total = transaction_stats.get('spending_total', 0)

    # NOTE: v1 assumes single currency for transactions
    # Multi-currency transaction support is future work
    primary_currency = config.get('primary_currency', 'EUR')

    num_months = transaction_stats.get('num_months', 12)

    return {
        primary_currency: {
            'income_monthly': income_total / num_months,
            'expenses_monthly': spending_total / num_months,
            'investments_monthly': investments_by_currency.get(primary_currency, 0),
            'cash_available': cash_by_currency.get(primary_currency, 0),
            'net_monthly': (income_total / num_months) - (spending_total / num_months) - investments_by_currency.get(primary_currency, 0)
        }
    }
```

### Budget Report Output

```
Monthly Budget (EUR)
════════════════════
Income:              +€4,500/mo
Expenses:            -€3,200/mo
Investments:         -€500/mo  (401k)
                     ──────────
Net Cash Flow:       +€800/mo

Cash Available:      €7,500
```

---

## Reporting System

### New Reports (v1)

#### 1. Net Worth Dashboard

**File:** `output/networth_report.html`

**Sections:**
1. **Cash Position** - Sum of cash account balances
2. **Investment Position** - Sum of investment account balances
3. **Net Worth** - Cash + Investments
4. **Account List** - All accounts with latest snapshot

**Mockup:**
```
═══════════════════════════════════════════
NET WORTH REPORT
As of January 8, 2025
═══════════════════════════════════════════

CASH ACCOUNTS (USD)
─────────────────────────────────────────
Chase Checking          $4,821.45  (Jan 8)
Ally Savings           $10,500.00  (Jan 8)
─────────────────────────────────────────
Total Cash             $15,321.45

INVESTMENT ACCOUNTS (USD)
─────────────────────────────────────────
Vanguard 401(k)       $125,000.00  (Jan 1)
Fidelity Brokerage     $45,000.00  (Jan 1)
─────────────────────────────────────────
Total Investments     $170,000.00

═══════════════════════════════════════════
NET WORTH (USD)       $185,321.45
═══════════════════════════════════════════
```

**Leverage Existing Report Infrastructure:**
- Use `report.py` templates system
- Reuse `format_currency()` helpers
- Follow existing HTML report patterns
- Could integrate with report diff feature (show net worth changes)

#### 2. Budget Projection Report

**File:** `output/budget_report.html`

**Sections:**
1. **Monthly Budget** - Income, expenses, investments, net
2. **Active Plans** - Investment commitments
3. **Cash Flow Forecast** - Next 3 months projection

**Integration with Existing:**
- Can show alongside spending report
- Use same currency formatting
- Leverage existing views/sections system for grouping

---

## Implementation Phases

### Phase 0: Planning & Architecture ✅ (Current)
**Duration:** Completed
**Deliverables:**
- [x] Implementation plan document (this file)
- [x] Architecture analysis of latest codebase
- [x] Data model specification
- [x] Configuration format examples

### Phase 1: Core Domain Objects
**Duration:** 2 weeks
**Deliverables:**
- [ ] `Account`, `Snapshot`, `Plan` classes (src/tally/domain.py)
- [ ] YAML loading for accounts/snapshots/plans (src/tally/v1_loader.py)
- [ ] Extend `config_loader.py` for v1 files
- [ ] Validation logic (currency matching, date ordering)
- [ ] Unit tests for domain objects

**Files to Create:**
- `src/tally/domain.py` - Domain object classes and enums
- `src/tally/v1_loader.py` - v1-specific config loading
- `tests/test_domain.py` - Domain object tests
- `tests/test_v1_loader.py` - Config loading tests

**Files to Modify:**
- `src/tally/config_loader.py` - Add v1 file loading
- `src/tally/cli_utils.py` - Add v1 detection helpers

**Leverage Existing:**
- Use `path_utils.resolve_data_source_paths()` for file resolution
- Follow existing YAML loading patterns from `config_loader.py`
- Use existing validation patterns

### Phase 2: Storage & Configuration
**Duration:** 1 week
**Deliverables:**
- [ ] accounts.yaml schema and parser
- [ ] snapshots.yaml schema and parser
- [ ] plans.yaml schema and parser
- [ ] settings.yaml extensions
- [ ] Starter templates for v1 files

**Files to Create:**
- `config/accounts.yaml.example`
- `config/snapshots.yaml.example`
- `config/plans.yaml.example`

**Files to Modify:**
- `src/tally/templates.py` - Add v1 starter templates
- `src/tally/cli_utils.py` - Add v1 init helpers
- `config/settings.yaml.example` - Add v1 settings

**Leverage Existing:**
- Follow patterns from `STARTER_SETTINGS`, `STARTER_MERCHANTS` in templates.py
- Use existing `init_config()` in `cli_utils.py`

### Phase 3: Multi-Currency Support
**Duration:** 1 week
**Deliverables:**
- [ ] Currency grouping logic
- [ ] Per-currency totals
- [ ] Currency formatting helpers (extend existing)
- [ ] Tests for multi-currency scenarios

**Files to Modify:**
- `src/tally/report.py` - Extend `format_currency()` for multi-currency
- `src/tally/analyzer.py` - Currency-aware aggregations

**Leverage Existing:**
- Extend existing `format_currency()` in report.py
- Use existing `currency_format` config pattern

### Phase 4: Net Worth Calculation
**Duration:** 1 week
**Deliverables:**
- [ ] Net worth calculation engine
- [ ] Cash position aggregation
- [ ] Investment position aggregation
- [ ] Latest snapshot resolution per account
- [ ] Tests for net worth calculations

**Files to Create:**
- `src/tally/networth.py` - Net worth calculation logic

### Phase 5: Budgeting Engine
**Duration:** 2 weeks
**Deliverables:**
- [ ] Budget calculation logic
- [ ] Plan-based projections
- [ ] Cash flow analysis
- [ ] Investment commitment tracking
- [ ] Tests for budget scenarios

**Files to Create:**
- `src/tally/budget.py` - Budget calculation engine

### Phase 6: Net Worth Report
**Duration:** 2 weeks
**Deliverables:**
- [ ] Net worth HTML report template
- [ ] Account list view
- [ ] Currency-grouped displays
- [ ] Optional: Net worth diff (integrate with report diff feature)
- [ ] Tests with Playwright MCP

**Files to Create:**
- `src/tally/templates/networth_report.html`
- `src/tally/templates/networth_report.css`
- `src/tally/templates/networth_report.js`

**Files to Modify:**
- `src/tally/report.py` - Add `generate_networth_report()`

**Leverage Existing:**
- Use template patterns from existing HTML reports
- Reuse Vue.js patterns if applicable
- Integrate with `compare_reports()` for diff feature

### Phase 7: Budget Report
**Duration:** 2 weeks
**Deliverables:**
- [ ] Budget HTML report template
- [ ] Monthly projection view
- [ ] Plan summary view
- [ ] Cash runway calculations
- [ ] Tests with Playwright MCP

**Files to Create:**
- `src/tally/templates/budget_report.html`
- `src/tally/templates/budget_report.css`
- `src/tally/templates/budget_report.js`

**Files to Modify:**
- `src/tally/report.py` - Add `generate_budget_report()`

### Phase 8: CLI Integration
**Duration:** 1 week
**Deliverables:**
- [ ] New CLI commands (tally networth, tally budget)
- [ ] Extend `tally up` for v1 reports
- [ ] v1 init command (tally v1 init)
- [ ] CLI help updates

**Files to Create:**
- `src/tally/commands/networth.py` - tally networth command
- `src/tally/commands/budget.py` - tally budget command
- `src/tally/commands/v1_init.py` - tally v1 init command

**Files to Modify:**
- `src/tally/cli.py` - Add v1 subparsers
- `src/tally/commands/run.py` - Integrate v1 reports into `tally up`

**Leverage Existing:**
- Follow command module patterns from `commands/` directory
- Use `resolve_config_dir()` from `cli_utils.py`
- Follow existing argparse patterns in `cli.py`

### Phase 9: Documentation & Migration
**Duration:** 1 week
**Deliverables:**
- [ ] User documentation for v1 features
- [ ] Migration guide for existing users
- [ ] Configuration examples
- [ ] Update CLAUDE.md with v1 guidance
- [ ] Update README.md

**Files to Create:**
- `docs/v1-guide.md`
- `docs/migration.md`

**Files to Modify:**
- `README.md` - Add v1 overview
- `CLAUDE.md` - Add v1 development notes

### Phase 10: Testing & Refinement
**Duration:** 2 weeks
**Deliverables:**
- [ ] Integration tests for full workflows
- [ ] Multi-currency test scenarios
- [ ] Edge case handling
- [ ] Performance testing (large datasets)
- [ ] User acceptance testing

**Leverage Existing:**
- Follow test patterns from `tests/` directory
- Use existing conftest.py fixtures
- Extend existing test infrastructure

---

## Migration Strategy

### Backward Compatibility

**Goal:** Existing Tally users can upgrade without breaking changes.

**Non-Breaking Additions:**
- v1 code is opt-in (disabled by default)
- Existing `tally up` command works unchanged
- All existing tests continue to pass
- No changes to existing report formats unless v1 enabled

**v1 Detection:**
```python
# Automatically enabled if accounts.yaml exists with accounts
def is_v1_enabled(config):
    return len(config.get('accounts', [])) > 0
```

**Migration Guide (documentation):**
```markdown
# Migrating to Tally v1

Tally v1 adds account tracking, snapshots, and financial planning.

## Step 1: Create accounts.yaml

```yaml
accounts:
  - id: checking
    name: My Checking
    kind: cash
    currency: USD
```

## Step 2: Add Current Balances (snapshots.yaml)

```yaml
snapshots:
  - account: checking
    date: 2025-01-08
    value: 5432.10
```

## Step 3: (Optional) Define Plans

```yaml
plans:
  - id: 401k
    type: invest
    from: checking
    to: retirement
    amount: 500
    currency: USD
    cadence: monthly
    status: active
```

## Step 4: Run tally up

v1 features automatically enable when accounts.yaml exists.
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_domain.py

def test_account_creation():
    account = Account(
        id='checking',
        name='Chase Checking',
        kind=AccountKind.CASH,
        currency='USD'
    )
    assert account.id == 'checking'
    assert account.kind == AccountKind.CASH

def test_snapshot_latest():
    snapshots = [
        Snapshot(account='checking', date=date(2025, 1, 1), value=1000),
        Snapshot(account='checking', date=date(2025, 1, 8), value=1200),
    ]
    latest = get_latest_snapshot(snapshots, 'checking')
    assert latest.value == 1200

def test_multi_currency_accounts():
    accounts = [
        Account(id='usd-checking', currency='USD', ...),
        Account(id='eur-checking', currency='EUR', ...),
    ]
    assert len(set(a.currency for a in accounts)) == 2
```

### Integration Tests

```python
# tests/test_v1_integration.py

def test_full_v1_workflow(tmp_path):
    """Test complete workflow: load config, analyze, generate reports."""
    config_dir = setup_v1_test_config(tmp_path)

    config = load_config(config_dir)
    assert is_v1_enabled(config)

    # Transaction analysis
    transactions = load_all_transactions(config)
    stats = analyze_transactions(transactions)

    # v1 calculations
    networth = calculate_networth(config['accounts'], config['snapshots'])
    budget = calculate_budget(config['accounts'], config['snapshots'],
                              config['plans'], stats, config)

    # Report generation
    generate_reports(config, stats, networth, budget)

    # Verify outputs
    assert (tmp_path / 'output' / 'spending_summary.html').exists()
    assert (tmp_path / 'output' / 'networth_report.html').exists()
    assert (tmp_path / 'output' / 'budget_report.html').exists()
```

---

## Open Questions

1. **Snapshot workflow**: Should we provide a CLI command for quick snapshot entry?
   - `tally snapshot checking 5432.10`
   - Pro: Convenient for daily updates
   - Con: Adds complexity

2. **Report integration**: Should v1 reports be separate files or integrated into single dashboard?
   - Option A: Separate HTML files (networth.html, budget.html)
   - Option B: Single dashboard with tabs
   - **Recommendation**: Start with separate, add integration later

3. **Negative balances**: Should we allow negative snapshots (overdrafts)?
   - Option A: Yes, allow negatives (models reality)
   - Option B: Validation error on negative
   - **Recommendation**: Allow for flexibility

4. **Plan tracking**: Should plans store `last_executed` date?
   - Pro: Useful for reminders
   - Con: Adds state, requires updates
   - **Recommendation**: Defer to v2

---

## Future Considerations (Not v1)

These are documented for future versions but NOT part of v1:

1. **FX Conversion** - Currency conversion with exchange rates
2. **Balance Reconciliation** - Matching transactions to balance changes
3. **Performance Tracking** - Investment returns, ROI
4. **Transaction ↔ Plan Matching** - Detecting plan execution
5. **Brokerage Integration** - API connections
6. **Liabilities & Debt** - Loan tracking
7. **OCR** - Screenshot parsing
8. **Advanced Plan Types** - SAVE, WITHDRAW, irregular cadences
9. **Net Worth History Charts** - Historical visualization
10. **Budget Alerts** - Notifications for overspending

---

## Success Metrics

### Adoption Metrics
- % of users creating `accounts.yaml` after upgrade
- Number of v1 reports generated vs spending reports
- User feedback on complexity

### Feature Metrics
- Average number of accounts tracked per user
- Snapshot update frequency
- Plan usage rate

### Quality Metrics
- Test coverage > 90%
- Zero regressions in existing spending analysis
- Load time < 2s for typical datasets
- All existing tests continue to pass

---

## Appendix: Updated File Structure After v1

```
tally/
├── src/tally/
│   ├── analyzer.py           # Existing: transaction analysis + diff
│   ├── classification.py     # Existing: tag-based classification
│   ├── config_loader.py      # Modified: v1 file loading
│   ├── cli_utils.py          # Modified: v1 detection helpers
│   ├── colors.py             # Existing: terminal colors
│   ├── path_utils.py         # Existing: path resolution
│   ├── domain.py             # NEW: Account, Snapshot, Plan classes
│   ├── v1_loader.py          # NEW: v1-specific config loading
│   ├── networth.py           # NEW: Net worth calculation
│   ├── budget.py             # NEW: Budget calculation
│   ├── report.py             # Modified: v1 report generation
│   ├── templates.py          # Modified: v1 starter templates
│   ├── merchant_engine.py    # Existing: rule matching
│   ├── parsers.py            # Existing: CSV parsing
│   ├── cli.py                # Modified: v1 commands
│   ├── commands/
│   │   ├── run.py           # Modified: v1 integration
│   │   ├── networth.py      # NEW: tally networth
│   │   ├── budget.py        # NEW: tally budget
│   │   ├── v1_init.py       # NEW: tally v1 init
│   │   └── ...              # Existing commands
│   └── templates/
│       ├── spending_report.html  # Existing
│       ├── networth_report.html  # NEW
│       └── budget_report.html    # NEW
├── config/
│   ├── settings.yaml.example     # Modified: v1 settings
│   ├── accounts.yaml.example     # NEW
│   ├── snapshots.yaml.example    # NEW
│   ├── plans.yaml.example        # NEW
│   ├── merchants.rules.example   # Existing
│   └── views.rules.example       # Existing
├── tests/
│   ├── test_domain.py            # NEW
│   ├── test_v1_loader.py         # NEW
│   ├── test_networth.py          # NEW
│   ├── test_budget.py            # NEW
│   ├── test_v1_integration.py    # NEW
│   └── ...                       # Existing tests
├── docs/
│   ├── v1-guide.md               # NEW
│   ├── migration.md              # NEW
│   └── ...                       # Existing docs
├── README.md                     # Modified: v1 overview
├── CLAUDE.md                     # Modified: v1 dev notes
└── TALLY_V1_IMPLEMENTATION_PLAN.md  # This file
```

---

## Conclusion

This updated implementation plan transforms Tally from a **spending analysis tool** into a **comprehensive personal finance modeling system** while:

✅ **Leveraging recent architectural improvements:**
- Modular CLI structure (cli_utils, colors, path_utils)
- Flexible path resolution (glob/folder support)
- Report diff infrastructure
- Field transform system

✅ **Maintaining backward compatibility:**
- v1 features are opt-in
- Existing workflows unchanged
- All current tests continue to pass

✅ **Following established patterns:**
- YAML configuration files
- Command module structure
- Validation and migration helpers
- Currency formatting system

**Core v1 Philosophy:**
- Plans say what should happen
- Transactions say what did happen
- Snapshots say what is true now

**Next Steps:**
1. Review and approve this updated plan
2. Begin Phase 1: Core domain objects
3. Iterate with user feedback

---

**Document Version:** 2.0 (Updated)
**Last Updated:** 2026-01-08
**Based on:** main branch commit 120fa5c
**Status:** Draft - Ready for Review
