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

`SecretsMasker` ships with a built-in set of field names it always masks (`password`, `api_key`,
`token`, `secret`, `access_token`, etc.). Pass `sensitive_fields` to extend this list — the
defaults are never removed.

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
