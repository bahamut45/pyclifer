# Core Classes

Internal Click subclasses and configuration objects. Exposed publicly for advanced use
cases such as subclassing or type-checking.

## PycliferOption

Extends `click.Option` with `is_global` and env-var binding support.

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