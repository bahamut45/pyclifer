# ExitCode — named exit codes with POSIX OS exit integration

## Problem

Two problems exist today:

1. `error_code` values are bare integers scattered across the codebase
   (`error_code=1`, `error_code=2`, `error_code=404`). There is no shared vocabulary:
   a reader seeing `error_code=2` has no idea whether it means "already exists",
   "bad argument", or something project-specific.

2. `error_code` is never used as the actual OS exit code. A command returning
   `Response(success=False, error_code=3)` still exits with `$? = 0`. Shell scripts
   cannot detect failures — a fundamental gap for a CLI framework.

## Design decision

Introduce `ExitCode`, a plain class with integer class attributes that:

1. Uses small POSIX-safe integers (0–127) as both the classification code in structured
   output and the actual OS exit code — one value, two consumers.
2. Is a standard Python class — projects subclass freely, no `IntEnum` restriction.
3. Is registered with the framework via `@app_group(exit_codes_class=MyExitCode)`,
   following the same explicit central-registration contract as Django's `MIDDLEWARE`
   in `settings.py`: declare once in the app entry point, framework uses it everywhere.

Wire `returns_response` to call `ctx.exit(result.error_code)` when
`result.success is False`, reading the active class from `ctx.meta["pyclif.exit_codes_class"]`.

## ExitCode definition

Lives in `src/pyclif/core/output/exit_codes.py`:

```python
class ExitCode:
    """Standard exit codes for pyclif commands.

    Values are POSIX-safe (0–127) and serve as both the classification code
    in structured output (JSON, YAML) and the actual OS exit code.

    Projects register a subclass via @app_group(exit_codes_class=MyExitCode).
    Subclasses inherit all base codes and add project-specific ones in the
    6–125 range (0–5 are reserved for pyclif, 126+ are reserved by the shell).

    Example:
        from pyclif import ExitCode as _Base

        class ExitCode(_Base):
            QUOTA_EXCEEDED = 10
            RATE_LIMITED = 11
    """

    SUCCESS = 0
    ERROR = 1
    ALREADY_EXISTS = 2
    NOT_FOUND = 3
    PERMISSION_DENIED = 4
    INVALID_INPUT = 5
```

Rationale for the default set:

| Code | Name                | Current usage / rationale                               |
|------|---------------------|---------------------------------------------------------|
| 0    | `SUCCESS`           | POSIX standard — implicit default on `OperationResult`  |
| 1    | `ERROR`             | POSIX standard — unhandled exceptions in `decorators.py`, `output.py` |
| 2    | `ALREADY_EXISTS`    | Already used throughout `project/interfaces.py`         |
| 3    | `NOT_FOUND`         | Replaces `error_code=404` in `demo/apps/tasks/`         |
| 4    | `PERMISSION_DENIED` | Logical complement to NOT_FOUND                         |
| 5    | `INVALID_INPUT`     | Completes the basic set                                 |

### Safe value ranges for project codes

| Range   | Reserved for                              | Verdict         |
|---------|-------------------------------------------|-----------------|
| 0–5     | pyclif framework codes                    | reserved        |
| 6–125   | Application-specific codes                | **use this**    |
| 126     | Command found but not executable (shell)  | do not use      |
| 127     | Command not found (shell)                 | do not use      |
| 128+n   | Signal exits (SIGTERM=143, SIGKILL=137)   | do not use      |
| 255     | Overflow / out-of-range                   | do not use      |

## Extensibility pattern — Django-style registration

Same explicit contract as Django's `MIDDLEWARE` in `settings.py`: declare the extension
once in the app entry point, the framework uses it everywhere. No magic, no import order
dependency.

```python
# core/constants.py — project defines its subclass
from pyclif import ExitCode as _Base

class ExitCode(_Base):
    QUOTA_EXCEEDED = 10   # inherits SUCCESS, ERROR, NOT_FOUND, etc.
    RATE_LIMITED = 11
```

```python
# cli.py — single registration point, like settings.py
from pyclif import app_group
from my_project.core.constants import ExitCode

@app_group(exit_codes_class=ExitCode)
def cli(): ...
```

The framework stores the class in `ctx.meta["pyclif.exit_codes_class"]`.
`returns_response` reads it via `meta.get("pyclif.exit_codes_class", ExitCode)` —
base class when nothing is registered, project subclass when one is.

Interfaces use `from pyclif import ExitCode` for base codes. Only files that reference
project-specific codes import from `constants.py`:

```python
# apps/billing/interfaces.py — custom code, import from project constants
from my_project.core.constants import ExitCode

OperationResult.error(item=plan, message="Quota exceeded.", error_code=ExitCode.QUOTA_EXCEEDED)
```

For base codes, `from pyclif import ExitCode` is always sufficient — the integer value
is identical whether it comes from the base class or the subclass.

## Validation

When `exit_codes_class` is provided, `@app_group` validates that all project-specific
values (those not present in the base `ExitCode`) fall within 6–125:

```python
_PROJECT_EXIT_CODE_MIN = 6
_PROJECT_EXIT_CODE_MAX = 125


def _validate_exit_codes_class(cls: type) -> None:
    """Raise ValueError if cls is not a valid ExitCode subclass."""
    if not (isinstance(cls, type) and issubclass(cls, ExitCode)):
        raise ValueError(
            f"{cls!r} must be a subclass of ExitCode."
        )
    base_values = {v for k, v in vars(ExitCode).items() if not k.startswith("_")}
    invalid = {
        k: v
        for k, v in vars(cls).items()
        if not k.startswith("_")
        and isinstance(v, int)
        and v not in base_values
        and not (_PROJECT_EXIT_CODE_MIN <= v <= _PROJECT_EXIT_CODE_MAX)
    }
    if invalid:
        details = ", ".join(f"{k}={v}" for k, v in invalid.items())
        raise ValueError(
            f"Project exit code values must be in 6–125 (pyclif uses 0–5, "
            f"shell reserves 126+). Invalid: {details}"
        )
```

## OS exit integration

`returns_response` in `core/decorators.py` calls `ctx.exit()` after dispatching output
when the response is a failure:

```python
output_ctx.print_result_based_on_format(result, options=options)
if isinstance(result, _Response) and not result.success and result.error_code:
    ctx = click_extra.get_current_context(silent=True)
    if ctx is not None:
        ctx.exit(result.error_code)
```

`ctx.exit()` raises `SystemExit` via Click's context — the correct way to exit inside
a Click command, triggering teardown hooks and avoiding double-exit issues.

The `SystemExit(2)` raised directly in `output.py` for an unresolvable output path is
left unchanged — it is a framework-level hard failure unrelated to `error_code`.

## Changes required

### 1. New file: `src/pyclif/core/output/exit_codes.py`

`ExitCode` plain class + `_validate_exit_codes_class()` + `_PROJECT_EXIT_CODE_MIN/MAX`.

### 2. `src/pyclif/core/output/__init__.py`

Add `ExitCode` to imports and `__all__`.

### 3. `src/pyclif/__init__.py`

Add `ExitCode` to `__all__` and the re-export block.

### 4. `GroupConfig` — `exit_codes_class` field

Add `exit_codes_class: type[ExitCode] = ExitCode` to `GroupConfig` in `core/classes.py`.
`@app_group` calls `_validate_exit_codes_class(exit_codes_class)` then stores the class
in `GroupConfig` and forwards it into `ctx.meta["pyclif.exit_codes_class"]` when the
group is invoked.

### 5. `OperationResult.error()` default

```python
@classmethod
def error(
    cls,
    item: str,
    message: str,
    error_code: int = ExitCode.ERROR,
) -> OperationResult: ...
```

### 6. Replace hardcoded integers in framework internals

| File                             | Before            | After                               |
|----------------------------------|-------------------|-------------------------------------|
| `core/decorators.py:340`         | `error_code=1`    | `error_code=ExitCode.ERROR`         |
| `core/mixins/output.py:82`       | `error_code=1`    | `error_code=ExitCode.ERROR`         |
| `core/mixins/output.py:234`      | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:66`  | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:107` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:179` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:236` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:270` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:287` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/project/interfaces.py:557` | `error_code=2`    | `error_code=ExitCode.ALREADY_EXISTS`|
| `apps/demo/.../interfaces.py:126`| `error_code=404`  | `error_code=ExitCode.NOT_FOUND`     |
| `apps/demo/.../interfaces.py:145`| `error_code=404`  | `error_code=ExitCode.NOT_FOUND`     |
| `apps/demo/.../interfaces.py:171`| `error_code=404`  | `error_code=ExitCode.NOT_FOUND`     |

### 7. `core/decorators.py` — OS exit integration

Add the `ctx.exit()` call in `returns_response` after output dispatch (see "OS exit
integration" section above).

### 8. Scaffolding — generated `cli.py` template

Update `apps/project/templates/cli.py.jinja2` — `exit_codes_class` is omitted by
default (base `ExitCode` is used automatically). Add a commented example:

```python
# To extend exit codes, define a subclass in core/constants.py and register it:
# from {{ project_name }}.core.constants import ExitCode
# @app_group(exit_codes_class=ExitCode)
@app_group()
def cli(): ...
```

### 9. Tests

- `tests/core/output/test_exit_codes.py` (new):
  - Each `ExitCode` attribute equals its expected integer value
  - Subclass inherits all base codes and adds its own
  - `_validate_exit_codes_class()` accepts a valid subclass
  - `_validate_exit_codes_class()` raises `ValueError` for a class that does not inherit `ExitCode`
  - `_validate_exit_codes_class()` raises `ValueError` for values < 6
  - `_validate_exit_codes_class()` raises `ValueError` for values > 125
  - `_validate_exit_codes_class()` error message names the offending code(s)
  - Base `ExitCode` values (0–5) pass validation unchanged in a subclass

- `tests/core/test_decorators.py`:
  - Failed `Response` triggers `ctx.exit()` with `result.error_code`
  - Successful `Response` does not call `ctx.exit()`
  - Unhandled-exception `Response` carries `ExitCode.ERROR`
  - Registered subclass is stored in `ctx.meta["pyclif.exit_codes_class"]`

- `tests/apps/project/test_interfaces.py`:
  - `ALREADY_EXISTS` results carry `error_code == ExitCode.ALREADY_EXISTS`

- `tests/apps/demo/test_interfaces.py`:
  - `NOT_FOUND` results carry `error_code == ExitCode.NOT_FOUND`

### 10. Docs — `docs/api/output.md`

Add a section documenting `ExitCode` covering:
- The value table with rationale
- The subclassing and `@app_group(exit_codes_class=...)` registration pattern
- Safe value ranges for project codes
- The OS exit behaviour (`$?` on failure)

## What does NOT change

- `error_code: int` type annotation on `OperationResult` and `Response` — `ExitCode`
  attributes are plain `int` values, fully compatible.
- `from_results()` aggregation logic — unchanged.
- All callers that pass a plain `int` literal continue to work.
- The `SystemExit(2)` in `output.py` for an unresolvable output path — unchanged.

## Delivery checklist

1. [ ] `src/pyclif/core/output/exit_codes.py` — `ExitCode` + `_validate_exit_codes_class`
2. [ ] `src/pyclif/core/output/__init__.py` — re-export `ExitCode`
3. [ ] `src/pyclif/__init__.py` — add to `__all__`
4. [ ] `core/classes.py` — `exit_codes_class` field on `GroupConfig`
5. [ ] `core/decorators.py` — validate + store `exit_codes_class` in `ctx.meta`
6. [ ] `OperationResult.error()` — update default to `ExitCode.ERROR`
7. [ ] Replace all hardcoded integers in framework internals (table above)
8. [ ] `core/decorators.py` — add `ctx.exit()` call in `returns_response`
9. [ ] Update scaffolding template `cli.py.jinja2`
10. [ ] `tests/core/output/test_exit_codes.py` — new test file
11. [ ] Update existing tests that assert on raw `error_code` integers
12. [ ] `docs/api/output.md` — document `ExitCode` and the registration pattern