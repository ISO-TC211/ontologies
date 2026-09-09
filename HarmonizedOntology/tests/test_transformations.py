import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pytest
from rdflib import Graph, Literal, Namespace, SDO, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from transformations import (
    DefaultTransformationPipeline,
    ConfigurationError,
    TransformationConfig,
    load_xmi,
    transform_directory,
    transform_xmi,
)
from transformations.pipeline.base import (
    NonInvertibleTransformationError,
    TransformationPipeline,
    TransformationStep,
)
from transformations.context import NS
from transformations.identifiers import sanitize_prefix
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


class DummyRule(TransformationStep):
    def transform(self, context):
        context.graph.add((Namespace("https://example.org/").thing, RDF.type, RDF.Property))
        return context


def test_transformation_rule_default_fit_returns_self():
    rule = DummyRule()
    assert rule.fit(None) is rule


def test_ruleset_applies_rules_in_order():
    ruleset = TransformationPipeline([DummyRule(), DummyRule()])
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


def test_attributes_on_classifier_roles_are_ignored():
    xmi = (
        PROJECT_ROOT.parent.parent
        / "HMMG"
        / "XMI"
        / "ConceptualModels"
        / "ISO 19148 Edition 2.xml"
    )
    graph = transform_xmi(xmi)
    assert isinstance(graph, Graph)
    assert (None, SDO.identifier, Literal("748EE51D-649F-4167-AE8F-4CA6A17D0F8C", datatype=HO.xmiId)) not in graph


def test_iri_service_uses_document_name_and_xmi_ids():
    context = load_xmi(SAMPLE_XMI)
    model = context.tree.findall(".//UML:Model", namespaces=NS)[0]
    model_id = model.get("xmi.id")
    service = context.iri_registry
    base = f"https://def.isotc211.org/model/{quote(SAMPLE_XMI.stem, safe='')}"

    assert str(service.model_iri) == base
    for identifiers in (service.package_iris, service.class_iris, service.property_iris):
        for xmi_id, iri in identifiers.items():
            assert str(iri) == f"{base}#{xmi_id}"


def test_document_prefix_is_sanitized_and_bound_to_fragment_namespace():
    graph = transform_xmi(SAMPLE_XMI)
    serialized = str(graph.serialize(format="turtle"))
    prefix = sanitize_prefix(SAMPLE_XMI.stem)
    namespace = f"https://def.isotc211.org/model/{quote(SAMPLE_XMI.stem, safe='')}#"

    assert prefix == "ISO19157Edition1"
    assert (prefix, URIRef(namespace)) in set(graph.namespaces())
    assert f"@prefix {prefix}: <{namespace}> ." in serialized


@pytest.mark.parametrize(
    ("document_name", "expected"),
    [
        ("ISO 19148 Edition 2", "ISO19148Edition2"),
        ("ISO-19148/Edition 2", "ISO19148Edition2"),
        ("123 model", "doc123model"),
        ("...", "doc"),
    ],
)
def test_sanitize_prefix_handles_turtle_prefix_edge_cases(document_name, expected):
    assert sanitize_prefix(document_name) == expected


def test_document_prefix_collisions_are_disambiguated(tmp_path):
    first = tmp_path / "ISO-19157.xml"
    second = tmp_path / "ISO19157.xml"
    first.write_bytes(SAMPLE_XMI.read_bytes())
    second.write_bytes(SAMPLE_XMI.read_bytes())

    graph = transform_directory(tmp_path, rule_names=["ExtractPackages"])
    namespaces = dict(graph.namespaces())

    assert namespaces["ISO19157"] == URIRef(
        "https://def.isotc211.org/model/ISO-19157#"
    )
    assert namespaces["ISO19157_2"] == URIRef(
        "https://def.isotc211.org/model/ISO19157#"
    )


def test_ruleset_can_select_subset():
    ruleset = DefaultTransformationPipeline()
    subset = ruleset.select(["ExtractPackages", "ExtractClasses"])
    assert [rule.name for rule in subset.rules] == ["ExtractPackages", "ExtractClasses"]


def test_transform_xmi_can_select_subset():
    graph = transform_xmi(SAMPLE_XMI, rule_names=["ExtractPackages", "ExtractClasses"])
    assert any(obj == HO.ModelPackage for _, _, obj in graph.triples((None, RDF.type, None)))
    assert any(obj == OWL.Class for _, _, obj in graph.triples((None, RDF.type, None)))
    assert not any(obj == RDF.Property for _, _, obj in graph.triples((None, RDF.type, None)))


def test_transform_directory_recursively_combines_xml_files(tmp_path):
    first = tmp_path / "first.xml"
    nested = tmp_path / "nested" / "second.xml"
    nested.parent.mkdir()
    first.write_bytes(SAMPLE_XMI.read_bytes())
    nested.write_bytes(SAMPLE_XMI.read_bytes())

    graph = transform_directory(tmp_path, rule_names=["ExtractPackages"])

    assert isinstance(graph, Graph)
    assert len(graph) > 0
    assert len(list(graph.triples((None, RDFS.isDefinedBy, None)))) >= 2


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


def test_config_validates_names_and_fills_profile_defaults():
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


def test_inspire_self_describing_enumeration_uses_datatype_one_of():
    graph = Graph()
    context = type("Context", (), {"graph": graph})()
    attribute = URIRef("https://example.org/status")
    InspireEnumerationStrategy().apply(
        context,
        class_iri=URIRef("https://example.org/Status"),
        values=["active", "retired"],
        attributes=[attribute],
        self_describing=True,
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
