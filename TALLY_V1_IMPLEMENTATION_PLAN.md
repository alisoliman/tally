# Tally v1 Implementation Plan
## Personal Finance Modeling System

**Status:** Planning Phase
**Date:** 2026-01-08
**Author:** Implementation Plan for expanding Tally from transaction analysis to full personal finance modeling

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [New Domain Model](#new-domain-model)
4. [Storage Architecture](#storage-architecture)
5. [Configuration Design](#configuration-design)
6. [Multi-Currency Support](#multi-currency-support)
7. [Budgeting Engine](#budgeting-engine)
8. [Reporting System](#reporting-system)
9. [Migration Strategy](#migration-strategy)
10. [Implementation Phases](#implementation-phases)
11. [Testing Strategy](#testing-strategy)
12. [Future Considerations](#future-considerations)

---

## Executive Summary

### Current State
Tally is a **transaction categorization and spending analysis tool** that:
- Parses CSV transaction exports from banks
- Categorizes transactions using rule-based merchant matching
- Generates HTML/JSON reports with spending summaries
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

## Current Architecture Analysis

### File Structure
```
tally/
├── src/tally/
│   ├── analyzer.py           # Core transaction analysis
│   ├── classification.py     # Transaction categorization logic
│   ├── config_loader.py      # Settings and data source loading
│   ├── merchant_engine.py    # Rule matching engine
│   ├── merchant_utils.py     # Merchant normalization
│   ├── parsers.py           # CSV parsing
│   ├── report.py            # HTML report generation
│   ├── section_engine.py    # View grouping logic
│   ├── cli.py               # Command-line interface
│   └── commands/            # CLI subcommands
├── config/                   # Example configurations
├── data/                     # User transaction CSVs
└── output/                   # Generated reports
```

### Key Data Structures

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
    'location': Optional[str],
    'extra_fields': Dict      # Custom captures from format string
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
    'transfers_out': float
}
```

### Current Strengths
1. **Flexible CSV Parsing** - Format string system handles diverse bank exports
2. **Powerful Rule Engine** - Expression-based merchant matching with regex, amounts, dates
3. **Tag System** - Special tags (`income`, `transfer`, `investment`) control classification
4. **Views/Sections** - Group merchants into custom spending categories
5. **Multiple Output Formats** - HTML, JSON, Markdown
6. **Backward Compatibility** - Migration helpers for config format changes

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

**Future Plan Types (not v1):**
- `SAVE` - Recurring transfers to savings
- `WITHDRAW` - Planned withdrawals

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
    location: Optional[str]
    extra_fields: Dict
```

**v1 Behavior:**
- Transactions don't define balances (snapshots do)
- `account_id` is optional in v1 (backward compatible)
- Used for income/expense reporting and budgeting
- No balance reconciliation

**Direction Classification:**
- `INCOME` - Salary, interest, deposits
- `EXPENSE` - Purchases, bills, transfers out

---

## Storage Architecture

### Design Philosophy
**File-based, version-controllable, AI-friendly**

### Current Storage (Transactions)
- CSV files in `data/` directory
- Parsed on-demand from `settings.yaml` data sources
- No persistence of analysis results

### New Storage Layers

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
    attachment: screenshots/savings-jan-8.png  # Optional screenshot reference

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

**Design Decisions:**
- YAML format (human-readable, version-controllable)
- Sorted by date for easy reading
- Optional `note` and `attachment` fields
- No validation against transactions (snapshots are truth)

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

  # Bi-weekly IRA contribution
  - id: ira-biweekly
    type: invest
    from: checking
    to: ira
    amount: 250.00
    currency: USD
    cadence: biweekly       # Future: not v1
    start_date: 2025-01-15
    status: paused          # Temporarily paused
```

**v1 Limitations:**
- Only `monthly` cadence supported
- Only `invest` type supported
- Only `active` and `paused` statuses

#### 5. Data Loading Architecture

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

        # NEW for v1
        'accounts': load_accounts(config_dir),
        'snapshots': load_snapshots(config_dir),
        'plans': load_plans(config_dir),
        'primary_currency': load_primary_currency(config_dir),
    }
    return config

def load_accounts(config_dir) -> List[Account]:
    """Load accounts from accounts.yaml."""
    # Parse YAML, validate structure, return Account objects

def load_snapshots(config_dir) -> List[Snapshot]:
    """Load snapshots from snapshots.yaml."""
    # Parse YAML, validate dates and amounts, return Snapshot objects

def load_plans(config_dir) -> List[Plan]:
    """Load plans from plans.yaml."""
    # Parse YAML, validate account references, return Plan objects
```

### Storage Benefits
1. **Human-Editable** - YAML is readable and easy to edit manually
2. **Version Control Friendly** - Git tracks changes to balances and plans
3. **AI Assistant Friendly** - LLMs can read/write YAML easily
4. **No Database Setup** - Works immediately, no migrations
5. **Privacy** - All data stays local (can be git-ignored)

---

## Configuration Design

### settings.yaml Extensions

```yaml
# Existing settings (keep all)
year: 2025
title: "Spending Analysis"
data_sources: [...]
output_dir: output
merchants_file: config/merchants.rules
views_file: config/views.rules

# NEW v1 settings
primary_currency: EUR          # Default currency for UI/reports
accounts_file: config/accounts.yaml
snapshots_file: config/snapshots.yaml
plans_file: config/plans.yaml

# Currency display (existing, enhanced)
currency_format: "€{amount}"   # Primary currency format

# NEW: Currency-specific formats (optional)
currency_formats:
  USD: "${amount}"
  EUR: "€{amount}"
  GBP: "£{amount}"
  PLN: "{amount} zł"
```

### Backward Compatibility

**Principles:**
1. v1 features are **additive** - existing configs work unchanged
2. If `accounts.yaml` doesn't exist, v1 features are disabled
3. Transaction analysis works independently of account tracking
4. Users can adopt v1 features incrementally

**Migration Path:**
```python
def is_v1_enabled(config):
    """Check if user has opted into v1 features."""
    accounts_file = config.get('accounts_file')
    if not accounts_file:
        return False
    accounts_path = resolve_path(config['_config_dir'], accounts_file)
    return os.path.exists(accounts_path)

# In analyzer.py
def analyze_and_report(config):
    # Existing transaction analysis (always runs)
    transaction_stats = analyze_transactions(transactions)

    # v1 features (only if enabled)
    if is_v1_enabled(config):
        accounts = config['accounts']
        snapshots = config['snapshots']
        plans = config['plans']

        networth_stats = calculate_networth(accounts, snapshots)
        budget_stats = calculate_budget(accounts, snapshots, plans, transaction_stats)

        # Generate new reports
        generate_networth_report(networth_stats)
        generate_budget_report(budget_stats)
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

### UI Display

```
Cash Position
─────────────
USD:
  Chase Checking         $4,821.45
  Ally Savings          $10,500.00
                        ──────────
  Total                 $15,321.45

EUR:
  N26 Checking           €2,500.00
                        ──────────
  Total                  €2,500.00
```

### Future Considerations (not v1)
- FX conversion with user-provided rates
- Historical FX rate tracking
- Consolidated totals in primary currency

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
def calculate_budget(accounts, snapshots, plans, transaction_stats):
    """
    Calculate monthly budget projections.

    Returns budget breakdown per currency.
    """
    # Get latest cash balances
    cash_by_currency = {}
    for account in accounts:
        if account.kind != AccountKind.CASH:
            continue
        latest_snapshot = get_latest_snapshot(snapshots, account.id)
        if latest_snapshot:
            if account.currency not in cash_by_currency:
                cash_by_currency[account.currency] = 0
            cash_by_currency[account.currency] += latest_snapshot.value

    # Get active investment plans
    active_plans = [p for p in plans if p.status == PlanStatus.ACTIVE]

    # Group plans by currency
    investments_by_currency = {}
    for plan in active_plans:
        if plan.currency not in investments_by_currency:
            investments_by_currency[plan.currency] = 0

        # Monthly investment amount
        if plan.cadence == Cadence.MONTHLY:
            investments_by_currency[plan.currency] += plan.amount

    # Get income and spending from transactions
    # (transaction_stats already computed from analyze_transactions)
    income_total = transaction_stats.get('income_total', 0)
    spending_total = transaction_stats.get('spending_total', 0)

    # NOTE: v1 assumes single currency for transactions
    # Multi-currency transaction support is future work
    primary_currency = config.get('primary_currency', 'EUR')

    return {
        primary_currency: {
            'income_monthly': income_total / 12,  # Assuming YTD data
            'expenses_monthly': spending_total / 12,
            'investments_monthly': investments_by_currency.get(primary_currency, 0),
            'cash_available': cash_by_currency.get(primary_currency, 0),
            'net_monthly': (income_total / 12) - (spending_total / 12) - investments_by_currency.get(primary_currency, 0)
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

### Design Decisions

1. **Only cash accounts count as "available"**
   - Investment accounts excluded from spendable money

2. **Plans reduce available cash**
   - Investment plans are "committed" money

3. **No transaction matching to plans**
   - Plans say what *should* happen
   - Transactions say what *did* happen
   - These can differ without error

4. **v1 monthly averages**
   - Income and expenses calculated as YTD / 12
   - Future: rolling averages, projections

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

#### 2. Budget Projection Report

**File:** `output/budget_report.html`

**Sections:**
1. **Monthly Budget** - Income, expenses, investments, net
2. **Active Plans** - Investment commitments
3. **Cash Flow Forecast** - Next 3 months projection

**Mockup:**
```
═══════════════════════════════════════════
BUDGET PROJECTION
January 2025
═══════════════════════════════════════════

MONTHLY CASH FLOW
─────────────────────────────────────────
Income                 +$4,500/mo
Expenses               -$3,200/mo
Investments            -$500/mo
─────────────────────────────────────────
Net Cash Flow          +$800/mo

ACTIVE INVESTMENT PLANS
─────────────────────────────────────────
401(k) Monthly         $500/mo → 401(k)
─────────────────────────────────────────
Total Investments      $500/mo

CASH RUNWAY
─────────────────────────────────────────
Available Cash         $15,321
Monthly Burn           -$3,200
Runway                 4.8 months
```

#### 3. Enhanced Spending Report (existing)

**Keep existing spending report, add v1 context:**
- Show which accounts transactions came from (if linked)
- Display budget projections alongside spending
- Link to net worth dashboard

### Report Generation

```python
# report.py (existing module, will be extended)

def generate_reports(config, stats, accounts, snapshots, plans):
    """Generate all reports based on config and analysis."""

    # Existing spending report (always generated)
    generate_spending_report(config, stats)

    # v1 reports (only if v1 enabled)
    if is_v1_enabled(config):
        networth_stats = calculate_networth(accounts, snapshots)
        budget_stats = calculate_budget(accounts, snapshots, plans, stats)

        generate_networth_report(config, networth_stats)
        generate_budget_report(config, budget_stats)
```

---

## Migration Strategy

### Backward Compatibility

**Goal:** Existing Tally users can upgrade without breaking changes.

#### Phase 1: Non-Breaking Addition
- v1 code added to codebase
- v1 features disabled by default
- Existing `tally up` command works unchanged
- Tests ensure existing behavior preserved

#### Phase 2: Opt-In v1
- Users manually create `accounts.yaml`, `snapshots.yaml`, `plans.yaml`
- v1 features auto-enable when these files exist
- Documentation shows migration examples
- `tally init` templates include v1 files (commented out)

#### Phase 3: v1 as Default (future)
- New `tally init` creates v1 files by default
- Existing users unaffected (no v1 files = v1 disabled)
- Legacy mode for pure transaction analysis

### Migration Helpers

```python
# cli.py - new command

def cmd_v1_init(args):
    """Initialize v1 files for existing Tally users."""
    config_dir = find_config_dir()

    # Create starter files
    create_starter_file(config_dir, 'accounts.yaml', STARTER_ACCOUNTS)
    create_starter_file(config_dir, 'snapshots.yaml', STARTER_SNAPSHOTS)
    create_starter_file(config_dir, 'plans.yaml', STARTER_PLANS)

    # Update settings.yaml
    update_settings_for_v1(config_dir)

    print("✓ v1 files created!")
    print("  Edit config/accounts.yaml to define your accounts")
    print("  Add snapshots to config/snapshots.yaml")
    print("  Define investment plans in config/plans.yaml")
```

### Data Migration

**No automatic migration** - v1 introduces new concepts that can't be inferred from transactions.

Users must manually:
1. Define their accounts in `accounts.yaml`
2. Record initial snapshots in `snapshots.yaml`
3. Define investment plans in `plans.yaml` (optional)

**Migration Guide (documentation):**
```markdown
# Migrating to Tally v1

Tally v1 adds account tracking, snapshots, and financial planning.

## Step 1: Define Your Accounts

Create `config/accounts.yaml`:

```yaml
accounts:
  - id: checking
    name: My Checking Account
    kind: cash
    currency: USD
```

## Step 2: Record Your Current Balances

Create `config/snapshots.yaml`:

```yaml
snapshots:
  - account: checking
    date: 2025-01-08
    value: 5432.10
    note: "Current balance from bank app"
```

## Step 3: (Optional) Define Investment Plans

Create `config/plans.yaml`:

```yaml
plans:
  - id: 401k
    type: invest
    from: checking
    to: retirement
    amount: 500
    currency: USD
    cadence: monthly
    start_date: 2025-01-01
    status: active
```

## Step 4: Link Transactions to Accounts (Optional)

In your data sources, you can now specify which account:

```yaml
data_sources:
  - name: Checking Transactions
    file: data/checking-2025.csv
    format: "{date:%m/%d/%Y},{description},{amount}"
    account: checking  # NEW: Link to account
```

This is optional - transactions work without account links.
```

---

## Implementation Phases

### Phase 0: Planning & Architecture (Current)
**Duration:** 1 week
**Deliverables:**
- [ ] Implementation plan document (this file)
- [ ] Architecture diagrams
- [ ] Data model specification
- [ ] Configuration format examples

### Phase 1: Core Domain Objects
**Duration:** 2 weeks
**Deliverables:**
- [ ] `Account`, `Snapshot`, `Plan` classes (src/tally/domain.py)
- [ ] YAML loading for accounts/snapshots/plans (extend config_loader.py)
- [ ] Validation logic (ensure currency matching, date ordering)
- [ ] Unit tests for domain objects

**Files to Create:**
- `src/tally/domain.py` - Domain object classes
- `src/tally/v1_loader.py` - v1 config loading
- `tests/test_domain.py` - Domain object tests
- `tests/test_v1_loader.py` - Config loading tests

**Files to Modify:**
- `src/tally/config_loader.py` - Add v1 file loading

### Phase 2: Storage & Configuration
**Duration:** 1 week
**Deliverables:**
- [ ] accounts.yaml schema and parser
- [ ] snapshots.yaml schema and parser
- [ ] plans.yaml schema and parser
- [ ] settings.yaml extensions (primary_currency, v1 file refs)
- [ ] Starter templates for v1 files

**Files to Create:**
- `config/accounts.yaml.example`
- `config/snapshots.yaml.example`
- `config/plans.yaml.example`

**Files to Modify:**
- `src/tally/cli.py` - Add v1 starter templates (STARTER_ACCOUNTS, etc.)
- `config/settings.yaml.example` - Add v1 settings

### Phase 3: Multi-Currency Support
**Duration:** 1 week
**Deliverables:**
- [ ] Currency grouping logic
- [ ] Per-currency totals
- [ ] Currency formatting helpers
- [ ] Tests for multi-currency scenarios

**Files to Modify:**
- `src/tally/report.py` - Add currency grouping
- `src/tally/analyzer.py` - Currency-aware aggregations

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

### Phase 6: Reporting (Net Worth)
**Duration:** 2 weeks
**Deliverables:**
- [ ] Net worth HTML report template
- [ ] Account list view
- [ ] Currency-grouped displays
- [ ] Interactive Vue.js components (if needed)
- [ ] Tests with Playwright MCP

**Files to Create:**
- `src/tally/templates/networth_report.html`
- `src/tally/templates/networth_report.css`
- `src/tally/templates/networth_report.js`

**Files to Modify:**
- `src/tally/report.py` - Add generate_networth_report()

### Phase 7: Reporting (Budget)
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
- `src/tally/report.py` - Add generate_budget_report()

### Phase 8: CLI Integration
**Duration:** 1 week
**Deliverables:**
- [ ] New CLI commands (tally networth, tally budget)
- [ ] v1 init command (tally v1 init)
- [ ] Enhanced `tally up` with v1 reports
- [ ] CLI help updates

**Files to Modify:**
- `src/tally/cli.py` - Add v1 commands
- `src/tally/commands/` - New command modules

### Phase 9: Documentation & Migration
**Duration:** 1 week
**Deliverables:**
- [ ] User documentation for v1 features
- [ ] Migration guide for existing users
- [ ] Configuration examples
- [ ] Video tutorials (optional)
- [ ] Update CLAUDE.md with v1 guidance

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

def test_plan_validation():
    # Should fail: currency mismatch
    with pytest.raises(ValueError):
        Plan(
            id='test',
            type=PlanType.INVEST,
            from_account=Account(id='a', currency='USD', ...),
            to_account=Account(id='b', currency='EUR', ...),
            amount=100,
            currency='USD',
            ...
        )
```

### Integration Tests

```python
# tests/test_v1_integration.py

def test_full_workflow_with_v1(tmp_path):
    """Test complete workflow: load config, analyze, generate reports."""
    # Create test config directory
    config_dir = setup_test_config(tmp_path)

    # Load config
    config = load_config(config_dir)

    # Verify v1 enabled
    assert is_v1_enabled(config)
    assert len(config['accounts']) > 0

    # Load transactions
    transactions = load_all_transactions(config)

    # Analyze
    stats = analyze_transactions(transactions)
    networth = calculate_networth(config['accounts'], config['snapshots'])
    budget = calculate_budget(config['accounts'], config['snapshots'], config['plans'], stats)

    # Generate reports
    generate_reports(config, stats, networth, budget)

    # Verify outputs
    assert os.path.exists(tmp_path / 'output' / 'spending_summary.html')
    assert os.path.exists(tmp_path / 'output' / 'networth_report.html')
    assert os.path.exists(tmp_path / 'output' / 'budget_report.html')
```

### HTML Report Tests (Playwright MCP)

```python
# tests/test_v1_reports.py

@pytest.mark.playwright
def test_networth_report_rendering(playwright_page, test_config):
    """Use Playwright to verify net worth report renders correctly."""
    # Generate report
    config = load_config(test_config)
    generate_networth_report(config)

    # Load in browser
    report_path = config['output_dir'] / 'networth_report.html'
    playwright_page.goto(f'file://{report_path}')

    # Verify key elements
    assert playwright_page.locator('h1:has-text("Net Worth")').is_visible()
    assert playwright_page.locator('.cash-accounts').is_visible()
    assert playwright_page.locator('.investment-accounts').is_visible()

    # Verify currency formatting
    total = playwright_page.locator('.net-worth-total').inner_text()
    assert '$' in total or '€' in total  # Has currency symbol
```

---

## Future Considerations (Not v1)

### Features Explicitly Out of Scope

These are documented for future versions but NOT part of v1:

#### 1. FX Conversion
- Currency conversion with exchange rates
- Historical rate tracking
- Consolidated totals in primary currency

#### 2. Balance Reconciliation
- Automatic matching of transactions to balance changes
- Discrepancy detection
- Transaction-based balance calculation

#### 3. Performance & Returns
- Investment performance tracking
- ROI calculations
- Gain/loss reporting

#### 4. Transaction ↔ Plan Matching
- Detecting when plans are executed
- Plan vs actual analysis
- Automated plan status updates

#### 5. Brokerage Integration
- API connections to brokers
- Automatic position updates
- Dividend/interest tracking

#### 6. Liabilities & Debt
- Loan tracking
- Debt payoff planning
- Amortization schedules

#### 7. OCR & Screenshot Parsing
- Automatic balance extraction from screenshots
- Receipt OCR
- Statement PDF parsing

#### 8. Advanced Account Types
- Savings vs checking distinction
- Credit cards as liability accounts
- Loan accounts

#### 9. Advanced Plan Types
- `SAVE` - Recurring savings transfers
- `WITHDRAW` - Planned withdrawals
- `DEBT_PAYOFF` - Debt reduction plans
- Irregular cadences (weekly, quarterly, annual)

#### 10. Tax Planning
- Tax-advantaged account tracking
- Contribution limit warnings
- Tax-lot tracking

---

## Risk Analysis

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Backward compatibility breaks | Medium | High | Extensive tests, feature flags, gradual rollout |
| YAML parsing errors | Medium | Medium | Strict validation, helpful error messages |
| Multi-currency complexity | Low | High | Start simple (group by currency), defer FX |
| Performance with large datasets | Low | Medium | Lazy loading, pagination in reports |
| User confusion with new model | High | Medium | Clear documentation, migration guide, examples |

### User Experience Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Too many config files | Medium | Medium | Keep v1 optional, provide templates |
| Manual snapshot entry burden | High | Medium | Simple YAML format, screenshot support |
| Unclear separation: plans vs transactions | Medium | High | Documentation emphasizing mental model |
| Multi-currency intimidation | Low | Low | Single-currency users unaffected |

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

---

## Questions for Design Review

1. **Snapshot workflow:** Should we provide a CLI command to quickly add snapshots? (`tally snapshot checking 5432.10`)

2. **Transaction linking:** Should we support linking transactions to accounts in v1, or defer?
   - Pro: Better transaction categorization by account
   - Con: Adds complexity, not needed for snapshots-as-truth model

3. **Plan execution tracking:** Should plans store last_executed date even if we don't match?
   - Pro: Useful for reminders
   - Con: Adds state management

4. **Multi-currency transactions:** Should transactions have `source_currency` and `target_currency`?
   - Pro: Handles cross-currency transfers
   - Con: Significant complexity for v1

5. **Negative balances:** Should we allow negative snapshots (overdrafts, debts)?
   - Pro: Models reality
   - Con: Confuses "cash available" logic

6. **Investment contributions in transactions:** Should investment-tagged transactions automatically suggest plan creation?
   - Pro: Helps users discover plans feature
   - Con: May be presumptuous

---

## Open Questions

1. How should we handle accounts closed mid-year?
   - Option A: Final snapshot with value=0
   - Option B: Deleted status field on Account
   - **Decision:** TBD

2. Should snapshots support pending transactions?
   - Option A: No, snapshots are final settled balances
   - Option B: Add `pending_value` field
   - **Decision:** TBD

3. How do we show accounts with no recent snapshots?
   - Option A: Show last known balance with "stale" warning
   - Option B: Hide from current reports, show in archive
   - **Decision:** TBD

---

## Appendix: File Structure After v1

```
tally/
├── src/tally/
│   ├── analyzer.py           # Existing: transaction analysis
│   ├── classification.py     # Existing: tag-based classification
│   ├── config_loader.py      # Modified: v1 file loading
│   ├── domain.py             # NEW: Account, Snapshot, Plan classes
│   ├── v1_loader.py          # NEW: v1-specific config loading
│   ├── networth.py           # NEW: Net worth calculation
│   ├── budget.py             # NEW: Budget calculation
│   ├── report.py             # Modified: v1 report generation
│   ├── merchant_engine.py    # Existing: rule matching
│   ├── parsers.py            # Existing: CSV parsing
│   ├── cli.py                # Modified: v1 commands
│   ├── commands/
│   │   ├── run.py           # Existing: tally up
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

This implementation plan transforms Tally from a **spending analysis tool** into a **comprehensive personal finance modeling system** while maintaining backward compatibility and simplicity.

**Core v1 Philosophy:**
- Plans say what should happen
- Transactions say what did happen
- Snapshots say what is true now

This model eliminates reconciliation complexity while enabling powerful features:
- Net worth tracking across accounts and currencies
- Budget projections with investment planning
- Multi-currency portfolio support

**Implementation Approach:**
- Phased rollout over ~12 weeks
- Opt-in v1 features (backward compatible)
- File-based storage (YAML, human-editable)
- No external dependencies (databases, APIs)

**Next Steps:**
1. Review and refine this plan
2. Begin Phase 1: Core domain objects
3. Iterate with user feedback

---

**Document Version:** 1.0
**Last Updated:** 2026-01-08
**Status:** Draft - Awaiting Review
