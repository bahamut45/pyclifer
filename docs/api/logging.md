# Logging

pyclifer ships a Rich-enhanced logging system with a custom `TRACE` level (5), automatic
secrets masking, and rotating file handler support.

## get_logger

Main factory. Returns a logger pre-configured with Rich formatting.

::: pyclifer.get_logger

---

## get_configured_logger

Returns a logger with full configuration applied (handlers, level, masker).

::: pyclifer.get_configured_logger

---

## configure_rich_logging

Low-level setup function. Called internally by `get_configured_logger`.

::: pyclifer.configure_rich_logging

---

## add_trace_method

Patches a logger instance with a `.trace()` method at level 5.

::: pyclifer.add_trace_method

---

## SecretsMasker

Log filter that redacts sensitive values from log records.

::: pyclifer.SecretsMasker

---

## RichExtraFormatter / RichExtraStreamHandler

Rich-aware formatter and stream handler. Wired up automatically by `configure_rich_logging`.

::: pyclifer.RichExtraFormatter

::: pyclifer.RichExtraStreamHandler

---

## Constants

::: pyclifer.TRACE

::: pyclifer.PYCLIFER_LOG_LEVELS