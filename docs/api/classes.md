# Core Classes

Internal Click subclasses and configuration objects. Exposed publicly for advanced use
cases such as subclassing or type-checking.

## PycliferOption

Extends `click.Option` with `is_global`, `context`, and env-var binding support.

- `is_global=True` — propagates this option to all subcommands automatically.
- `context=True` — marks the option as a *context option*: its value is passed
  to the `context_factory` callable on `@app_group`, and it is accepted at any
  position in the command chain (even after a subcommand name).

::: pyclifer.PycliferOption

---

## PycliferGroup

Base Click group class used by `app_group` and `group`. Composes
`HandleResponseMixin` + `GlobalOptionsMixin`.

::: pyclifer.PycliferGroup

---

## CustomConfigOption

Extends click-extra's config option with multi-location Linux config file search
(`/etc/<app>/`, `~/.config/<app>/`, etc.).

::: pyclifer.CustomConfigOption

---

## PycliferTimerOption

Internal option class powering `timer=True` on `@app_group`. Subclasses click-extra's
`TimerOption` to integrate with pyclifer's output format: suppresses the text echo in
`json`/`yaml` mode and injects timing fields into `Response.data` via `returns_response`.

::: pyclifer.core.classes.PycliferTimerOption