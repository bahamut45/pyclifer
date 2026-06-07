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
2. **Integration tests**: Test decorator interactions and CLI flows
3. **Configuration tests**: Test `CustomConfigOption` functionality
4. **Logging tests**: Test verbosity, file logging, Rich formatting
5. **Tox compatibility tests**: Marked `@pytest.mark.tox` — multi-version checks

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
