# Complete Examples

Comprehensive examples of using pyclif decorators to build various types of CLI applications.

## Basic CLI Application

```python
from pyclif import app_group, command, option


@app_group(
    name="myapp",
    auto_envvar_prefix="MYAPP"
)
def cli():
    """My Application — a sample CLI built with pyclif."""
    pass


@cli.command()
@option("--message", "-m", default="Hello World", help="Message to display")
def hello(message):
    """Display a greeting message."""
    print(message)


if __name__ == "__main__":
    cli()
```

```bash
python myapp.py hello --message "Welcome!"
python myapp.py hello -m "Hi there!"
MYAPP_MESSAGE="Hello from env!" python myapp.py hello
python myapp.py --log-file /tmp/myapp.log hello
```

## Database Management CLI

```python
from pyclif import app_group, group, option
import click


@app_group(name="dbmanager", auto_envvar_prefix="DBMGR")
def cli():
    """Database Management Tool."""
    pass


@cli.group()
@group(name="database")
def database():
    """Database management commands."""
    pass


@database.command()
@option("--url", "-u", required=True, help="Database URL")
@option("--timeout", "-t", type=int, default=30, help="Connection timeout")
@option("--ssl/--no-ssl", default=True, help="Use SSL connection")
def connect(url, timeout, ssl):
    """Connect to the database."""
    ssl_status = "with SSL" if ssl else "without SSL"
    print(f"Connecting to {url} with timeout {timeout}s {ssl_status}")


@database.command()
@option(
    "--backup-dir", "-d", required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Backup directory"
)
@option("--compress/--no-compress", default=True, help="Compress backup")
@option("--tables", multiple=True, help="Specific tables to backup")
def backup(backup_dir, compress, tables):
    """Backup the database."""
    compression = "with compression" if compress else "without compression"
    if tables:
        table_list = ", ".join(tables)
        print(f"Backing up tables [{table_list}] to {backup_dir} {compression}")
    else:
        print(f"Backing up entire database to {backup_dir} {compression}")


if __name__ == "__main__":
    cli()
```

```bash
dbmanager database connect --url postgres://localhost/mydb --timeout 60
dbmanager database backup --backup-dir /backups --compress
dbmanager database backup -d /backups --tables users orders --no-compress
```

## Web Service CLI

```python
from pyclif import app_group, group, option
import click


@app_group(name="webctl", auto_envvar_prefix="WEBCTL")
def cli():
    """Web Service Control Tool."""
    pass


@cli.group()
@group(name="service")
def service():
    """Service management commands."""
    pass


@service.command()
@option("--port", "-p", type=int, default=8080, help="Service port")
@option("--host", "-h", default="localhost", help="Service host")
@option("--workers", "-w", type=int, default=4, help="Number of workers")
@option("--debug/--no-debug", default=False, help="Enable debug mode")
def start(port, host, workers, debug):
    """Start the web service."""
    mode = "debug" if debug else "production"
    print(f"Starting service on {host}:{port} with {workers} workers in {mode} mode")


@service.command()
@option("--force", "-f", is_flag=True, help="Force stop without graceful shutdown")
def stop(force):
    """Stop the web service."""
    method = "force" if force else "graceful"
    print(f"Stopping service with {method} shutdown")


@service.command()
def status():
    """Show service status."""
    print("Service status: Running")
```

**Configuration file** (`~/.config/webctl/config.toml`):

```toml
[service.start]
host = "0.0.0.0"
port = 8080
workers = 8
debug = false
```

```bash
webctl service start --port 9000 --workers 8 --debug
webctl service stop --force
webctl service status
webctl --config ~/.config/webctl/production.toml service start
WEBCTL_PORT=9090 webctl service start
```

## Structured Output with Response

Attach a `BaseRenderer` subclass to control the output for every format — table columns,
JSON fields, and Rich display — from a single class.

```python
from pyclif import app_group, BaseRenderer, OperationResult, Response
import click


class UserRenderer(BaseRenderer):
    fields = ["id", "name", "active"]   # included in JSON / YAML / raw
    columns = ["id", "name", "active"]  # shown in the table
    rich_title = "Users"
    success_message = "Users retrieved."


@app_group()
@click.pass_context
def cli(ctx):
    """API management CLI."""
    pass


@cli.command()
@click.pass_context
def list_users(ctx):
    """List all users."""
    users = [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
    ]
    results = [OperationResult.ok(str(u["id"]), data=u) for u in users]
    return Response.from_results(results, renderer=UserRenderer())
```

```bash
myapp list-users                        # table (default format)
myapp --output-format json list-users   # JSON output
myapp -o yaml list-users                # YAML output
myapp -o text list-users                # plain message only
```

## Advanced Patterns

### Custom Validation

```python
from pyclif import app_group, option
import click


def validate_email(ctx, param, value):
    """Custom email validation."""
    if value and "@" not in value:
        raise click.BadParameter("Must be a valid email address")
    return value


@app_group(name="userctl", auto_envvar_prefix="USERCTL")
def cli():
    """User Management CLI."""
    pass


@cli.command()
@option("--email", required=True, callback=validate_email, help="User email address")
@option(
    "--role",
    type=click.Choice(["admin", "user", "guest"]),
    default="user",
    help="User role"
)
def create_user(email, role):
    """Create a new user."""
    print(f"Creating user {email} with role {role}")
```

### Global Options

```python
from pyclif import app_group, option
import click


@app_group(name="myapp", auto_envvar_prefix="MYAPP")
@option("--api-key", is_global=True, help="API key for authentication")
@click.pass_context
def cli(ctx, api_key):
    """My Application with a global API key."""
    pass


@cli.command()
@click.pass_context
def fetch(ctx, api_key):
    """Fetch data using the global API key."""
    print(f"Fetching with key: {api_key}")
```

## Testing Your CLI

```python
import pytest
from click.testing import CliRunner
from myapp import cli


def test_hello_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["hello", "--message", "Test"])
    assert result.exit_code == 0
    assert "Test" in result.output


def test_environment_variable():
    runner = CliRunner(env={"MYAPP_MESSAGE": "From Env"})
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "From Env" in result.output


def test_config_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("config.toml", "w") as f:
            f.write('[hello]\nmessage = "From Config"\n')
        result = runner.invoke(cli, ["--config", "config.toml", "hello"])
        assert result.exit_code == 0
        assert "From Config" in result.output
```

## See Also

- [Getting Started](getting-started.md)
- [Configuration Management](configuration.md)
- [Output Formatting](output-formatting.md)
- [Development and Testing](development.md)
