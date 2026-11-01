"""Tests for the TRACE level setup in pyclifer.core.log.levels."""

import logging
import subprocess
import sys

from pyclifer import TRACE


def _run_fresh(code: str) -> subprocess.CompletedProcess:
    """Run code in a new interpreter, where no application has been declared yet.

    The trace method lives on the global Logger class, so only a new process shows what a
    program sees before it builds an application.
    """
    return subprocess.run(  # noqa: S603 - fixed interpreter, code written in this file
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )


class TestTraceAvailability:
    """get_logger returns loggers that have a trace method, without building an application."""

    def test_get_logger_trace_works_before_any_application(self):
        result = _run_fresh(
            "from pyclifer import get_logger\n"
            "get_logger('probe.module').trace('message')\n"
            "print('ok')\n"
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "ok"

    def test_package_logger_has_trace_before_any_application(self):
        result = _run_fresh("import pyclifer\nprint(callable(pyclifer.logger.trace))\n")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "True"

    def test_plain_logging_loggers_get_trace_too(self):
        result = _run_fresh(
            "import logging, pyclifer\nprint(callable(logging.getLogger('other').trace))\n"
        )
        assert result.stdout.strip() == "True"


class TestTraceSourceLocation:
    """A TRACE record points at the code that called trace(), like DEBUG and INFO records do."""

    @staticmethod
    def _record_for(call, caplog):
        """Run call(logger) with TRACE enabled and return the single record it produced."""
        logger = logging.getLogger("tests.trace.location")
        with caplog.at_level(TRACE, logger=logger.name):
            call(logger)
        assert len(caplog.records) == 1
        return caplog.records[0]

    def test_record_points_at_the_caller(self, caplog):
        def caller(logger):
            logger.trace("message")

        record = self._record_for(caller, caplog)
        assert record.filename == "test_levels.py"
        assert record.funcName == "caller"

    def test_record_location_matches_a_debug_record(self, caplog):
        def caller(logger):
            logger.debug("d")
            logger.trace("t")

        logger = logging.getLogger("tests.trace.location")
        with caplog.at_level(TRACE, logger=logger.name):
            caller(logger)
        debug, trace = caplog.records
        assert (trace.filename, trace.funcName) == (debug.filename, debug.funcName)

    def test_stacklevel_given_by_the_caller_is_relative_to_the_caller(self, caplog):
        def helper(logger):
            logger.trace("message", stacklevel=2)

        def outer(logger):
            helper(logger)

        record = self._record_for(outer, caplog)
        assert record.funcName == "outer"
