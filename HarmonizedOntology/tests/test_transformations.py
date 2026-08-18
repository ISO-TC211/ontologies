import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF

from transformations import BaseRuleSet, load_xmi, transform_xmi
from transformations.rule import NonInvertibleTransformationError, TransformationRule
from transformations.ruleset import TransformationRuleset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_XMI = (
    PROJECT_ROOT.parent.parent
    / "HMMG"
    / "XMI"
    / "ConceptualModels"
    / "ISO 19157 Edition 1.xml"
)
HO = Namespace("https://def.isotc211.org/def/ho/")


class DummyRule(TransformationRule):
    def transform(self, context):
        context.graph.add((Namespace("https://example.org/").thing, RDF.type, RDF.Property))
        return context


def test_transformation_rule_default_fit_returns_self():
    rule = DummyRule()
    assert rule.fit(None) is rule


def test_ruleset_applies_rules_in_order():
    ruleset = TransformationRuleset([DummyRule(), DummyRule()])
    graph = Graph()
    context = type("Context", (), {"graph": graph})()
    result = ruleset.transform(context)
    assert result is graph
    assert len(graph) == 1


def test_default_ruleset_runs_against_repository_xmi():
    graph = transform_xmi(SAMPLE_XMI)
    assert isinstance(graph, Graph)
    assert len(graph) > 0
    assert any(obj == HO.ModelPackage for _, _, obj in graph.triples((None, RDF.type, None)))
    assert any(obj == OWL.Class for _, _, obj in graph.triples((None, RDF.type, None)))


def test_ruleset_can_select_subset():
    ruleset = BaseRuleSet()
    subset = ruleset.select(["BaseExtractPackages", "BaseExtractClasses"])
    assert [rule.name for rule in subset.rules] == ["BaseExtractPackages", "BaseExtractClasses"]


def test_transform_xmi_can_select_subset():
    graph = transform_xmi(SAMPLE_XMI, rule_names=["BaseExtractPackages", "BaseExtractClasses"])
    assert any(obj == HO.ModelPackage for _, _, obj in graph.triples((None, RDF.type, None)))
    assert any(obj == OWL.Class for _, _, obj in graph.triples((None, RDF.type, None)))
    assert not any(obj == RDF.Property for _, _, obj in graph.triples((None, RDF.type, None)))


def test_inverse_transform_raises_for_non_invertible_rule():
    with pytest.raises(NonInvertibleTransformationError):
        DummyRule().inverse_transform(None)


def test_cli_smoke():
    result = subprocess.run(
        [sys.executable, "main.py", str(SAMPLE_XMI), "--format", "turtle"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "@prefix" in result.stdout.lower()


def test_package_import_smoke():
    result = subprocess.run(
        [sys.executable, "-c", "from transformations import transform_xmi; print(transform_xmi.__name__)"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
