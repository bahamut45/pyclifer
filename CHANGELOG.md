# Changelog

All notable changes to this project will be documented in this file.

## [0.4.2] - 2026-06-07

### Documentation

- **readme**: Clarify PYCLIFER acronym formatting and add French response rule
- Expand API reference and update project metadata
- **specs**: Add demo page design spec
- **plans**: Add demo page implementation plan
- **demo**: Scaffold demo page and add nav entry
- **demo**: Add introduction and page skeleton
- **demo**: Add CLI tour — explore, add, list
- **demo**: Add CLI tour — show, errors, sync, users
- **demo**: Add walkthrough — structure and model layer
- **demo**: Add walkthrough — renderer layer
- **demo**: Add walkthrough — interface layer
- **demo**: Add walkthrough — command layer
- **demo**: Add walkthrough — core layer and next steps
- **specs**: Archive demo-page-design spec
- **demo**: Translate tip admonition titles to English

## [0.4.1] - 2026-06-07

### Miscellaneous

- Add build job and PyPI publish workflow

## [0.4.0] - 2026-06-07

### Miscellaneous

- **docs**: Replace logo.png asset

## [0.3.1] - 2026-06-01

### Documentation

- **specs**: Add deps-upgrade spec

### Miscellaneous

- **deps**: Upgrade click-extra, rich, rich-click
- **specs**: Archive `2026-06-01-deps-upgrade-fr.md`
- **deps**: Isolate bump-my-version via uvx

## [0.3.0] - 2026-06-01

### Bug Fixes

- **log**: Correct get_configured_logger name parameter type annotation
- **output**: Use INVALID_INPUT exit code for missing filter path

### Documentation

- **claude**: Document git workflow, commit format and spec process
- **specs**: Add core-simplification spec (1.1 already implemented)
- **specs**: Mark 1.2 done in core-simplification
- **specs**: Mark 1.3 done in core-simplification
- **claude**: Include spec ✅ update in feature commit, not separately
- **claude**: Add pytest step and click_extra import rule
- **specs**: Add make-context refactor spec, archive core-simplification

### Miscellaneous

- **deps**: Declare rich as direct dependency
- **deps**: Update `rich` dependency constraints

## [0.2.0] - 2026-05-25

### Features

- **core**: Introduce named `ExitCode` integration with POSIX compliant behavior

## [0.1.7] - 2026-05-23

### Miscellaneous

- **workflows**: Update release workflow permissions

## [0.1.6] - 2026-05-23

### Miscellaneous

- **workflows**: Add GitHub Actions workflow for automated releases

## [0.1.5] - 2026-05-23

### Miscellaneous

- **deps**: Bump multiple dependencies to newer versions

## [0.1.4] - 2026-05-23

### Features

- **tasks**: Add Taskfile for development automation

## [0.1.3] - 2026-05-23

### Miscellaneous

- **deps**: Update `pydantic` and `pydantic-core` to latest versions

## [0.1.2] - 2026-05-23

### Style

- **tests**: Update tests to reflect `soft_wrap` changes in console printing

## [0.1.1] - 2026-05-22

### Documentation

- **README**: Update installation instructions with GitHub link
- **how-to**: Add comprehensive guides for pyclif patterns

### Miscellaneous

- **specs**: Archive how-to guides specification

### Style

- **output**: Enable `soft_wrap` for console printing

## [0.1.0] - 2026-05-22

### Documentation

- **demo**: Add comprehensive CLI demo specifications
- **project**: Add working style guidelines to CLAUDE.md

### Features

- **demo**: Introduce new Demo app scaffolding
- **cli**: Introduce `add_group` command for managing subgroups
- **cli**: Support nested app paths in `add_command`
- **project**: Improve app group initialization and renderer fields
- **demo**: Add Tasks and Users app groups with scaffolding
- **cli**: Support adding multiple commands in a single call
- **tasks**: Add core commands to the Tasks app
- **users**: Add `list` and `whoami` commands to Users app
- **demo**: Implement core functionality for Tasks and Users apps
- **apps**: Add scaffolding for apps with core utilities

### Miscellaneous

- **demo**: Archive demo CLI spec

### Refactoring

- **project**: Modularize list variable wiring logic

## [0.0.15] - 2026-05-20

### Features

- **models**: Introduce BaseModel for core domain modeling

### Miscellaneous

- **pre-commit**: Update `uv sync` command with additional dependency groups

## [0.0.14] - 2026-05-20

### Features

- **logging**: Add support for custom sensitive field masking
- **logging**: Enhance sensitive data masking and extend documentation
- **output**: Add pagination support to responses and commands
- **output**: Enhance filter path support and error handling

### Miscellaneous

- **pre-commit**: Update mkdocs build entry to use virtual environment
- **pre-commit**: Update `uv sync` hook with additional groups

### Refactoring

- **output**: Improve filter path resolution and error handling

## [0.0.13] - 2026-04-23

### Documentation

- **claude**: Update contributing guidelines for code quality and file structure

### Features

- **scaffolding**: Add support for flat apps without @group wrapper

## [0.0.12] - 2026-04-22

### Tests

- **core**: Add extensive test coverage for core helpers and decorators

### Style

- **tests**: Remove redundant comments and suppress specific inspections

## [0.0.11] - 2026-04-22

### Features

- **ci**: Add CI workflow with test coverage reporting

### Miscellaneous

- **pre-commit**: Refine `git-cliff` hook for version extraction

### Style

- **docs**: Improve branding with logo and favicon assets

## [0.0.10] - 2026-04-22

### Documentation

- **scaffolding**: Add comprehensive scaffolding usage and examples

### Features

- **scaffolding**: Enhance template generation and method wiring

### Miscellaneous

- **pre-commit**: Update `git-cliff` pre-commit hook for version tagging

## [0.0.9] - 2026-04-22

### Miscellaneous

- **pre-commit**: Update ruff hook to v0.15.11

### Refactoring

- **logging**: Migrate `logging` package to `log` for improved clarity

## [0.0.8] - 2026-04-22

### Documentation

- **output**: Refine and expand documentation for output handling updates

## [0.0.7] - 2026-04-21

### Features

- **docs**: Enhance pre-commit and documentation workflows
- **docs**: Update API documentation and improve structure
- **core**: Implement BaseInterface and Renderer foundations
- **output**: Improve renderer and output handling across major components

### Miscellaneous

- **docs**: Add alias configuration for versioning

### Tests

- **output**: Add comprehensive unit tests for `Response` and `OperationResult`

## [0.0.6] - 2026-04-20

### Features

- **dev**: Enhance development workflow with additional dependencies
- **error-handling**: Standardize error handling across interfaces and commands

### Miscellaneous

- **docs**: Simplify deployment logic in workflow

## [0.0.5] - 2026-04-19

### Miscellaneous

- **docs**: Update workflow config and deploy logic

## [0.0.4] - 2026-04-19

### Features

- **timer**: Add `--time/--no-time` option for execution timing

## [0.0.3] - 2026-04-19

### Documentation

- Update `CHANGELOG.md` and `pyproject.toml` for streamlined development workflow

## [0.0.2] - 2026-04-19

### Documentation

- Add repository guidelines for contribution and code style
- Refine `CLAUDE.md` formatting and update `.gitignore`
- Add comprehensive documentation for `pyclif` features and usage
- Streamline imports across documentation examples
- Add API documentation and deployment workflow
- Add comprehensive `README.md` for project overview and usage
- Update `README.md` with version badge

### Features

- **project**: Add `pyproject.toml` for project configuration
- **core**: Introduce foundational modules for `pyclif` framework
- **cli**: Add initial CLI entry point and scaffolding for `pyclif`
- **core**: Expand imports and `__all__` for extended functionality
- **core**: Expand `__all__` and imports for enhanced CLI capabilities
- **project**: Add scaffolding for `pyclif project` commands
- **tables**: Add `ScaffoldingTable` for enriched CLI output
- **project**: Integrate `git-cliff` for auto-generated changelogs
- **dev**: Integrate pre-commit hooks with Ruff for code linting and formatting

### Miscellaneous

- **gitignore**: Update `.gitignore` to exclude internal specs

### Refactoring

- **core**: Enhance type annotations and code formatting

### Tests

- **core**: Add comprehensive unit tests for `pyclif` core modules
- **project**: Add unit tests for `ScaffoldingInterface` and `ScaffoldingTable`

### Style

- **core**: Apply consistent code formatting across the project


