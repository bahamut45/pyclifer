# Context

## BaseContext

The context object passed to every command via `pass_cli_context`. Composites
`RichHelpersMixin` and `OutputFormatMixin` to expose Rich console helpers and output
dispatching.

::: pyclifer.BaseContext