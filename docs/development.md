# Development and Testing

This guide covers development practices, testing, and contribution guidelines for pyclifer.

## Development Setup

### Requirements

- Python 3.10 or higher
- uv for dependency management
- Git for version control

### Setting up the Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bahamut45/pyclifer.git
   cd pyclifer
   ```

2. **Install dependencies:**
   ```bash
   uv sync --extra dev
   ```

3. **Activate the virtual environment (optional — uv run handles this automatically):**
   ```bash
   source .venv/bin/activate
   ```

## Project Structure

```
pyclifer/
├── src/pyclifer/              # Main package
│   ├── __init__.py          # Public API exports
│   └── core/                # Core functionality
│       ├── __init__.py      # Core exports
│       ├── callbacks.py     # Click callbacks (meta storage)
│       ├── classes.py       # PycliferOption, PycliferGroup, CustomConfigOption
│       ├── context.py       # BaseContext
│       ├── decorators.py    # @app_group, @group, @command, @option
│       ├── rich_help_config.py  # Rich-click help configuration
│       ├── logging/         # Rich logging system
│       └── mixins/          # Feature mixins (cli, output, response, rich)
│           └── output/      # Response, CliTable, ExceptionTable
├── tests/                   # Test files (mirror src/ layout)
├── docs/                    # Documentation
├── pyproject.toml           # Project configuration
└── README.md                # Main project README
```

## Testing

The project uses pytest with comprehensive test coverage.

### Running Tests

```bash
# All tests
uv run python -m pytest tests/ -v

# Specific test file
uv run python -m pytest tests/core/log/test_verbosity_default.py -v

# With coverage
uv run python -m pytest tests/ --cov=pyclifer --cov-report=html
```

### Test Categories

1. **Unit tests**: Test individual components in isolation
2. **Integration tests** (`tests/integration/`): Run every feature in a real application (see below)
3. **Configuration tests**: Test `CustomConfigOption` functionality
4. **Logging tests**: Test verbosity, file logging, Rich formatting
5. **Tox compatibility tests**: Marked `@pytest.mark.tox` — multi-version checks

### The Integration Suite

`tests/integration/` builds real applications and drives them from the command line, to find defects
that appear only when features are combined. It has four parts:

- **`inventory.py`** discovers the features by introspection: every `GroupConfig` field, every option
  factory, every name in `pyclifer.__all__` and every framework event. Nothing is listed by hand.
- **`scenarios.py`** says where each feature is exercised. A feature is either `COVERED` (it maps to
  `path/to/test_file.py::TestClass`) or `EXCLUDED` (it maps to the reason it is not tested). `PENDING`
  stays empty.
- **`test_inventory.py`** fails when a discovered feature is not declared, when a declaration is stale or
  duplicated, or when a `COVERED` entry points at a test that does not exist. A new `GroupConfig` field,
  option factory, public symbol or event therefore needs an entry in `scenarios.py`.
- **`harness.py`** builds an application and `assert_healthy` checks the contract that says it works: no
  warning while building, unique option names, `--help` working, a command answering in the requested
  format, and an unknown command exiting with code 2.

The scenarios cover the `GroupConfig` matrix (`test_group_config_matrix.py`), the automatic options
(`test_automatic_options.py`), propagation and Rich/plain help parity at three depths
(`test_propagation.py`) and the public API (`test_public_api.py`).

When you write a scenario, run the case in a fresh process first and assert what it printed, not what
you expect it to print. Logging is global to the process, which is why `conftest.py` restores it around
every test. A defect found this way gets its own failing test and its own commit.

The whole suite takes about 26 seconds without coverage and about 48 seconds with the default
coverage options. The integration tests are about 17 seconds of that.

### Writing Tests

```python
import pytest
from click.testing import CliRunner
from pyclifer import app_group, command, option


@app_group()
def test_cli():
    """Test CLI application."""
    pass


@test_cli.command()
@option("--name", required=True, help="Name parameter")
def hello(name):
    """Test hello command."""
    print(f"Hello {name}!")


def test_hello_command():
    runner = CliRunner()
    result = runner.invoke(test_cli, ["hello", "--name", "Test"])
    assert result.exit_code == 0
    assert "Hello Test!" in result.output


def test_missing_required_option():
    runner = CliRunner()
    result = runner.invoke(test_cli, ["hello"])
    assert result.exit_code != 0
    assert "Missing option" in result.output
```

### Testing with pyclifer.testing

pyclifer ships a `pyclifer.testing` module that removes the `CliRunner` boilerplate
shown above. It is available without any extra dependency — `pytest` is already
in the project's `dev` extra. It is not re-exported from `pyclifer.__init__` so
`pytest` stays a dev-only dependency.

```python
from pyclifer.testing import invoke

def test_hello_command():
    result = invoke(test_cli, ["hello", "--name", "Test"])
    assert result.exit_code == 0
    assert "Hello Test!" in result.output
```

`CliResult` (returned by `invoke()`) exposes typed accessors:

| Property | Type | Description |
|----------|------|--------------|
| `exit_code` | `int` | Command exit code |
| `output` | `str` | Full stdout output |
| `stderr` | `str` | Captured stderr output |
| `json` | `Any` | Stdout parsed as JSON — raises `ValueError` if invalid |
| `yaml` | `Any` | Stdout parsed as YAML — raises `ValueError` if invalid |
| `exception` | `Exception \| None` | Unhandled exception, or None on clean exit |

pytest fixtures are also available — import them into your `conftest.py`:

```python
# conftest.py
from pyclifer.testing import cli_runner, cli_invoke
```

### Testing Configuration Files

```python
def test_config_file_loading():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("test_config.toml", "w") as f:
            f.write('[hello]\nname = "From Config"\n')

        result = runner.invoke(test_cli, ["--config", "test_config.toml", "hello"])
        assert result.exit_code == 0
        assert "Hello From Config!" in result.output
```

## Code Quality

### Linting and Formatting

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

### Code Style Summary

- **Type hints**: PEP 585 built-in generics (`list[str]`, `dict[str, Any]`), never `typing.List`/`Dict`/`Optional`
- **Docstrings**: Google style, required on all public classes, methods, and functions
- **Naming**: `snake_case` for functions/modules, `PascalCase` for classes, `_single_underscore` for private
- **Imports**: PEP 8 order — stdlib → third-party → local; relative imports preferred inside the package

See `CLAUDE.md` for the full style reference.

## Testing Across Python Versions

pyclifer supports Python 3.10, 3.11, 3.12, and 3.13. Use tox to test across all versions:

```bash
# Test all supported versions
uv run tox

# Test a specific version
uv run tox -e py310
uv run tox -e py313
```

Note: always use `uv run tox` rather than `tox` directly, so the project venv's tox (with the tox-uv plugin)
is used.

### tox Configuration

```toml
[tool.tox]
env_list = ["py310", "py311", "py312", "py313"]
isolated_build = true

[tool.tox.env_run_base]
runner = "uv-venv-lock-runner"
package = "editable"
extras = ["dev"]
commands = [
    ["python", "-m", "pytest", "tests/", "-v"],
    ["pyclifer", "--help"],
]
```

## Contributing

### Workflow

1. **Fork** the repository on GitHub
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make changes** and add tests
4. **Run tests:**
   ```bash
   uv run python -m pytest tests/ -v
   ```
5. **Run quality checks:**
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   ```
6. **Commit:**
   ```bash
   git commit -m "✨ feat: add your feature description"
   ```
7. **Push and open a Pull Request** on GitHub

### Commit Message Convention

pyclifer uses conventional commits with emoji prefixes:

| Prefix | Type     |
|--------|----------|
| ✨      | feat     |
| 🐛     | fix      |
| 📝     | docs     |
| 🧪     | test     |
| ♻️     | refactor |
| 🎨     | style    |
| 🚀     | release  |

## Release Process

Versions are managed with `bump-my-version`. Version is synced across `pyproject.toml`, `README.md`, and
`src/pyclifer/__init__.py`.

```bash
# Bump patch version (1.0.0 → 1.0.1)
uv run bump-my-version bump patch

# Bump minor version (1.0.0 → 1.1.0)
uv run bump-my-version bump minor
```

## See Also

- [Getting Started](getting-started.md)
- [Configuration Management](configuration.md)
- [Output Formatting](output-formatting.md)
- [Examples](examples.md)
