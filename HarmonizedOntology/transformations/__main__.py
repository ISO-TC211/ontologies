"""Module entry point for the transformation package."""
from __future__ import annotations

import argparse
from pathlib import Path

from lxml import etree
from rdflib import Graph, URIRef

from .identifiers import ExtractionIndex, make_iri
from .pipeline import DefaultTransformationPipeline
from .config import TransformationConfig
from .context import TransformationContext


def load_xmi(xmi_path: str | Path, graph: Graph | None = None) -> TransformationContext:
    xml_path = Path(xmi_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"XMI file not found: {xml_path}")
    tree = etree.parse(str(xml_path))
    source_iri = URIRef(make_iri("std", xml_path))
    return TransformationContext(tree, source_iri, graph=graph, extraction_index=ExtractionIndex(tree))


def transform_xmi(xmi_path, rule_names=None, config=None, graph=None) -> Graph:
    context = load_xmi(xmi_path, graph=graph)
    ruleset = DefaultTransformationPipeline(rule_names=rule_names, config=config)
    context.strategies = ruleset.strategies
    return ruleset.transform(context)


def transform_directory(xmi_directory, rule_names=None, config=None) -> Graph:
    directory = Path(xmi_directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"XMI directory not found: {directory}")

    graph = Graph()
    for xml_path in sorted(
        path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() == ".xml"
    ):
        transform_xmi(xml_path, rule_names=rule_names, config=config, graph=graph)
    return graph


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run transformation rules against an XMI file or directory.")
    parser.add_argument("xmi_path", help="Path to an XMI XML file or directory")
    parser.add_argument(
        "--rules",
        nargs="*",
        default=None,
        help="Optional subset of rule names to run",
    )
    parser.add_argument("--format", default="turtle", help="RDF serialization format to emit")
    parser.add_argument("--paper", help="Paper profile identifier")
    parser.add_argument("--strategy", action="append", default=[], metavar="DECISION_POINT=STRATEGY")
    args = parser.parse_args(argv)

    selected = dict(item.split("=", 1) for item in args.strategy)
    config = TransformationConfig(args.paper, selected) if args.paper else None
    input_path = Path(args.xmi_path)
    if input_path.is_dir():
        graph = transform_directory(input_path, rule_names=args.rules, config=config)
        graph.serialize(destination=str(input_path / "output.ttl"), format=args.format)
    else:
        graph = transform_xmi(input_path, rule_names=args.rules, config=config)
        print(graph.serialize(format=args.format))
    return graph


if __name__ == "__main__":
    main()
