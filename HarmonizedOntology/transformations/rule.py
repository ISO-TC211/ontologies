from __future__ import annotations

from abc import ABC, abstractmethod


class NonInvertibleTransformationError(ValueError):
    """Raised when a transformation rule cannot safely invert its own extraction."""


class TransformationRule(ABC):
    """Base class for stateless or stateful XMI-to-RDF transformation rules."""

    @property
    def name(self):
        return self.__class__.__name__

    def fit(self, context, y=None):
        """Optional fitting hook; default behavior is a no-op by returning `self`."""
        return self

    @abstractmethod
    def transform(self, context):
        """Apply a transformation to the provided extraction context."""
        raise NotImplementedError

    def fit_transform(self, context, y=None):
        """Convenience wrapper for scikit-learn-style rule composition."""
        self.fit(context, y=y)
        return self.transform(context)

    def inverse_transform(self, context):
        """Optional inverse transform for rules that are explicitly safe to invert."""
        raise NonInvertibleTransformationError(
            f"Rule '{self.name}' does not support inverse_transform() for this extraction."
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r})"
