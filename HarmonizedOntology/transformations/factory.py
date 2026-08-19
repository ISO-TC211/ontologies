from __future__ import annotations

from .implementations.BaseTransformation import BaseRuleSet


class ProfileAwareRulesetFactory:
    """Resolve an immutable transformation configuration into a ruleset."""

    def create(self, config):
        return BaseRuleSet(config=config)


def make_ruleset(config):
    return ProfileAwareRulesetFactory().create(config)