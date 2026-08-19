import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from transformations import (
    BaseRuleSet,
    ConfigurationError,
    TransformationConfig,
    load_xmi,
    transform_xmi,
)
from transformations.implementations.BaseTransformation import is_self_describing_enumeration
from transformations.rule import NonInvertibleTransformationError, TransformationRule
from transformations.ruleset import TransformationRuleset
from transformations.strategies.enumeration import InspireEnumerationStrategy, IsoEnumerationStrategy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_XMI = (
    PROJECT_ROOT.parent.parent
    / "HMMG"
    / "XMI"
    / "ConceptualModels"
    / "ISO 19157 Edition 1.xml"
)
HO = Namespace("https://def.isotc211.org/def/ho/")
ISO191502 = Namespace("http://def.isotc211.org/iso19150/-2/2012/base#")


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


def test_config_validates_names_and_fills_profile_baselines():
    config = TransformationConfig("jetlund", {"abstract_class": "annotation"})
    assert config.strategies["inheritance"] == "direct_subclass"
    assert "composition" not in config.strategies
    assert config.configuration_id == TransformationConfig(
        "jetlund", {"abstract_class": "annotation"}
    ).configuration_id
    with pytest.raises(ConfigurationError, match="Unknown paper"):
        TransformationConfig("unknown-paper")
    with pytest.raises(ConfigurationError, match="Unknown decision point"):
        TransformationConfig("jetlund", {"unknown": "annotation"})
    with pytest.raises(ConfigurationError, match="Unknown strategy"):
        TransformationConfig("jetlund", {"abstract_class": "unknown"})


def test_explicit_abstract_strategies_change_rdf_output():
    annotated = transform_xmi(
        SAMPLE_XMI,
        config=TransformationConfig("jetlund", {"abstract_class": "annotation"}),
    )
    unions = transform_xmi(
        SAMPLE_XMI,
        config=TransformationConfig("zedlitz_luttenberger_2012"),
    )
    assert list(annotated.triples((None, ISO191502.isAbstract, None)))
    assert list(unions.triples((None, OWL.disjointUnionOf, None)))


def test_iso_enumeration_uses_literal_datatype_one_of():
    graph = Graph()
    context = type("Context", (), {"graph": graph})()
    attribute = URIRef("https://example.org/attribute")
    IsoEnumerationStrategy().apply(
        context,
        class_iri=URIRef("https://example.org/Status"),
        values=["active", "retired"],
        attributes=[attribute],
    )
    data_range = graph.value(attribute, RDFS.range)
    assert (attribute, RDF.type, OWL.DatatypeProperty) in graph
    assert data_range is not None
    assert (data_range, OWL.oneOf, None) in graph
    assert Literal("active") in graph.objects(graph.value(data_range, OWL.oneOf), RDF.first)


def test_inspire_non_self_describing_enumeration_uses_skos_concept_range():
    graph = Graph()
    context = type("Context", (), {"graph": graph})()
    enumeration = URIRef("https://example.org/Status")
    attribute = URIRef("https://example.org/status")
    InspireEnumerationStrategy().apply(
        context,
        class_iri=enumeration,
        values=["active", "retired"],
        attributes=[attribute],
        self_describing=False,
    )
    scheme = graph.value(enumeration, RDFS.seeAlso)
    assert scheme is not None
    assert (scheme, RDF.type, SKOS.ConceptScheme) in graph
    assert (attribute, RDFS.range, SKOS.Concept) in graph
    assert not list(graph.triples((None, OWL.oneOf, None)))


def test_enumeration_self_description_is_derived_from_member_names():
    assert is_self_describing_enumeration(["active", "not-applicable", "unknown_value"])
    assert not is_self_describing_enumeration(["1", "2"])
    assert not is_self_describing_enumeration(["code_01", "code_02"])


def test_inspire_self_describing_enumeration_uses_datatype_one_of():
    graph = Graph()
    context = type("Context", (), {"graph": graph})()
    attribute = URIRef("https://example.org/status")
    InspireEnumerationStrategy().apply(
        context,
        class_iri=URIRef("https://example.org/Status"),
        values=["active", "retired"],
        attributes=[attribute],
        self_describing=is_self_describing_enumeration(["active", "retired"]),
    )
    assert (attribute, RDF.type, OWL.DatatypeProperty) in graph
    assert list(graph.triples((None, OWL.oneOf, None)))


def test_cli_accepts_paper_and_strategy_flags():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            str(SAMPLE_XMI),
            "--paper",
            "zedlitz_luttenberger_2012",
            "--strategy",
            "abstract_class=disjoint_union",
            "--format",
            "turtle",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "disjointUnionOf" in result.stdout
