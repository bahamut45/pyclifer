"""Logging filters for pyclifer."""

import builtins
import logging
import re
from collections import namedtuple
from typing import Any, ClassVar

# BaseExceptionGroup exists from Python 3.11 only.
_EXCEPTION_GROUP = getattr(builtins, "BaseExceptionGroup", None)

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

    def __init__(
        self, sensitive_fields: list[str] | None = None, mask_free_text: bool = False
    ) -> None:
        """Initialize the masker, merging sensitive_fields into DEFAULT_FIELDS.

        Args:
            sensitive_fields: Additional field names to mask on top of DEFAULT_FIELDS.
                              None and [] are equivalent — only DEFAULT_FIELDS are used.
            mask_free_text: Also mask key=value pairs written inside the text of a message and
                            of the exception it carries (message, cause, context, group, notes).
                            Off by default: a name that contains a sensitive field is masked
                            whatever its value means, so max_tokens=100 is masked too.
        """
        super().__init__()
        all_fields = self.DEFAULT_FIELDS | set(sensitive_fields or [])
        pattern = "|".join(re.escape(f) for f in sorted(all_fields))
        self._regex = re.compile(rf"\b({pattern})\b", re.IGNORECASE)
        # The fields this masker hides, lowercase, matched as substrings of a key name.
        self._fields = frozenset(field.strip().lower() for field in all_fields)
        self._mask_free_text = mask_free_text
        self._text_regex = self._build_text_regex(self._fields)

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

        if self._mask_free_text:
            self._mask_message(record)
            self._mask_exception(record)

        record_dict[self.ALREADY_FILTERED_FLAG] = True
        return True

    @staticmethod
    def _build_text_regex(fields: frozenset[str]) -> re.Pattern[str]:
        """Compile the pattern that finds a sensitive key and its value inside a text.

        The key is any name that contains a sensitive field, possibly quoted. It is followed by
        = or :, an optional authorization scheme, then the value: quoted up to the closing
        quote, or unquoted up to a space or a delimiter.

        The key can only start at the beginning of a word. Without that anchor, every position
        inside a long run of word characters restarted the greedy prefix, which made the cost
        grow with the square of the text.
        """
        alternatives = "|".join(re.escape(f) for f in sorted(fields, key=len, reverse=True))
        return re.compile(
            rf"""
            (?<![\w.\-])
            (?P<key>["']?[\w.\-]*(?:{alternatives})[\w.\-]*["']?)
            (?P<separator>\s*[:=]\s*)
            (?P<scheme>(?:Bearer|Basic|Token)\s+)?
            (?:"(?P<double>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s"',;&)\]}}]+))
            """,
            re.IGNORECASE | re.VERBOSE,
        )

    def redact_text(self, text: str) -> str:
        """Mask the value of every sensitive key written as key=value inside a text.

        Args:
            text: The text to scan, for example a log message.

        Returns:
            The text with those values replaced by a placeholder. A secret with no key next to it,
            as in "the password is hunter2", cannot be found and is kept.
        """

        def replace(match: re.Match[str]) -> str:
            quote = (
                '"' if match["double"] is not None else "'" if match["single"] is not None else ""
            )
            return (
                f"{match['key']}{match['separator']}{match['scheme'] or ''}{quote}*CENSORED*{quote}"
            )

        return self._text_regex.sub(replace, text)

    def _mask_message(self, record: logging.LogRecord) -> None:
        """Replace a record's message by its formatted and masked text.

        The arguments are folded into the message first, since a secret can sit in either, and
        emptied afterwards. A message that cannot be formatted is left to logging to report.
        """
        try:
            message = record.getMessage()
        except (TypeError, ValueError):  # bad format string or arguments: logging will report it
            return
        record.msg = self.redact_text(message)
        record.args = ()

    def _mask_exception(self, record: logging.LogRecord) -> None:
        """Mask the secrets written in the exception a record carries.

        The exception of exc_info is replaced by a masked copy, so that a handler still renders it
        itself, with its Rich traceback. A text another handler already formatted and cached in
        exc_text is masked too, since the formatter would reuse it. The source lines a traceback
        shows are not touched.
        """
        if record.exc_text:
            record.exc_text = self.redact_text(record.exc_text)
        if record.exc_info and record.exc_info[1] is not None:
            _, exception, traceback = record.exc_info
            masked = self._masked_exception(exception, {})
            record.exc_info = (type(masked), masked, traceback)

    def _masked_exception(
        self, exception: BaseException | None, copies: dict[int, BaseException]
    ) -> BaseException | None:
        """Copy an exception so that its text is masked, with the same type name and traceback.

        The copy is an instance of a subclass of the original type that has the same name and
        module and whose str() is the masked text of the original. The cause, the context, the
        exceptions of a group and the notes are masked the same way.

        Args:
            exception: The exception to copy, or None.
            copies: The copies already made, by the id of the original, which stops a chain that
                loops back to an exception already met.

        Returns:
            The masked copy, or None when there is no exception.
        """
        if exception is None:
            return None
        if id(exception) in copies:
            return copies[id(exception)]

        text = self.redact_text(str(exception))
        original_type = type(exception)
        try:
            masked_type = type(
                original_type.__name__,
                (original_type,),
                {
                    "__str__": lambda self: text,
                    "__module__": original_type.__module__,
                    "__qualname__": original_type.__qualname__,
                },
            )
            if _EXCEPTION_GROUP is not None and isinstance(exception, _EXCEPTION_GROUP):
                members = [
                    self._masked_exception(member, copies) for member in exception.exceptions
                ]
                masked = masked_type.__new__(masked_type, exception.message, members)
            else:
                masked = masked_type.__new__(masked_type, *exception.args)
        except (TypeError, ValueError):  # a type that cannot be subclassed or built from its args
            masked = RuntimeError(text)

        masked.__dict__.update(exception.__dict__)
        copies[id(exception)] = masked
        notes = getattr(exception, "__notes__", None)
        if isinstance(notes, list):
            masked.__notes__ = [self.redact_text(str(note)) for note in notes]
        masked.__cause__ = self._masked_exception(exception.__cause__, copies)
        masked.__context__ = self._masked_exception(exception.__context__, copies)
        masked.__suppress_context__ = (
            exception.__suppress_context__
        )  # after __cause__, which sets it
        masked.__traceback__ = exception.__traceback__
        return masked

    def _hides(self, name: Any) -> bool:
        """Tell whether a key name holds one of the fields this masker hides.

        Unlike should_hide_value_for_key, which only knows the default fields, this takes the
        sensitive_fields given to the masker into account.
        """
        if isinstance(name, str):
            name = name.strip().lower()
            return any(field in name for field in self._fields)
        return False

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
            if name and self._hides(name):
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
        except Exception as e:  # security filter must never crash — log and return item unredacted
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
