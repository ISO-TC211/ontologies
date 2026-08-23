from .base import (
    NonInvertibleTransformationError,
    TransformationPipeline,
    TransformationStep,
)
from .classes import ExtractClasses, ExtractSubclassRelations
from .packages import ExtractPackageHierarchy, ExtractPackages
from .properties import (
    AddSchemaDescriptionProperty,
    ExtractAssociations,
    ExtractAttributes,
    ExtractEnumerations,
)


class DefaultTransformationPipeline(TransformationPipeline):
    """Default XMI-to-RDF transformation ruleset for ho extraction."""

    def __init__(self, rule_names=None, config=None):
        self.config = config
        rules = [
            AddSchemaDescriptionProperty(),
            ExtractPackages(),
            ExtractPackageHierarchy(),
            ExtractClasses(),
            ExtractSubclassRelations(),
            ExtractAssociations(),
            ExtractAttributes(),
            ExtractEnumerations(),
        ]
        if config is not None:
            strategies = config.profile.strategies
            self.strategies = {
                point: strategies[point][config.strategies[point]]()
                for point in config.strategies
            }
        else:
            self.strategies = {}
        self._strategy_context = self.strategies
        if rule_names is not None:
            if isinstance(rule_names, str):
                rule_names = [rule_names]
            rules = [rule for rule in rules if rule.name in rule_names]
        super().__init__(rules)


__all__ = [
    "DefaultTransformationPipeline",
    "NonInvertibleTransformationError",
    "TransformationPipeline",
    "TransformationStep",
    "AddSchemaDescriptionProperty",
    "ExtractPackages",
    "ExtractPackageHierarchy",
    "ExtractClasses",
    "ExtractSubclassRelations",
    "ExtractAssociations",
    "ExtractAttributes",
    "ExtractEnumerations",
]
