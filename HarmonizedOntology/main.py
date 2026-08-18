"""Simple CLI entry point for running the harmonized ontology transform."""

import argparse

from transformations import transform_xmi


def main(argv=None):
    """Run the default XMI-to-RDF transformation."""
    parser = argparse.ArgumentParser(
        description="Convert an XMI file into RDF using the default Harmonized Ontology rules.",
    )
    parser.add_argument("xmi_path", help="Path to the XMI file")
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
