"""Logging filters for pyclif."""

import logging
import re
from collections import namedtuple
from typing import Any, ClassVar

DEFAULT_SENSITIVE_FIELDS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "passphrase",
        "pwd",
        "passwd",
        "password",
        "private_key",
        "secret",
        "token",
        "keyfile_dict",
        "service_account",
    }
)


def should_hide_value_for_key(name: str) -> bool:
    """Determine if a key's value should be hidden based on its name.

    Checks whether the key name matches any predefined sensitive field
    patterns using case-insensitive comparison.

    Args:
        name: The name of the key to evaluate.

    Returns:
        True if the name matches a sensitive field and should be masked,
        False otherwise.
    """
    if isinstance(name, str):
        name = name.strip().lower()
        return any(s in name for s in DEFAULT_SENSITIVE_FIELDS)
    return False


class SecretsMasker(logging.Filter):
    """Redact secrets from logs."""

    ALREADY_FILTERED_FLAG = "__SecretsMasker_filtered"
    DEFAULT_FIELDS: ClassVar[frozenset[str]] = DEFAULT_SENSITIVE_FIELDS

    def __init__(self, sensitive_fields: list[str] | None = None) -> None:
        """Initialize the masker, merging sensitive_fields into DEFAULT_FIELDS.

        Args:
            sensitive_fields: Additional field names to mask on top of DEFAULT_FIELDS.
                              None and [] are equivalent — only DEFAULT_FIELDS are used.
        """
        super().__init__()
        all_fields = self.DEFAULT_FIELDS | set(sensitive_fields or [])
        pattern = "|".join(re.escape(f) for f in sorted(all_fields))
        self._regex = re.compile(rf"\b({pattern})\b", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter a log record by redacting sensitive values.

        Checks whether the record was already processed to avoid duplicate
        redaction. If not processed, applies redaction to all record fields
        containing sensitive data.

        Args:
            record: The log record to filter.

        Returns:
            True if the record was successfully filtered or already processed,
            False if no regex is configured.
        """
        record_dict = record.__dict__

        if self.ALREADY_FILTERED_FLAG in record_dict:
            return True

        if self._regex:
            for k, v in record_dict.items():
                record_dict[k] = self.redact(v)
        else:
            return False

        record_dict[self.ALREADY_FILTERED_FLAG] = True
        return True

    def _redact_all(self, item, depth):
        """Recursively replace all string values with a censored placeholder."""
        if isinstance(item, str):
            return "*CENSORED*"
        if isinstance(item, dict):
            return {
                dict_key: self._redact_all(nested_item, depth + 1)
                for dict_key, nested_item in item.items()
            }
        elif isinstance(item, (tuple, set)):
            return tuple(self._redact_all(nested_item, depth + 1) for nested_item in item)
        elif isinstance(item, list):
            return [self._redact_all(nested_item, depth + 1) for nested_item in item]
        else:
            return item

    def _redact(self, item, name, depth):
        """Recursively redact sensitive fields from a value based on the key name.

        Depth is bounded to avoid spending excessive effort on deeply nested
        structures and to prevent infinite recursion when a structure holds a
        reference to itself.
        """
        try:
            if name and should_hide_value_for_key(name):
                return self._redact_all(item, depth)
            if isinstance(item, dict):
                return {
                    dict_key: self._redact(nested_item, name=dict_key, depth=(depth + 1))
                    for dict_key, nested_item in item.items()
                }
            elif isinstance(item, tuple) and hasattr(item, "_asdict") and hasattr(item, "_fields"):
                named_tuple = item.__class__.__name__
                # noinspection PyProtectedMember
                item = item._asdict()
                masked_dict = {
                    dict_key: self._redact(nested_item, name=dict_key, depth=(depth + 1))
                    for dict_key, nested_item in item.items()
                }
                # noinspection PyArgumentList
                return namedtuple(named_tuple, masked_dict.keys())(**masked_dict)
            elif isinstance(item, str):
                return item
            elif isinstance(item, (tuple, set)):
                return tuple(
                    self._redact(nested_item, name=None, depth=(depth + 1)) for nested_item in item
                )
            elif isinstance(item, list):
                return [
                    self._redact(nested_element, name=None, depth=(depth + 1))
                    for nested_element in item
                ]
            else:
                return item
        except Exception as e:
            logging.warning(
                "Unable to redact %s. Error was: %s: %s",
                repr(item),
                type(e).__name__,
                str(e),
            )

            return item

    def redact(self, item: Any, name: str | None = None) -> Any:
        """Redact sensitive information from the given input data.

        Processes the provided item and optionally uses the name for context
        during redaction to securely obfuscate sensitive fields.

        Args:
            item: The data object to be redacted.
            name: An optional name providing context for the redaction process.

        Returns:
            The redacted version of the input data.
        """
        return self._redact(item, name, depth=0)
