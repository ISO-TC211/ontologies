from __future__ import annotations

from .implementations.BaseTransformation import DefaultTransformationPipeline


class ProfileAwareRulesetFactory:
    """Resolve an immutable transformation configuration into a ruleset."""

    def create(self, config):
        return DefaultTransformationPipeline(config=config)


def make_ruleset(config):
    return ProfileAwareRulesetFactory().create(config)