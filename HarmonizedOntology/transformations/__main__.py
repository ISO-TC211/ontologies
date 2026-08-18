"""Module entry point for the transformation package."""
from __future__ import annotations

import argparse
from pathlib import Path

from lxml import etree
from rdflib import Graph, URIRef

from .implementations.BaseTransformation import BaseRuleSet, make_iri


class TransformationContext:
    def __init__(self, tree, source_iri, graph=None):
        self.tree = tree
        self.source_iri = source_iri
        self.graph = graph or Graph()
        self.metadata = {}


def load_xmi(xmi_path):
    xml_path = Path(xmi_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"XMI file not found: {xml_path}")
    tree = etree.parse(str(xml_path))
    source_iri = URIRef(make_iri("std", xml_path))
    return TransformationContext(tree, source_iri)


def transform_xmi(xmi_path, rule_names=None):
    context = load_xmi(xmi_path)
    ruleset = BaseRuleSet(rule_names=rule_names)
    graph = ruleset.transform(context)
    return graph


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run ho transformation rules against an XMI file.")
    parser.add_argument("xmi_path", help="Path to the XMI XML file")
    parser.add_argument(
        "--rules",
        nargs="*",
        default=None,
        help="Optional subset of rule names to run, e.g. BaseExtractPackages BaseExtractClasses",
    )
    parser.add_argument("--format", default="turtle", help="RDF serialization format to emit")
    args = parser.parse_args(argv)

    graph = transform_xmi(args.xmi_path, rule_names=args.rules)
    print(graph.serialize(format=args.format))
    return graph


if __name__ == "__main__":
    main()
