"""Base domain model backed by Pydantic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pydantic

if TYPE_CHECKING:
    from typing_extensions import Self


class BaseModel(pydantic.BaseModel):
    """Base class for pyclif domain models.

    Extends pydantic.BaseModel with to_dict(), from_dict() and field_names()
    for integration with OperationResult and BaseRenderer.

    Subclass and declare fields as Pydantic annotations. Use field_validator()
    for business-rule validation on top of the automatic type validation.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a JSON-compatible dict."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build an instance from a dict with Pydantic validation.

        Args:
            data: Raw dict (API response, DB row, …) to validate and coerce.

        Returns:
            A validated model instance.

        Raises:
            pydantic.ValidationError: When the data does not match the model schema.
        """
        return cls.model_validate(data)

    @classmethod
    def field_names(cls) -> list[str]:
        """Return the declared field names.

        Returns:
            List of field name strings in declaration order.
        """
        return list(cls.model_fields.keys())
