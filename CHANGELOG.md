# Changelog

All notable changes to this project will be documented in this file.

## [0.9.0] - 2026-11-02

### Bug Fixes

- **response**: Answer Click usage errors in structured formats
- **events**: Report a handler error swallowed on a bare call
- **events**: Validate event names in emit
- **response**: Forward add_command keyword arguments
- **decorators**: Stop duplicating options without rich help
- **decorators**: Make output_format_default the contract of the application
- **response**: Wrap sub-group commands attached after being defined
- **log**: Honor enable_secrets_filter and sensitive_fields at run time
- **decorators**: Honor show_envvar on the automatic options
- **log**: Let --verbosity be stricter than the default
- **log**: Honor use_rich_logging=False with a standard console handler
- **log**: Mask secrets in exception tracebacks with mask_free_text
- **mixins**: List propagated global options in the help of plain commands
- **mixins**: Hand context options on to commands added after their group
- **mixins**: Stop passing propagated options to groups that cannot take them
- **mixins**: Apply use_rich_help=False to the whole application
- **options**: Read one environment variable for a global option
- **decorators**: Let Click errors and exits through returns_response
- **output**: Dump unknown objects as plain YAML
- **log**: Install trace() when pyclifer is imported
- **log**: Point TRACE records at the caller
- **decorators**: Accept click_extra option classes in option()
- **log**: Count the trace() frame only on Python 3.11+
- **renderer**: Explain when Response.data is not a dict
- **decorators**: Answer a rendering failure in the requested format
- **decorators**: Search the MRO for is_global in option()
- **output**: Keep container subclasses intact in YAML output
- **log**: Make the free-text masking regex linear
- **decorators**: Accept output_format_default in any casing
- **decorators**: Name global option variables per invocation
- **output**: Write an Enum as its value in JSON and YAML
- **decorators**: Keep structured stdout valid when printing fails twice
- **decorators**: Refuse version= without the version option

### Documentation

- **specs**: Retarget click-extra upgrade spec to 9.x
- **specs**: Note config priority gap in click-extra upgrade spec
- **specs**: Add config-system-user-merge spec
- **classes**: Explain Extra prefix of PycliferExtraGroup
- **claude**: Require doc-review before a version bump
- **specs**: Add usage-errors-json-response spec
- **specs**: Add lifecycle-events spec
- **specs**: Rework lazy-command-loading spec
- **specs**: Drop issue placeholder from lifecycle-events
- **claude**: Require testing behaviour instead of assuming it
- **specs**: Mark lifecycle-events verification done
- **events**: Document lifecycle events
- **events**: Note two measured edge cases
- **specs**: Add integration-test-matrix spec
- **testing**: Document the integration suite and archive spec 15
- **specs**: Add code-review-findings spec
- **specs**: Record logging decisions and add init-at-runtime draft
- **specs**: Add the correction plan to the review spec
- **claude**: Record design principles and working rules in CLAUDE.md
- **claude**: Note the PyPI trusted publisher prerequisite
- **specs**: Add the integration-suite replay to the lazy-commands spec
- **decorators**: Fix the log_file_option docstring order
- **specs**: Archive the code-review findings spec
- Fix the findings of the doc-review before 0.9.0

### Features

- **config**: Merge system and user config files, user wins
- **events**: Add lifecycle event names
- **events**: Add EventsMixin
- **events**: Wire on= into groups and decorators
- **events**: Emit config.loaded after the config resolution
- **events**: Let users define their own events
- **response**: Make handle_response tri-state on groups
- **log**: Add mask_free_text to mask key=value secrets in messages
- **log**: Add GroupConfig.replace_root_handlers

### Miscellaneous

- **deps**: Refresh uv.lock to latest compatible versions
- **deps**: Align ruff pre-commit hook with ruff 0.17.3

### Tests

- **integration**: Add feature inventory and exhaustiveness guard
- **integration**: Add the scenario harness
- **integration**: Measure GroupConfig across a configuration matrix
- **integration**: Measure the effect of every automatic option
- **integration**: Add propagation and parity scenarios (spec 15 item 5)
- **integration**: Add public API scenarios (spec 15 item 6)

## [0.8.0] - 2026-08-30

### Bug Fixes

- **testing**: Separate CliResult.output from merged stderr stream

### Documentation

- **specs**: Add 8 independent feature specs
- **specs**: Add documentation tasks to all 8 feature specs
- **claude**: Enforce documentation updates as part of spec definition of done
- **specs**: Rename decorator to with_renderer_class, add scaffolding migration
- Add graphify skill instructions to CLAUDE.md
- **specs**: Add issue-7 lazy-command-loading spec
- **specs**: Add issue-8 interactive-encrypted-configuration spec
- **specs**: Add click-extra-8-upgrade spec

### Features

- **testing**: Add pyclifer.testing module with pytest helpers

### Miscellaneous

- **gitignore**: Ignore graphify-out directory
- **graphify**: Add .graphifyignore file for custom corpus exclusions
- **specs**: Prefix spec files with priority order
- **specs**: Archive 01-test-helpers spec

## [0.7.5] - 2026-06-14

### Bug Fixes

- **decorators**: Suppress traceback in JSON/YAML output mode

### Documentation

- **specs**: Add issue-6 suppress-traceback-json-mode spec

### Miscellaneous

- **specs**: Archive issue-6 suppress-traceback-json-mode

## [0.7.4] - 2026-06-14

### Tests

- **decorators**: Fix CI-fragile MissingParameter assertion

## [0.7.3] - 2026-06-14

### Bug Fixes

- **docs**: Replace broken @cli.group()+@group() with @group()+add_command()

### Documentation

- **getting-started**: Fix standalone @group example missing parent wiring
- **getting-started**: Add Response pattern example alongside print() minimal
- **api/decorators**: Document store_in_meta, handle_response, and app_group kwargs
- **logging**: List full DEFAULT_FIELDS, add PYCLIFER_LOG_LEVELS value, log handler example
- **output-formatting**: Document model_class, datetime_format, date_format on BaseRenderer

### Miscellaneous

- **plans**: Archive demo-page and doc-review-fixes plans

## [0.7.2] - 2026-06-12

### Bug Fixes

- **cli**: Use panel attr instead of rich_help_panel on display copies
- **decorators**: Skip required-option validation when subcommand requests --help

### Miscellaneous

- **plans**: Archive required-options-block-help plan

## [0.7.1] - 2026-06-11

### Bug Fixes

- **responses**: Set error_code=0 on successful responses

### Documentation

- **error-handling**: Correct error_code description for successful responses

### Miscellaneous

- **plans**: Archive context-options-subcommand-help plan

## [0.7.0] - 2026-06-10

### Documentation

- **api**: Document show_in_subcommand_help, context_options_panel, and mixin propagation

### Features

- **classes**: Add show_in_subcommand_help to PycliferOption and context_options_panel to GroupConfig
- **mixins**: Add CONTEXT_OPTIONS_PANEL constant and _get_context_option_display_copy
- **decorators**: Forward show_in_subcommand_help and store _context_options_panel on group
- **mixins**: Add _propagate_context_options and update add_command

### Miscellaneous

- **tests**: Fix test_classes module docstring and tighten panel default assertion

### Tests

- **mixins**: Add end-to-end integration tests for context options in subcommand help
- **mixins**: Cover plain option without context attr in display copy

## [0.6.0] - 2026-06-09

### Documentation

- **specs**: Add base-renderer-failed-result spec
- **output**: Document failed OperationResult handling in BaseRenderer

### Features

- **renderer,tables**: First-class failed OperationResult handling

### Tests

- **log**: Cover set_level more-verbose branch in PycliferVerbosityOption

## [0.5.0] - 2026-06-09

### Documentation

- **specs**: Add anywhere-passable options spec
- Add context-options how-to guide and update API docs

### Features

- **classes,decorators**: Add context= option and context_factory
- **scaffold**: Use context_factory pattern in generated projects
- Anywhere-passable options and declarative context construction

### Miscellaneous

- Add .worktrees/ to .gitignore

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


