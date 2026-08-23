from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from rdflib import Graph

from ..context import TransformationContext


class NonInvertibleTransformationError(ValueError):
    """Raised when a transformation rule cannot safely invert its own extraction."""


class TransformationStep(ABC):
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


class TransformationPipeline:
    """An ordered sequence of transformation rules applied to one extraction context."""

    def __init__(self, rules=None):
        self.rules = []
        if rules is not None:
            for rule in rules:
                self.add_rule(rule)

    def add_rule(self, rule):
        if not isinstance(rule, TransformationStep):
            raise TypeError(f"Rule '{rule}' is not a TransformationStep instance.")
        self.rules.append(rule)
        return self

    def fit(self, context, y=None):
        for rule in self.rules:
            rule.fit(context, y=y)
        return self

    def transform(self, context: TransformationContext) -> Graph:
        for idx, rule in enumerate(self.rules):
            if not isinstance(rule, TransformationStep):
                raise TypeError(
                    f"Rule at position {idx} is not a valid transformation rule: {rule!r}"
                )
            result = rule.transform(context)
            if hasattr(context, "graph"):
                if isinstance(result, type(context.graph)):
                    context.graph = result
                elif hasattr(result, "graph"):
                    context.graph = result.graph
            elif hasattr(result, "graph"):
                context = result
        return context.graph if hasattr(context, "graph") else context

    def fit_transform(self, context, y=None):
        self.fit(context, y=y)
        return self.transform(context)

    def inverse_transform(self, context):
        graph = context.graph if hasattr(context, "graph") else context
        for rule in reversed(self.rules):
            try:
                graph = rule.inverse_transform(context)
            except NonInvertibleTransformationError as exc:
                raise NonInvertibleTransformationError(
                    f"Rule '{rule.name}' failed during inverse transform: {exc}"
                ) from exc
        return graph

    def __len__(self):
        return len(self.rules)

    def __iter__(self):
        return iter(self.rules)

    def __getitem__(self, item):
        return self.rules[item]

    def select(self, names):
        if isinstance(names, str):
            names = [names]
        allowed = {rule.name for rule in self.rules}
        selected = []
        for name in names:
            if name not in allowed:
                raise ValueError(f"Unknown rule '{name}'. Available rules: {sorted(allowed)}")
            selected.append(next(rule for rule in self.rules if rule.name == name))
        return TransformationPipeline(selected)

    def __repr__(self):
        return f"TransformationPipeline(rules={[rule.name for rule in self.rules]!r})"
