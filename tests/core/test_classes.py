"""Tests for PycliferOption.context and GroupConfig.context_factory."""

from typing import Any

from pyclifer.core.classes import GroupConfig, PycliferOption

# ---------------------------------------------------------------------------
# PycliferOption — context attribute
# ---------------------------------------------------------------------------


class TestPycliferOptionContextAttr:
    """PycliferOption stores the context attribute correctly."""

    def test_context_defaults_to_false(self):
        """context defaults to False when not passed."""
        opt = PycliferOption(["--host"])
        assert opt.context is False

    def test_context_true_is_stored(self):
        """context=True is stored on the instance."""
        opt = PycliferOption(["--host"], context=True)
        assert opt.context is True

    def test_context_false_explicit(self):
        """context=False explicit is stored correctly."""
        opt = PycliferOption(["--host"], context=False)
        assert opt.context is False

    def test_context_and_is_global_independent(self):
        """context and is_global can both be True simultaneously."""
        opt = PycliferOption(["--resource"], context=True, is_global=True)
        assert opt.context is True
        assert opt.is_global is True

    def test_is_global_unchanged_when_context_added(self):
        """Adding context=True does not change is_global default."""
        opt = PycliferOption(["--host"], context=True)
        assert opt.is_global is False


# ---------------------------------------------------------------------------
# GroupConfig — context_factory attribute
# ---------------------------------------------------------------------------


class TestGroupConfigContextFactory:
    """GroupConfig stores context_factory correctly."""

    def test_context_factory_defaults_to_none(self):
        """context_factory is None by default."""
        cfg = GroupConfig()
        assert cfg.context_factory is None

    def test_context_factory_callable_stored(self):
        """A callable passed as context_factory is stored."""

        class AppContext:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs

        cfg = GroupConfig(context_factory=AppContext)
        assert cfg.context_factory is AppContext

    def test_context_factory_lambda_stored(self):
        """A lambda is stored as context_factory."""
        factory = lambda **kw: kw  # noqa: E731
        cfg = GroupConfig(context_factory=factory)
        assert cfg.context_factory is factory
