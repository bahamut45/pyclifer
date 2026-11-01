# Rich Logging

pyclifer integrates Rich into the logging system while maintaining full compatibility with `click-extra` and
preserving the `SecretsMasker` filter and custom `TRACE` level.

## Overview

The Rich logging integration provides:

- **Colored output**: Beautiful, colored log messages with Rich formatting
- **Rich tracebacks**: Enhanced exception display with syntax highlighting
- **Security filtering**: Automatic masking of sensitive information
- **TRACE level**: Custom debug level (value 5) for detailed troubleshooting
- **File logging**: Time-based rotating log files with configurable verbosity
- **Click-extra compatibility**: Seamless integration with existing CLI infrastructure

## Architecture

The logging system lives in `src/pyclifer/core/log/`:

1. **`levels.py`** — Custom logging levels and utilities
    - `TRACE` level (value 5)
    - `PYCLIFER_LOG_LEVELS` extending click-extra's log levels
    - `add_trace_method()` for adding trace capability to loggers

2. **`handlers.py`** — Rich-enhanced stream handlers
    - `RichExtraStreamHandler`: click-extra compatible Rich handler
    - Automatic Rich tracebacks support
    - Built-in `SecretsMasker` integration

3. **`formatters.py`** — Enhanced log formatters
    - `RichExtraFormatter`: Rich markup support with TRACE level styling

4. **`filters.py`** — Log filtering utilities
    - `SecretsMasker`: Automatic masking of passwords, keys, tokens, etc.

5. **`config.py`** — Configuration utilities
    - `configure_rich_logging()`: Global logging configuration
    - `get_configured_logger()`: Factory for Rich-enabled loggers
    - `PycliferVerbosityOption`: Verbosity option with TRACE support
    - `setup_file_logging()`: Time-based rotating log files
    - `create_log_file_callback()`: Click callback for `--log-file`

`PYCLIFER_LOG_LEVELS` extends click-extra's standard levels with `TRACE`:

```python
from pyclifer import PYCLIFER_LOG_LEVELS
# {"TRACE": 5, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
```

For advanced handler setup — when wiring pyclifer logging into an existing logging config:

```python
from pyclifer import (
    RichExtraFormatter,
    RichExtraStreamHandler,
    add_trace_method,
    TRACE,
)
import logging

# Add .trace() method to any logger
logger = logging.getLogger("myapp")
add_trace_method(logger)
logger.trace("low-level trace message")  # level 5

# Build a handler manually
handler = RichExtraStreamHandler()
handler.setFormatter(RichExtraFormatter())
handler.setLevel(TRACE)
```

Most projects use `configure_rich_logging()` or `@app_group(use_rich_logging=True)` instead —
these primitives are for custom setups.

## Usage

### Automatic Rich Logging with `@app_group`

```python
from pyclifer import app_group


@app_group()  # Rich logging enabled by default
def cli():
    """My CLI with beautiful Rich logging."""
    pass


@app_group(
    use_rich_logging=True,
    enable_secrets_filter=True,
    add_log_file_option=True,
    log_file_default_level="TRACE",
)
def advanced_cli():
    """CLI with explicit Rich configuration."""
    pass


@app_group(
    enable_secrets_filter=True,
    sensitive_fields=["bearer_token", "api_secret_key"],
)
def secure_cli():
    """CLI that masks custom sensitive fields in addition to the defaults."""
    pass
```

### Logging from Code

```python
from pyclifer import logger, get_logger

# Use the pre-configured global logger
logger.info("Application starting...")
logger.trace("Checking internal state")

# Or create a named logger
app_logger = get_logger("my-app")
app_logger.warning("Something might be wrong")
```

### Command Line Usage

```bash
# Use TRACE level for detailed debugging
myapp --verbosity TRACE command

# Supported levels: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
myapp --verbosity DEBUG command

# Environment variable support
MYAPP_VERBOSITY=TRACE myapp command
```

The level goes both ways. The default is `WARNING` (change it with `verbosity_default_level`), and a
level you choose replaces it, whether it is more or less verbose:

```bash
myapp --verbosity DEBUG command    # warnings, plus info and debug messages
myapp --verbosity ERROR command    # only errors and critical messages
myapp command --verbosity ERROR    # the option is accepted after the subcommand too
```

If you give two levels on the same command line, the most verbose one wins.

### File Logging

```python
from pyclifer import app_group


@app_group(
    add_log_file_option=True,  # Adds --log-file option
    log_file_default_level="TRACE",  # Default file log level
    log_file_rotation_when="midnight",
    log_file_rotation_backup_count=7
)
def cli():
    pass
```

```bash
myapp --log-file /var/log/myapp.log command
MYAPP_LOG_FILE=/var/log/myapp.log myapp command
```

Console verbosity (`--verbosity`) and file log level are independent.

### Centralized Configuration

```python
from pyclifer import get_logger, configure_rich_logging

# Done automatically by @app_group — shown here for reference
configure_rich_logging(
    use_rich=True,
    rich_tracebacks=True,
    enable_secrets_filter=True,
    sensitive_fields=["bearer_token", "api_secret_key"],  # merged into defaults
)

logger = get_logger()  # Automatically Rich-enabled
```

## Features

### Custom Sensitive Fields

`SecretsMasker` ships with a built-in set of field names it always masks. Pass `sensitive_fields`
to extend this list — the defaults are never removed.

Default masked fields (`SecretsMasker.DEFAULT_FIELDS`):

```
access_token, api_key, apikey, authorization, keyfile_dict,
passphrase, passwd, password, private_key, pwd,
secret, service_account, token
```

```python
@app_group(
    sensitive_fields=["bearer_token", "api_secret_key"],
)
def cli():
    """bearer_token and api_secret_key are masked in addition to the defaults."""
    pass
```

`sensitive_fields` propagates to both the console handler and the file handler (if `--log-file`
is active). The complete default list is available as `SecretsMasker.DEFAULT_FIELDS`.

A field matches when its name contains one of the listed names, ignoring case: with `token` in the
list, `bearer_token` and `Token` are masked too. Set `enable_secrets_filter=False` to turn the
filter off.

!!! note "Masking works on keys, not on free text"
    The filter hides the **value of a key**, in a dict, a named tuple or a log record attribute:

    ```python
    log.warning("payload %s", {"password": "hunter2", "user": "bob"})
    # payload {'password': '*CENSORED*', 'user': 'bob'}
    ```

    A plain message such as `log.warning("password=hunter2")` is not scanned and is logged as is.
    Pass secrets as structured arguments to have them masked.

### Preserved Functionality

- **TRACE level**: Custom debug level (value 5)
- **SecretsMasker filter**: Automatic masking of sensitive data — extensible via `sensitive_fields`
- **Full compatibility**: Works with existing code without modifications

### Rich Capabilities

- **Colored output**: Automatic colorization of log levels and messages
- **Rich tracebacks**: Syntax-highlighted exception traces
- **Timestamp display**: Automatic `[MM/DD/YY HH:MM:SS]` formatting
- **File rotation**: Fine-grained control over log file rotation policies
- **Global logger**: Pre-instantiated `logger` available for immediate use

### Click-Extra Integration

- **Extended verbosity**: TRACE level in `--verbosity` option
- **Environment variables**: Full `<PREFIX>_VERBOSITY` support
- **Automatic configuration**: No manual setup required

## Examples

### Basic CLI with Rich Logging

```python
from pyclifer import app_group, logger


@app_group()
def cli():
    """CLI with automatic Rich logging."""
    pass


@cli.command()
def test():
    """Test command."""
    logger.trace("Detailed debug information")
    logger.info("Operation successful")
    logger.warning("Warning message")
    logger.error("Error occurred")
```

### Advanced Configuration

```python
from pyclifer import app_group


@app_group(
    use_rich_logging=True,
    enable_secrets_filter=True
)
def secure_cli():
    """CLI with Rich logging and secrets filtering."""
    pass


@app_group(use_rich_logging=False)
def simple_cli():
    """CLI with standard logging."""
    pass
```

With `use_rich_logging=False` the console uses click-extra's standard handler: one line per record,
written as `level: message` (lowercase level, no timestamp).

```text
warning: Disk usage is above 90%
```

Everything else behaves as with Rich: `--verbosity` sets the level, `enable_secrets_filter` and
`sensitive_fields` mask secrets, and `--log-file` writes the rotating file.

### Rich Markup in Log Messages

```python
from pyclifer import logger

logger.info("[green]✓[/green] Success!")
logger.warning("[yellow]⚠[/yellow] Warning!")

try:
    risky_operation()
except Exception:
    logger.exception("Rich will display beautiful tracebacks")
```

## See Also

- [Getting Started](getting-started.md)
- [Examples](examples.md)
