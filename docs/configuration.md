# Configuration Management

pyclifer provides powerful configuration management through the `CustomConfigOption` class, which extends
click-extra's configuration support with multi-location search and Linux system conventions.

## Overview

The configuration system supports:

- **Multiple file formats**: TOML, YAML, JSON
- **Multiple search locations**: System-wide and user-specific directories
- **Environment variable integration**: Automatic mapping with configurable prefixes
- **Glob pattern support**: Wildcard matching for configuration files
- **Cross-platform compatibility**: Linux-specific features with fallbacks

## CustomConfigOption Features

### 1. Multi-location Support

The configuration system searches for files in multiple locations automatically:

- **System-wide configuration** (Linux only): `/etc/<cli_name>/`
- **User-specific configuration**: `~/.config/<cli_name>/` (or platform equivalent)
- **Explicitly provided paths**: Via `--config` option

### 2. Linux System Integration

On Linux, pyclifer follows standard conventions by looking for system-wide configuration in `/etc/<cli_name>/`.
This allows system administrators to set default configurations for all users.

### 3. Multiple Format Support

Configuration files can be written in:

- **TOML** (recommended): `config.toml`
- **YAML**: `config.yaml` or `config.yml`
- **JSON**: `config.json`

### 4. Glob Pattern Support

Use wildcard patterns to specify configuration files:

```bash
myapp --config "/etc/myapp/*.toml"
myapp --config "~/.config/myapp/dev-*.yaml"
```

## Configuration Search Order

1. **System-wide** (Linux only): `/etc/<cli_name>/*.{toml,yaml,json}`
2. **User-specific**: `~/.config/<cli_name>/*.{toml,yaml,json}`
3. **Explicitly provided**: Any path passed via `--config`

Files found later override values from earlier files, so users can override system defaults.

## Environment Variables

All options automatically support environment variables with a configurable prefix.

### Automatic Mapping

For a CLI named "myapp" with prefix "MYAPP":

| CLI Option       | Environment Variable | Example                                               |
|------------------|----------------------|-------------------------------------------------------|
| `--database-url` | `MYAPP_DATABASE_URL` | `export MYAPP_DATABASE_URL="postgres://localhost/db"` |
| `--timeout`      | `MYAPP_TIMEOUT`      | `export MYAPP_TIMEOUT="30"`                           |
| `--config`       | `MYAPP_CONFIG`       | `export MYAPP_CONFIG="/etc/myapp/prod.toml"`          |

### Setting the Environment Variable Prefix

```python
from pyclifer import app_group


@app_group(auto_envvar_prefix="MYAPP")
def cli():
    """My application."""
    pass
```

## Configuration File Structure

Configuration files in click-extra (and pyclifer) automatically derive their structure from your CLI commands and
options. The structure mirrors your command hierarchy — you don't manually create arbitrary sections.

### How It Works

- Top-level options go at the root level
- Command-specific options go under the command name
- Sub-commands create nested sections

### Example CLI Structure

```python
from pyclifer import app_group, command, option
import click


@app_group(name="myapp")
def cli():
    """myapp cli."""
    pass


@cli.command()
@option("--database-url", help="Database URL")
@option("--timeout", type=int, default=30, help="Timeout")
def connect(database_url, timeout):
    """Connect to database."""
    pass


@cli.command()
@option("--output-file", help="Output file path")
@option("--format", type=click.Choice(["json", "yaml"]), help="Output format")
def export(output_file, format):
    """Export data."""
    pass
```

### Corresponding Configuration Files

**config.toml**:

```toml
[myapp.connect]
database-url = "postgres://localhost/myapp"
timeout = 60

[myapp.export]
output-file = "/tmp/export.json"
format = "json"
```

**config.yaml**:

```yaml
myapp:
  connect:
    database-url: "postgres://localhost/myapp"
    timeout: 60
  export:
    output-file: "/tmp/export.json"
    format: "json"
```

**config.json**:

```json
{
  "myapp": {
    "connect": {
      "database-url": "postgres://localhost/myapp",
      "timeout": 60
    },
    "export": {
      "output-file": "/tmp/export.json",
      "format": "json"
    }
  }
}
```

### Key Configuration Rules

1. **Command names become section names**: `@cli.command()` functions create configuration sections
2. **Option names map directly**: `--database-url` becomes `database-url` in config
3. **Nested commands create nested sections**: Sub-groups create deeper nesting
4. **Global options go at root**: Options on the main group go at the top level
5. **No arbitrary sections**: Only command names are valid top-level sections

### Common Mistakes

❌ **Wrong — arbitrary sections:**

```toml
[database]   # Does not match any command
url = "postgres://localhost/db"
```

✅ **Correct — command-based sections:**

```toml
[myapp.connect]   # Matches the "connect" command
database-url = "postgres://localhost/db"
timeout = 30
```

## Usage Examples

### System Configuration (Linux)

```bash
sudo mkdir -p /etc/myapp
sudo tee /etc/myapp/config.toml << EOF
[connect]
database-url = "postgres://prod-server/myapp"
timeout = 60
EOF

myapp connect  # picks up system config automatically
```

### User Configuration

```bash
mkdir -p ~/.config/myapp
cat > ~/.config/myapp/config.toml << EOF
[connect]
database-url = "postgres://localhost/myapp_dev"
timeout = 10
EOF
```

### Override with Environment Variables

```bash
export MYAPP_TIMEOUT="60"
myapp connect  # Uses timeout=60, overriding config file
```

### Explicit Configuration File

```bash
myapp --config /path/to/custom-config.toml connect
```

## Configuration in Code

### Automatic Configuration Option

`@app_group` adds the configuration option automatically:

```python
from pyclifer import app_group


@app_group(add_config_option=True)  # default
def cli():
    """My CLI with automatic config option."""
    pass
```

### Disabling Automatic Configuration

```python
from pyclifer import app_group


@app_group(add_config_option=False)
def cli():
    """My CLI without config option."""
    pass
```

### Custom Configuration Option

```python
import click_extra
from pyclifer import app_group, CustomConfigOption


@click_extra.option(
    "--config", "-C",
    cls=CustomConfigOption,
    help="Custom configuration file location"
)
@app_group(add_config_option=False)
def cli():
    """My CLI with a custom config option."""
    pass
```

## Troubleshooting

### Configuration Not Found

1. Check file permissions (readable by the user)
2. Verify file format syntax (use a validator for TOML/YAML/JSON)
3. Check search paths with verbose output: `myapp -vv --help`
4. Verify environment variable names match the expected pattern

### Multiple Configuration Files

Files are merged in order — later files override earlier ones:

```
/etc/myapp/base.toml
/etc/myapp/production.toml
~/.config/myapp/personal.toml
```

### Environment Variable Conflicts

Environment variables take precedence over configuration files:

```bash
# Config file has timeout = 30, but:
export MYAPP_TIMEOUT="60"
myapp connect  # Uses timeout=60
```

## See Also

- [Getting Started](getting-started.md)
- [Examples](examples.md)
