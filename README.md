# trend-trading

> Given a ticker, output the current trend stage using documented systems.

A Python toolkit that fetches market data, computes technical indicators, applies a documented trend-trading system's rules, and outputs where the instrument is in its trend cycle right now. Currently ships the Clenow CTA system (EMA 50/100 filter + Donchian 100/50 + ATR 20 sizing); more systems planned.

The trend systems encoded here come from the companion project **[research-to-backtest](https://github.com/lilechen/research-to-backtest)**, which extracts trading systems from books and papers into structured specs. This repo is the downstream: it **runs** those specs against live data.

## Features

- **Live data**: A-shares via [akshare](https://akshare.akfamily.xyz/); US / HK / global via [yfinance](https://pypi.org/project/yfinance/)
- **Local parquet cache** to avoid hammering free APIs
- **Stage analysis** (Clenow Stage 2 / 3 / 1 detection) with key indicators, levels, sizing
- **4 risk levels** (7.5 / 10 / 15 / 30 bp) matching Clenow Table 4.5
- **JSON output** for programmatic use
- **Unit tests** with synthetic data (no network needed)

## Quick start

### Install

```bash
git clone https://github.com/lilechen/trend-trading.git
cd trend-trading
pip install -e ".[dev]"
```

Or just install deps:

```bash
pip install pandas numpy akshare yfinance pyarrow typer
```

### Use

```bash
# Analyze a Chinese A-share
python -m trend_trading analyze 600519

# Analyze a US ticker
python -m trend_trading analyze AAPL --years 5

# Customize risk level and account equity
python -m trend_trading analyze 000001 --risk-bp 10 --equity 500000

# JSON output for programmatic use
python -m trend_trading analyze 600519 --json
```

### Example output

```
============================================================
  600519  —  clenow 阶段分析
============================================================
数据截止: 2026-07-10
当前价:   1204.98

[阶段判定]
  阶段:    Stage 2(下降趋势,可做空)
  Regime:  trend_down
  Signal:  exit_long
  建议持仓: short

[关键指标]
  EMA50                       1251.9482
  EMA100                      1300.2888
  EMA50 4周斜率                     -4.93%
  Donchian High (100d)        1526.9800
  Donchian Low (100d)         1168.6300
  Donchian High (50d)         1376.9800
  Donchian Low (50d)          1168.6300
  ATR20                         28.7164
  距 100d 高                      -21.09%
  距 50d 低                        +3.11%

[仓位建议(risk factor 4 档)]
  7.5bp                             2 手
  10bp                              3 手
  15bp (core)                       5 手
  30bp (aggressive)                10 手

[关键价位]
  long_entry_trigger            1526.98
  short_entry_trigger           1168.63
  long_exit_trigger             1168.63
  short_exit_trigger            1376.98

[注意]
  - EMA50 4 周斜率 < -2%,上升趋势走弱,警惕
```

## Available systems

| System | Source | Style |
|---|---|---|
| `clenow` (default) | Andreas F. Clenow《Following the Trend》Ch.4 | EMA 50/100 filter + Donchian 100 entry / 50 exit + ATR 20 sizing |
| _(more planned)_ | — | — |

List with `python -m trend_trading systems`.

## How it works

```
code (CLI arg)
  ↓
data/fetcher.py          ← akshare / yfinance, with parquet cache
  ↓
data/cache.py            ← data/cache/<code>.parquet, 12h TTL
  ↓
indicators/{ma, atr, donchian, slope}.py
  ↓
systems/<name>.py        ← applies rules, returns AnalysisResult
  ↓
analysis/stage.py        ← formats as human-readable report
  ↓
CLI output
```

Each `systems/<name>.py` is a `TrendSystem` subclass that implements `analyze(df) → AnalysisResult`. Adding a new system = implementing that one method.

## Repository layout

```
trend-trading/
├── trend_trading/                # Python package
│   ├── data/
│   │   ├── fetcher.py            # akshare / yfinance wrapper
│   │   └── cache.py              # parquet cache
│   ├── indicators/
│   │   ├── ma.py                 # SMA / EMA / EMA slope
│   │   ├── atr.py                # ATR with EMA / SMA smoothing
│   │   ├── donchian.py           # Donchian 100 / 50 + three-weeks-tight
│   │   └── slope.py              # simple / normalized slope
│   ├── systems/
│   │   ├── base.py               # TrendSystem ABC + AnalysisResult
│   │   └── clenow.py             # Clenow Ch.4 implementation
│   └── analysis/
│       └── stage.py              # analyze() + format_report()
├── tests/                        # unit tests (no network)
├── data/cache/                   # gitignored, parquet cache
├── pyproject.toml
├── README.md
└── LICENSE
```

## Run tests

```bash
pytest tests/                       # or: python -m pytest tests/
```

Tests use synthetic OHLCV data — **no internet required** to run them.

## Data sources & rate limits

- **akshare** (A-shares): free, no API key. Risk of rate limiting on heavy use. Local cache (12h TTL by default) mitigates this.
- **yfinance** (US / HK / global): free, no API key. yfinance is known to rate-limit aggressively. If you hit `Too Many Requests`, wait a few minutes or use `--no-cache` to force a refresh.
- **Both**: not for commercial / real-money trading. For personal research only.

## Roadmap

- [ ] **Weinstein stage system** (30-week MA + 4 stages)
- [ ] **O'Neil CAN SLIM** (7-factor screen + base patterns)
- [ ] **Streamlit web UI** with chart visualization
- [ ] **Watchlist mode**: scan N tickers at once and rank
- [ ] **Real-time refresh** during market hours
- [ ] **Backtest mode**: apply system to historical data and report metrics (sharpe / max DD / win rate)
- [ ] **Signal subscription** (email / push notification when regime flips)

## Related projects

- **[research-to-backtest](https://github.com/lilechen/research-to-backtest)**: extract trading systems from PDFs (sister project). The Clenow spec encoded in this repo was extracted there.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is for **personal research and education only**. It is not financial advice, not a trading recommendation, and not a production trading system. The trend systems encoded here are simplified operationalizations of book methods, and any analysis output is "back-of-envelope" by design. Do not trade based on this output without independent verification, risk management, and a proper backtest.
