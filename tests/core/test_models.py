"""Unit tests for BaseModel."""

import pydantic
import pytest
from pydantic import field_validator

from pyclif import BaseModel

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _Article(BaseModel):
    id: int
    title: str
    status: str


class _ArticleWithValidator(BaseModel):
    id: int
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("draft", "published"):
            raise ValueError(f"invalid status: {v!r}")
        return v


# ---------------------------------------------------------------------------
# TestBaseModelToDict
# ---------------------------------------------------------------------------


class TestBaseModelToDict:
    def test_returns_all_fields(self) -> None:
        article = _Article(id=1, title="Hello", status="draft")
        result = article.to_dict()
        assert result == {"id": 1, "title": "Hello", "status": "draft"}

    def test_returns_dict_type(self) -> None:
        article = _Article(id=1, title="Hello", status="draft")
        assert isinstance(article.to_dict(), dict)

    def test_nested_model_is_serialized(self) -> None:
        class _Inner(BaseModel):
            value: int

        class _Outer(BaseModel):
            inner: _Inner

        outer = _Outer(inner=_Inner(value=42))
        result = outer.to_dict()
        assert result == {"inner": {"value": 42}}


# ---------------------------------------------------------------------------
# TestBaseModelFromDict
# ---------------------------------------------------------------------------


class TestBaseModelFromDict:
    def test_creates_instance_from_valid_dict(self) -> None:
        article = _Article.from_dict({"id": 1, "title": "Hello", "status": "draft"})
        assert isinstance(article, _Article)
        assert article.id == 1
        assert article.title == "Hello"
        assert article.status == "draft"

    def test_coerces_string_to_int(self) -> None:
        article = _Article.from_dict({"id": "42", "title": "Hello", "status": "draft"})
        assert article.id == 42

    def test_raises_validation_error_on_wrong_type(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="id"):
            _Article.from_dict({"id": "not-an-int", "title": "Hello", "status": "draft"})

    def test_raises_validation_error_on_missing_field(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="title"):
            _Article.from_dict({"id": 1, "status": "draft"})

    def test_returns_subclass_instance(self) -> None:
        article = _ArticleWithValidator.from_dict({"id": 1, "status": "draft"})
        assert isinstance(article, _ArticleWithValidator)


# ---------------------------------------------------------------------------
# TestBaseModelFieldNames
# ---------------------------------------------------------------------------


class TestBaseModelFieldNames:
    def test_returns_declared_field_names(self) -> None:
        assert _Article.field_names() == ["id", "title", "status"]

    def test_returns_list_type(self) -> None:
        assert isinstance(_Article.field_names(), list)

    def test_respects_declaration_order(self) -> None:
        class _Ordered(BaseModel):
            z: int
            a: str
            m: float

        assert _Ordered.field_names() == ["z", "a", "m"]

    def test_empty_model_returns_empty_list(self) -> None:
        class _Empty(BaseModel):
            pass

        assert _Empty.field_names() == []


# ---------------------------------------------------------------------------
# TestBaseModelFieldValidator
# ---------------------------------------------------------------------------


class TestBaseModelFieldValidator:
    def test_valid_status_passes(self) -> None:
        article = _ArticleWithValidator(id=1, status="draft")
        assert article.status == "draft"

    def test_invalid_status_raises_validation_error(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="invalid status"):
            _ArticleWithValidator(id=1, status="unknown")

    def test_validator_runs_on_from_dict(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="invalid status"):
            _ArticleWithValidator.from_dict({"id": 1, "status": "unknown"})
