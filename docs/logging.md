# Logging

TELECOM-NET-SIM uses the standard `logging` module via a thin wrapper
in `telecom_logging.py`. No custom framework, no external dependencies.

## Quick start

```python
from telecom_logging import setup_logging, get_logger

setup_logging(level="INFO")
logger = get_logger(__name__)
logger.info("hello")
```

## CLI options

The simulator (`telecom_net_sim.py`) exposes three flags:

| Flag | Effect |
|---|---|
| `--verbose`, `-v` | Enable DEBUG-level logging |
| `--quiet`, `-q` | Only show WARNING and above |
| `--log-file PATH` | Also write logs to `PATH` (UTF-8) |

### Examples

```bash
python telecom_net_sim.py
python telecom_net_sim.py --verbose
python telecom_net_sim.py --quiet
python telecom_net_sim.py --verbose --log-file logs/run.log
python telecom_net_sim.py --subs 100 --cdrs 500 --verbose
```

## Log format

```
HH:MM:SS | LEVEL   | module                | message
```

Example:

```
10:51:00 | INFO    | telecom_net_sim       | [1/7] Building network topology...
10:51:00 | INFO    | telecom_net_sim       |       Cells: 294 | Core nodes: 119
10:51:00 | INFO    | telecom_attack        | Generating 25 scenarios...
10:51:00 | WARNING | telecom_attack        | Attack simulation skipped
```

- **Timestamp**: HH:MM:SS (local time).
- **Level**: DEBUG / INFO / WARNING / ERROR / CRITICAL.
- **Module**: the logger name (usually `__name__`).
- **Message**: free-form.

## Why not just print

- **Levels**: filter at runtime (`--quiet` in CI, `--verbose` when debugging).
- **Routing**: stdout, stderr, a file, or all three.
- **Testability**: `caplog` fixture lets you assert log messages in tests.
- **Metadata**: timestamp, level, and module name come for free.

## Custom usage

```python
from telecom_logging import setup_logging, get_logger, silence

setup_logging(level="DEBUG", log_file="logs/app.log")

logger = get_logger(__name__)
logger.debug("detailed trace")
logger.info("normal progress")
logger.warning("recoverable issue")
logger.error("hard failure")

silence("streamlit", level=30)
```

## Testing

```python
import logging
from telecom_logging import setup_logging, get_logger

def test_logs_message(caplog):
    setup_logging(level="INFO")
    logger = get_logger("my.module")
    with caplog.at_level(logging.INFO):
        logger.info("hello")
    assert "hello" in caplog.text
```

The full suite lives in `tests/test_logging.py`.

## Design notes

- **Idempotent**: calling `setup_logging()` twice does not duplicate handlers.
- **UTF-8 safe**: file handler uses `encoding="utf-8"`.
- **No global state pollution**: previous handlers are removed first.
- **Report output is not logging**: the final `report.txt` is still produced by `build_report()` using `print()`.

## API reference

::: telecom_logging.setup_logging

::: telecom_logging.get_logger

::: telecom_logging.silence
