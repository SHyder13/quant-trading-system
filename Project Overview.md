Project Overview.md

# Institutional Quant Trading System - File Breakdown

## Configuration Layer (`config/`)
*The brain's settings - what the system should remember*

### `strategy_config.py`
**Purpose**: Stores all strategy-specific parameters that quants tweak constantly
```python
# Examples of what goes here:
BREAK_CONFIRMATION_CANDLES = 2
RETEST_TIMEOUT_MINUTES = 30
MIN_VOLUME_THRESHOLD = 10000
LEVEL_TOLERANCE_POINTS = 0.02
```
**Why Separate**: Quants A/B test different parameters constantly. Having them in one file means you can swap entire parameter sets without touching code.

### `risk_config.py`
**Purpose**: Risk parameters that compliance/risk managers control
```python
# Examples:
MAX_POSITION_SIZE = 100000
MAX_DAILY_LOSS = -5000
MAX_LEVERAGE = 3.0
POSITION_CONCENTRATION_LIMIT = 0.05
```
**Why Separate**: Risk parameters are often controlled by risk management teams, not the strategy developers. They need to change these without touching strategy code.

### `market_config.py`
**Purpose**: Market structure definitions that rarely change
```python
# Examples:
TRADING_SESSIONS = {
    'premarket': {'start': '04:00', 'end': '09:29'},
    'regular': {'start': '09:30', 'end': '16:00'}
}
MARKET_HOLIDAYS = ['2024-12-25', '2024-01-01']
```
**Why Separate**: Market rules are facts, not strategy decisions. Clean separation prevents accidental changes.

---

## Data Layer (`data/`)
*The system's senses - how it perceives the market*

### `market_data_fetcher.py`
**Purpose**: The single source of truth for getting market data
- Handles connections to multiple data providers (Bloomberg, Refinitiv, broker APIs)
- Manages reconnections when feeds go down
- Standardizes data formats from different sources
**Significance**: In institutional settings, data feeds cost $10K+/month and are mission-critical. This file ensures bulletproof data acquisition.

### `data_processor.py`
**Purpose**: Cleans and validates raw market data
- Removes bad ticks (prices that are clearly wrong)
- Handles corporate actions (stock splits, dividends)
- Fills data gaps during market closures
**Significance**: Dirty data kills strategies. One bad tick can trigger false signals and lose thousands.

### `level_calculator.py`
**Purpose**: Your strategy's core math - calculates PDH, PDL, PMH, PML
- Handles complex cases (Friday→Monday, holidays, half-days)
- Recalculates levels when market sessions change
- Validates level accuracy against historical data
**Significance**: This is your strategy's foundation. If levels are wrong, everything else fails.

### `session_manager.py`
**Purpose**: Knows what time it is in market terms
- Tracks current trading session (premarket, regular, after-hours)
- Handles timezone conversions (your server might be in different timezone)
- Manages daylight savings transitions
**Significance**: Trading outside intended sessions can be catastrophic. This prevents "oops, I traded at 3 AM" disasters.

---

## Strategy Layer (`strategy/`)
*The system's decision-making brain*

### `level_detector.py`
**Purpose**: Identifies and tracks your key levels in real-time
- Maintains current PDH, PDL, PMH, PML values
- Updates levels when sessions change
- Validates level integrity (are they reasonable?)
**Significance**: The watchtower of your strategy - always knows where important prices are.

### `break_detector.py`
**Purpose**: Identifies when price breaks through your key levels
- Detects clean breaks vs. false breakouts
- Considers volume confirmation
- Tracks break strength and momentum
**Significance**: The trigger mechanism - decides when something interesting is happening.

### `retest_detector.py`
**Purpose**: Identifies when price returns to test a broken level
- Monitors for pullbacks after breaks
- Validates retest quality (clean bounce vs. messy chop)
- Times out stale setups
**Significance**: The confirmation mechanism - separates real opportunities from noise.

### `signal_generator.py`
**Purpose**: Combines break + retest detection into actionable signals
- Generates BUY/SELL signals when conditions align
- Adds signal confidence scores
- Manages signal timing and expiration
**Significance**: The decision maker - converts analysis into action.

### `pattern_validator.py`
**Purpose**: Quality control for trading signals
- Checks if market conditions support the strategy
- Validates signal strength against historical performance
- Filters out low-probability setups
**Significance**: The quality gate - prevents trading in unfavorable conditions.

---

## Risk Layer (`risk/`)
*The system's survival instinct*

### `position_sizer.py`
**Purpose**: Calculates how much to trade on each signal
- Uses Kelly Criterion, fixed fractional, or other sizing methods
- Considers current portfolio exposure
- Adjusts size based on market volatility
**Significance**: Determines if you make money or go broke. Even great signals fail with poor sizing.

### `stop_loss_manager.py`
**Purpose**: Manages stop losses dynamically
- Sets initial stops based on technical levels
- Trails stops as positions move favorably
- Handles different stop types (market, limit, trailing)
**Significance**: Your insurance policy - limits damage when trades go wrong.

### `take_profit_manager.py`
**Purpose**: Manages profit-taking strategies
- Sets profit targets based on risk/reward ratios
- Scales out of positions partially
- Adjusts targets based on momentum
**Significance**: Ensures you actually capture profits instead of watching winners turn into losers.

### `risk_calculator.py`
**Purpose**: Real-time risk monitoring across all positions
- Calculates portfolio-level risk metrics
- Monitors correlation between positions
- Alerts when risk limits are approached
**Significance**: The portfolio doctor - ensures you don't accidentally concentrate too much risk.

---

## Execution Layer (`execution/`)
*The system's hands - how it interacts with markets*

### `order_manager.py`
**Purpose**: Manages the lifecycle of every order
- Tracks order states (pending, filled, cancelled)
- Handles partial fills and order modifications
- Manages order timing and urgency
**Significance**: The traffic controller - ensures orders execute as intended.

### `broker_interface.py`
**Purpose**: Communicates with your broker's API
- Handles different broker protocols (FIX, REST, WebSocket)
- Manages authentication and reconnections
- Standardizes responses from different brokers
**Significance**: The translator - converts your intentions into broker-specific commands.

### `execution_tracker.py`
**Purpose**: Monitors execution quality
- Tracks slippage (difference between expected and actual fill prices)
- Measures execution latency
- Identifies execution problems
**Significance**: The performance auditor - ensures you're getting fair executions.

### `portfolio_manager.py`
**Purpose**: Maintains real-time view of all positions
- Tracks P&L for each position and overall portfolio
- Manages position reconciliation with broker
- Calculates portfolio-level metrics
**Significance**: The accounting department - knows exactly what you own and what it's worth.

---

## Monitoring Layer (`monitoring/`)
*The system's nervous system - awareness and alerting*

### `logger.py`
**Purpose**: Structured logging system for everything
- Logs all decisions, executions, and errors
- Creates audit trails for compliance
- Enables post-mortem analysis of problems
**Significance**: The black box recorder - helps debug issues and prove compliance.

### `performance_tracker.py`
**Purpose**: Real-time strategy performance analysis
- Calculates Sharpe ratio, max drawdown, win rate
- Tracks performance attribution by setup type
- Compares against benchmarks
**Significance**: The report card - tells you if your strategy is actually working.

### `alert_system.py`
**Purpose**: Notifications when important events occur
- Sends alerts for large losses, system errors, or unusual market conditions
- Integrates with email, SMS, Slack, etc.
- Manages alert priorities and escalation
**Significance**: The early warning system - gets your attention when things need it.

### `dashboard.py`
**Purpose**: Real-time visual monitoring interface
- Shows live P&L, positions, and market conditions
- Displays strategy performance metrics
- Provides manual override controls
**Significance**: The cockpit - gives you situational awareness and control.

---

## Testing Framework (`tests/`)
*The system's training ground*

### `unit/`
**Purpose**: Tests individual components in isolation
- Tests level calculation accuracy
- Tests signal generation logic
- Tests risk calculations
**Significance**: Catches bugs before they cost money.

### `integration/`
**Purpose**: Tests how components work together
- Tests full data pipeline
- Tests strategy + risk + execution workflow
- Tests broker connectivity
**Significance**: Ensures the whole system works, not just individual parts.

### `backtesting/`
**Purpose**: Tests strategy on historical data
- Simulates trading over past market conditions
- Measures historical performance
- Validates strategy assumptions
**Significance**: Proves your strategy worked historically before risking real money.

---

## How It All Connects

**Data Flow**: `market_data_fetcher` → `data_processor` → `level_calculator` → `level_detector` → `break_detector` → `retest_detector` → `signal_generator` → `position_sizer` → `order_manager` → `broker_interface`

**Risk Flow**: Every component checks with `risk_calculator` before taking action

**Monitoring Flow**: Every component reports to `logger` and `performance_tracker`

**Configuration Flow**: All components read their settings from the appropriate config file

This structure allows institutional quants to:
- **Scale**: Add new strategies without breaking existing ones
- **Maintain**: Fix bugs in one component without affecting others  
- **Collaborate**: Different team members work on different components
- **Audit**: Track every decision and execution for compliance
- **Optimize**: A/B test different parameters and components independently

The complexity pays off when you're managing millions of dollars and can't afford system failures or compliance issues.